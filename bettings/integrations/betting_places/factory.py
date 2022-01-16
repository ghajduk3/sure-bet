import logging
from typing import Union

from bettings import enums as betting_enums
from bettings.integrations.betting_places import exceptions as bet_place_exceptions
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places.admiral.client import AdmiralSoccerClient
from bettings.integrations.betting_places.olimpwin.client import OlimpSoccerClient
from bettings.integrations.betting_places.zlatnik import client as zlatnik_client
from bettings.integrations.betting_places.olimpwin import client as olimp_client
from bettings.integrations.betting_places.admiral import client as admiral_client
from bettings.integrations.betting_places.zlatnik.client import ZlatnikSoccerClient

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[CLIENT_FACTORY]"


class Factory:

    _client_sport_mapping = {
        betting_enums.Sports.FOOTBALL: {
            bet_place_enums.BettingInstitutions.OLIMPWIN: olimp_client.OlimpSoccerClient,
            bet_place_enums.BettingInstitutions.ZLATNIK: zlatnik_client.ZlatnikSoccerClient,
            bet_place_enums.BettingInstitutions.ADMIRAL: admiral_client.AdmiralSoccerClient,
        }
    }

    def create(self, client, sport):
        # type: (bet_place_enums.BettingInstitutions, betting_enums.Sports) -> Union[OlimpSoccerClient, ZlatnikSoccerClient, AdmiralSoccerClient]

        # TODO: Add clients constants
        sport_clients = self._client_sport_mapping.get(sport)
        if not sport_clients:
            raise bet_place_exceptions.BetIntegrationClientNotFound("{} There are no clients for sport {}".format(_LOG_PREFIX, sport.name))

        client = sport_clients.get(client)
        if not client:
            raise bet_place_exceptions.BetIntegrationClientNotFound("{} Client {} is not found for sport {}".format(_LOG_PREFIX, client.name, sport.name))

        try:
            return client()
        except Exception as e:
            logger.exception("{} Client initialization error".format(_LOG_PREFIX))
