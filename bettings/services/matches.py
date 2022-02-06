import random
import logging

from bettings.services.data import matches as matches_data_service
from bettings.services.data import odds as odds_data_service

from bettings.integrations import services as bet_integration_services

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[MATCH-PROCESSING-SERVICE]"


class MatchProcessing:
    def __init__(self):
        self._batch = random.randint(0, 1000000)

    def process_matches(self, client, sport):
        logger.info("{} Started match processing for client {} and sport {}.".format(_LOG_PREFIX, client.name, sport.name))
        all_match_odds = bet_integration_services.get_client_all_match_odds_by_sport(client, sport)
        logger.info("{} Found {} matches for client {} and sport {}.".format(_LOG_PREFIX, len(all_match_odds), client.name, sport.name))

        for match in all_match_odds:
            match_odds = match.pop('bet_odds', {})
            match_created = matches_data_service.get_or_create_match(match, self._batch, client.value)

            if not match_created:
                continue

            odds_data_service.update_or_create_bet_odds(client, match_odds, match_created.id)
            logger.info("{} Processed match id={}.".format(_LOG_PREFIX, match_created.id))







