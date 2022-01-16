import enum


class ChoiceEnums(enum.IntEnum):
    @classmethod
    def get_description(cls):
        raise NotImplementedError("get_description is not implemented")

    @classmethod
    def choices(cls):
        return [(choice.value, choice.get_description()) for choice in cls]


class Sports(ChoiceEnums):
    FOOTBALL = 1

    def get_description(self):
        _descriptions = {self.FOOTBALL: "FOOTBALL"}
        return _descriptions.get(self)


