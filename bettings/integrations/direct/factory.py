import logging
from typing import Union

from bettings import enums as betting_enums
from bettings.integrations.scrapers import exceptions as bet_place_exceptions
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.direct.betting_places.volcano import client as volcano_client
from bettings.integrations.direct.betting_places.zlatnik import client as zlatnik_client
from bettings.integrations.direct.betting_places.meridian import client as meridian_client
from bettings.integrations.direct.betting_places.sansa import client as sansa_client
from bettings.integrations.direct.betting_places.lob import client as lob_client
from bettings.integrations.direct.betting_places.lvbet import client as lvbet_client
from bettings.integrations.direct.betting_places.maxbet import client as maxbet_client



logger = logging.getLogger(__name__)
_LOG_PREFIX = "[API-CLIENT-FACTORY]"


class Factory:

    _client_sport_mapping = {
        betting_enums.Sports.FOOTBALL: {
            bet_place_enums.BettingInstitutions.VOLCANO: volcano_client.VolcanoApiSoccerClient,
            bet_place_enums.BettingInstitutions.ZLATNIK: zlatnik_client.ZlatnikApiSoccerClient,
            bet_place_enums.BettingInstitutions.MERIDIAN: meridian_client.MeridianApiSoccerClient,
            bet_place_enums.BettingInstitutions.SANSA: sansa_client.SansaApiSoccerClient,
            bet_place_enums.BettingInstitutions.LOB: lob_client.LobApiSoccerClient,
            bet_place_enums.BettingInstitutions.LVBET: lvbet_client.LVBetApiSoccerClient,
            bet_place_enums.BettingInstitutions.MAXBET: maxbet_client.MaxBetApiSoccerClient,
        }
    }

    def create(self, client, sport):
        # TODO: Add clients constants
        sport_clients = self._client_sport_mapping.get(sport)
        if not sport_clients:
            raise bet_place_exceptions.BetIntegrationClientNotFound("{} There are no clients for sport {}".format(_LOG_PREFIX, sport.name))

        bet_client = sport_clients.get(client)
        if not bet_client:
            raise bet_place_exceptions.BetIntegrationClientNotFound("{} Client {} is not found for sport {}".format(_LOG_PREFIX, client.name, sport.name))

        try:
            return bet_client()
        except Exception as e:
            logger.exception("{} Client initialization error".format(_LOG_PREFIX))