

class BasePacket:
    def get_type(self) -> str:
        raise NotImplementedError()

    def deserialize(self, data: dict):
        pass

    def serialize(self) -> dict:
        return {
            "_type": self.get_type()
        }

    @property
    def name(self) -> str:
        return self.get_type()

    def new_instance(self) -> "BasePacket":
        raise NotImplementedError()

