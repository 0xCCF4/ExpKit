import base64
import inspect
import json
from pathlib import Path

from Crypto.Hash import SHA512

import expkit
from expkit.base.net.packet import BasePacket
from expkit.framework.database import StageDatabase, TaskDatabase, GroupDatabase, register_packet, PacketDatabase


@register_packet
class PacketWorkerHello(BasePacket):
    def __init__(self):
        self.initialized = False
        self.version = None
        self.database = None

    def get_type(self) -> str:
        return "worker_hello"

    def new_instance(self) -> "BasePacket":
        if not self.initialized:
            self.version = expkit.__version__
            database_entries = []

            database_entries.extend([x for x in StageDatabase.get_instance().stages.values()])
            database_entries.extend([x for x in TaskDatabase.get_instance().tasks.values()])
            database_entries.extend([x for x in GroupDatabase.get_instance().groups.values()])
            database_entries.extend([x for x in PacketDatabase.get_instance().packets.values()])

            self.database = {}

            for x in database_entries:
                class_file = Path(inspect.getfile(x.__class__))
                data = class_file.read_bytes()
                hash = SHA512.new(data=data).digest()
                hash = base64.b64encode(hash).decode("utf-8")

                # Used when locally changing the root database files for debugging
                self.database[x.name] = hash

        return self

    def serialize(self) -> dict:
        return {
            "version": self.version,
            "database": self.database,
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

