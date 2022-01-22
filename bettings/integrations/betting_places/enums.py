import enum

from bettings import enums as betting_enums

class FootballMatchPlays(enum.Enum):
    ONE = '1'
    X = 'x'
    TWO = '2'
    ONEX = '1x'
    XTWO = 'x2'
    ONETWO = '12'


class BettingInstitutions(betting_enums.ChoiceEnums):
    OLIMPWIN = 1
    ZLATNIK = 2
    ADMIRAL = 3
    MERIDIAN = 4

    def get_description(self):
        _descriptions = {
            self.OLIMPWIN: "OLIMP",
            self.ZLATNIK: "ZLATNIK",
            self.ADMIRAL: "ADMIRAL",
        }
        return _descriptions.get(self)