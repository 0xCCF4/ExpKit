import json
import math
import socket
from typing import Tuple

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import SHA512
from Crypto.Protocol import KDF
from Crypto.Util import Padding


class SecureConnection:
    block_size = 256  # bytes
    tag_size = 128//8  # bytes
    nonce_size = 16  # bytes
    max_blocks = 2**16  # max blocks in one packet

    assert int(math.log2(max_blocks)) == math.log2(max_blocks)

    def __init__(self, socket: socket.socket, addr: Tuple[str, int], key: str, salt: bytes):
        self.native_conn = socket
        self.addr = addr

        socket.settimeout(5)

        if key is None:
            self.key = None
        else:
            self.key = KDF.PBKDF2(password=key, salt=salt, dkLen=256//8, count=1, hmac_hash_module=SHA512)
            assert len(self.key) == 256//8

    def __write(self, data: bytes):
        self.native_conn.sendall(data)

    def __read(self, length: int) -> bytes:
        return self.native_conn.recv(length)

    def close(self):
        self.native_conn.close()

    def write(self, data: bytes):
        assert len(data) <= SecureConnection.max_blocks * SecureConnection.block_size, "Packet too large"

        data = Padding.pad(data, block_size=SecureConnection.block_size)
        nonce = Random.get_random_bytes(16)

        if self.key is None:
            ciphertext, tag = data, int(0).to_bytes(SecureConnection.tag_size, byteorder="little")
        else:
            enc = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = enc.encrypt_and_digest(data)

        n_blocks = math.ceil(len(data) / SecureConnection.block_size)

        #           length                                        nonce                         tag
        n_to_send = int(math.log2(SecureConnection.max_blocks)) + SecureConnection.nonce_size + SecureConnection.tag_size + len(data)

        actual_data  = b""
        actual_data += n_blocks.to_bytes(int(math.log2(SecureConnection.max_blocks)), byteorder="little")
        actual_data += nonce
        actual_data += tag
        actual_data += ciphertext

        assert len(actual_data) == n_to_send

        self.__write(actual_data)

    def read(self) -> bytes:
        blocks = int.from_bytes(self.__read(int(math.log2(SecureConnection.max_blocks))), byteorder="little")
        try:
            nonce = self.__read(SecureConnection.nonce_size)
            tag = self.__read(SecureConnection.tag_size)

            ciphertext = Padding.unpad(self.__read(blocks * SecureConnection.block_size), block_size=SecureConnection.block_size)

            if self.key is None:
                data = ciphertext
            else:
                dec = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
                data = dec.decrypt_and_verify(ciphertext, tag)
        except socket.timeout:
            raise EOFError("Connection timed out")

        return data

    def write_packet(self, packet):
        self.write(json.dumps(packet.serialize()).encode("utf-8"))

