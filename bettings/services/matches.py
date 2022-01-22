import random

from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.services.data import matches as matches_data_service
from bettings.services.data import odds as odds_data_service

from bettings.integrations import services as bet_integration_services


class MatchProcessing:
    def __init__(self):
        self._batch = random.randint(0, 1000000)

    def create_matches(self):
        # get matches for all sports for all clients
        for sport in betting_enums.Sports:
            for client in bet_place_enums.BettingInstitutions:
                self._process_matches(client, sport)

    def _process_matches(self, client, sport):
        # find match if exists update time if changed
        #     Add or update odds for specific client
        all_match_odds = bet_integration_services.get_client_all_match_odds_by_sport(client, sport)

        for match in all_match_odds:
            match_odds = match.pop('bet_odds', {})

            match_object = matches_data_service.get_or_create_match(match, self._batch, client.value)

            print("Match", match_object.id, match.get('player_home'), match.get('player_away'), match_odds)
            odds_data_service.update_or_create_bet_odds(client, match_odds, match_object.id)








