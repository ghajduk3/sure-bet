from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.services import matches as match_service


def populate_data():

    match_service_client = match_service.MatchProcessing()

    bet_places = [
        bet_place_enums.BettingInstitutions.OLIMPWIN,
        bet_place_enums.BettingInstitutions.ADMIRAL,
        bet_place_enums.BettingInstitutions.SBBET,
        bet_place_enums.BettingInstitutions.ZLATNIK,
        bet_place_enums.BettingInstitutions.VOLCANO,
        bet_place_enums.BettingInstitutions.MERIDIAN,
    ]
    for bet_place in bet_places:
        print("Fetching data from {}".format(bet_place.name))
        match_service_client.process_matches(bet_place, betting_enums.Sports.FOOTBALL)

if __name__ == '__main__':
    populate_data()