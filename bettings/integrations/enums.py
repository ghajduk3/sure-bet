import enum

from bettings import enums as betting_enums


class FootballMatchPlays(enum.Enum):
    ONE = '1'
    X = 'x'
    TWO = '2'
    ONEX = '1x'
    XTWO = 'x2'
    ONETWO = '12'

    @staticmethod
    def get_description():
        return [play.value for play in FootballMatchPlays]


class BettingInstitutions(betting_enums.ChoiceEnums):
    OLIMPWIN = 1
    ZLATNIK = 2
    ADMIRAL = 3
    MERIDIAN = 4
    VOLCANO = 5
    SBBET = 6
    PREMIER = 7
    SANSA = 8
    LOB = 9
    LVBET = 10
    MAXBET = 11

    def get_description(self):
        _descriptions = {
            self.OLIMPWIN: "OLIMP",
            self.ZLATNIK: "ZLATNIK",
            self.ADMIRAL: "ADMIRAL",
            self.MERIDIAN: "MERIDIAN",
            self.VOLCANO: "VOLCANO",
            self.SBBET: "SBBET",
            self.PREMIER: "PREMIER",
            self.SANSA: "SANSA",
            self.LOB: "LOB",
            self.LVBET: 'LVBET',
            self.MAXBET: 'MAXBET',
        }
        return _descriptions.get(self)


class HttpRequestMethods(enum.Enum):
    GET = 'GET'
    POST = 'POST'
