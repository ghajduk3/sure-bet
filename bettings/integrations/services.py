import logging

from bettings.integrations import enums as bet_place_enums
from bettings.integrations import constants
from bettings.integrations.scrapers import factory as scraper_bet_place_factory
from bettings.integrations.direct import factory as api_bet_place_factory

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[BET-PLACE-SERVICES]"


def get_client_all_match_odds_by_sport(client, sport):
    api_client_flag = True if client in constants.API_CLIENTS else False
    integration_client = api_bet_place_factory.Factory().create(client, sport) if api_client_flag else scraper_bet_place_factory.Factory().create(client, sport)
    # TODO: add client init selenium
    try:
        return integration_client.get_matches_odds_all()
    # Check all exceptions and catch specific ones
    except Exception as e:
        logger.exception("{} Unable to fetch match odds for client {}".format(_LOG_PREFIX, client.name))