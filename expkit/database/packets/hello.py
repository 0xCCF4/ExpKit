import base64
import inspect
import json
from pathlib import Path

from Crypto import Random
from Crypto.Hash import SHA512

import expkit
from expkit.base.architecture import Platform, Architecture
from expkit.base.net.packet import BasePacket
from expkit.framework.database import StageDatabase, TaskDatabase, GroupDatabase, register_packet, PacketDatabase


@register_packet
class PacketWorkerServerHello(BasePacket):
    def __init__(self):
        self.version = None
        self.database = None
        self.platform = None
        self.architecture = None
        self.challenge = None

    def get_type(self) -> str:
        return "worker_hello_server"

    def new_instance(self) -> "PacketWorkerServerHello":
        new = PacketWorkerServerHello()
        new.platform = Platform.get_system_platform()
        new.architecture = Architecture.get_system_architecture()

        new.version = expkit.__version__
        database_entries = []

        database_entries.extend([x for x in StageDatabase.get_instance().stages.values()])
        database_entries.extend([x for x in TaskDatabase.get_instance().tasks.values()])
        database_entries.extend([x for x in GroupDatabase.get_instance().groups.values()])
        database_entries.extend([x for x in PacketDatabase.get_instance().packets.values()])

        new.database = {}

        for x in database_entries:
            class_file = Path(inspect.getfile(x.__class__))
            data = class_file.read_bytes()
            hash = SHA512.new(data=data).digest()
            hash = base64.b64encode(hash).decode("utf-8")

            # Used when locally changing the root database files for debugging
            new.database[x.name] = hash

        new.challenge = Random.get_random_bytes(512)

        return new

    def serialize(self) -> dict:
        return {
            "version": self.version,
            "database": self.database,
            "platform": self.platform.name,
            "architecture": self.architecture.name,
            "challenge": base64.b64encode(self.challenge).decode("utf-8"),
            **super().serialize()
        }

    def deserialize(self, data: dict):
        if self.version != data.get("version", "none"):
            raise ValueError(f"Version mismatch: {self.version} != {data.get('version', 'none')}")

        for k, v in self.database.items():
            if k not in data["database"]:
                raise ValueError(f"Target does not contain database entry: {k}")
            if v != data["database"][k]:
                raise ValueError(f"Database entry mismatch: {k}")
        for k, v in data["database"].items():
            if k not in self.database:
                raise ValueError(f"This instance does not contain database entry: {k}")
            if v != self.database[k]:
                raise ValueError(f"Database entry mismatch: {k}")

        self.database = data["database"]
        self.platform = Platform.get_platform_from_name(data["platform"])
        self.architecture = Architecture.get_architecture_from_name(data["architecture"])
        self.challenge = base64.b64decode(data["challenge"].encode("utf-8"))


@register_packet
class PacketWorkerClientHello(BasePacket):
    def __init__(self):
        self.challenge_response = None

    def get_type(self) -> str:
        return "worker_hello_response"

    def new_instance(self) -> "PacketWorkerClientHello":
        new = PacketWorkerClientHello()
        return new

    def serialize(self) -> dict:
        return {
            "challenge_response": base64.b64encode(self.challenge_response).decode("utf-8"),
            **super().serialize()
        }

    def deserialize(self, data: dict):
        self.challenge_response = base64.b64decode(data["challenge_response"].encode("utf-8"))

    def generate_response(self, challenge: bytes, token: bytes):
        self.challenge_response = SHA512.new(data=challenge+token).digest()

    def verify_response(self, challenge: bytes, token: bytes):
        return SHA512.new(data=challenge+token).digest() == self.challenge_response

