from bettings.integrations import enums as bet_place_enums
# FETCH 3 DAYS OF BETS
BET_DAY_FETCH_LIMIT=1

API_CLIENTS = [
        bet_place_enums.BettingInstitutions.VOLCANO,
        bet_place_enums.BettingInstitutions.ZLATNIK,
        bet_place_enums.BettingInstitutions.MERIDIAN,
        bet_place_enums.BettingInstitutions.SANSA,
]

SCRAPER_CLIENTS = [
    bet_place_enums.BettingInstitutions.SBBET,
    bet_place_enums.BettingInstitutions.OLIMPWIN,
    bet_place_enums.BettingInstitutions.ADMIRAL,
]

