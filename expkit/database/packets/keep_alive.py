import base64
import inspect
import json
from pathlib import Path

from Crypto.Hash import SHA512

import expkit
from expkit.base.net.packet import BasePacket
from expkit.framework.database import StageDatabase, TaskDatabase, GroupDatabase, register_packet, PacketDatabase


@register_packet
class PacketWorkerKeepAlive(BasePacket):
    def __init__(self):
        self.reason = ""

    def get_type(self) -> str:
        return "worker_alive"

    def new_instance(self) -> "BasePacket":
        return PacketWorkerKeepAlive()

    def serialize(self) -> dict:
        return {
            **super().serialize()
        }

    def deserialize(self, data: dict):
        pass

