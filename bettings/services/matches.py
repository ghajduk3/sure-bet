from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.services.data import matches as matches_data_service
from bettings.services.data import odds as odds_data_service

from bettings.integrations import services as bet_integration_services


class MatchProcessing:
    @classmethod
    def create_matches(cls):
        # get matches for all sports for all clients
        for sport in betting_enums.Sports:
            for client in [bet_place_enums.BettingInstitutions.MERIDIAN]:
                cls._process_matches(client, sport)

    @staticmethod
    def _process_matches(client, sport):
        # find match if exists update time if changed
        #     Add or update odds for specific client
        all_match_odds = bet_integration_services.get_client_all_match_odds_by_sport(client, sport)

        for match in all_match_odds:
            match_odds = match.pop('bet_odds', {})
            existing_match = matches_data_service.find_match_by_filters(
                **{
                    'player_home': match.get('player_home'),
                    'player_away': match.get('player_away'),
                    'sport': match.get('sport'),
                }
            )

            if not existing_match:
                existing_match = matches_data_service.create_match(match)
                if not existing_match:
                    continue

            print("Match", existing_match.id, match.get('player_home'), match.get('player_away'), match_odds)
            odds_data_service.update_or_create_bet_odds(client, match_odds, existing_match.id)








