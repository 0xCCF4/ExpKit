

class BasePacket:
    def get_type(self) -> str:
        raise NotImplementedError()

    def deserialize(self, data: dict) -> any:
        pass

    def serialize(self) -> dict:
        return {
            "_type": self.get_type()
        }
