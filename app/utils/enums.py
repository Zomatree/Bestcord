class Enum:
    def items(self):
        return [(key, value) for key, value in self.__dict__.items() if not callable(value) and not key.startswith("__")]

    def values(self):
        return [item[0] for item in self.items()]

    def keys(self):
        return [item[1] for item in self.items()]

class ChannelType(Enum):
    text = 0
    dm = 1
    voice = 2
    dm = 3
    category = 4
    news = 5
    news_thread = 10
    public_thread = 11
    private_thread = 12
    stage = 13
