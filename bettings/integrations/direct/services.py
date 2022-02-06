import logging
from bettings.integrations.direct import factory as api_bet_place_factory

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[API-BET-PLACE-SERVICES]"


def get_client_all_match_odds_by_sport(client, sport):
    api_integration_client = api_bet_place_factory.Factory().create(client, sport)
    # TODO: add client init selenium
    try:
        return api_integration_client.get_matches_odds_all()
    # Check all exceptions and catch specific ones
    except Exception as e:
        logger.exception("{} Unable to fetch match odds for client {}".format(_LOG_PREFIX, client.name))