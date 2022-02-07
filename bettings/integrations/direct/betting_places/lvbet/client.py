import datetime
import logging

from django.conf import settings
import simplejson

from bettings import enums as betting_enums
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.direct import exceptions as direct_exceptions
from bettings.integrations.direct import constants as direct_constants

from bettings.integrations.direct.betting_places import base as base_client

logger = logging.getLogger(__name__)
_LOG_PREFIX = '[LVBET-API-CLIENT]'


class LVBetApiSoccerClient(base_client.ApiBaseClient):

    NUMBER_OF_FETCH_DAYS = None
    API_URL = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.LVBET.name][betting_enums.Sports.FOOTBALL.name]['url']

    def __init__(self):
        super(LVBetApiSoccerClient, self).__init__()

    def get_matches_odds_all(self, number_of_days=3):
        self.NUMBER_OF_FETCH_DAYS = number_of_days
        raw_leagues_with_matches = self._get_raw_leagues_with_matches()

        if not raw_leagues_with_matches:
            logger.info('{} There are no matches to be parsed'.format(_LOG_PREFIX))
            return {}

        return self._parse_matches_data(raw_leagues_with_matches)

    @classmethod
    def _get_raw_leagues_with_matches(cls):
        # get all matches from the api
        raw_matches = simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.GET.value,
                url=cls.API_URL,
            ).content
        )

        return raw_matches

    @classmethod
    def _parse_matches_data(cls, raw_location_league_matches):
        all_matches = []

        for match in raw_location_league_matches:
            try:
                league_name = match.get('sportsGroups',[])[2].get('name')
                player_home, player_away = cls._get_players(match.get('participants', {}))
                date_time = cls._get_match_date_time(match.get('date', ''))
                match_odds = {
                    'player_home': cls._get_normalized_soccer_team_info(player_home),
                    'player_away': cls._get_normalized_soccer_team_info(player_away),
                    'player_home_display': player_home,
                    'player_away_display': player_away,
                    'sport': betting_enums.Sports.FOOTBALL,
                    'league': league_name,
                    'tournament': '',
                    'date_time': date_time,
                    'bet_odds': cls._get_match_odds(match.get('primaryMarkets', [])),
                }
                all_matches.append(match_odds)
            except Exception as e:
                print("Exception while parsin match. Error: {}".format(str(e)))
                continue
        return all_matches


    @staticmethod
    def _get_players(participants):
        return participants.get('home'), participants.get('away')

    @staticmethod
    def _get_match_date_time(date_time):
        if not date_time:
            msg = 'No date_time information.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)

        return datetime.datetime.strptime(date_time, '%Y-%m-%dT%H:%M:00+00:00')

    @staticmethod
    def _get_match_odds(match_odd_information):
        if not match_odd_information:
            msg = 'There are no odds data'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)

        base_game_odd_info = {}
        double_chance_odd_info = {}
        for market in match_odd_information:
            if market.get('marketTypeId') == direct_constants.LVBET_BASE_ODDS_CODE:
                base_game_odd_info = market.get('selections', {})

            if market.get('marketTypeId') == direct_constants.LVBET_DOUBLE_CHANCE_ODDS_CODE:
                double_chance_odd_info = market.get('selections', {})
        odds = {}

        for odd in base_game_odd_info:
            if odd.get('order') == 1:
                odds[bet_place_enums.FootballMatchPlays.ONE.value] = odd.get('rate', {}).get('decimal')
            if odd.get('order') == 3:
                odds[bet_place_enums.FootballMatchPlays.TWO.value] = odd.get('rate', {}).get('decimal')
            if odd.get('order') == 2:
                odds[bet_place_enums.FootballMatchPlays.X.value] = odd.get('rate', {}).get('decimal')

        for odd in double_chance_odd_info:
            if odd.get('order') == 1:
                odds[bet_place_enums.FootballMatchPlays.ONEX.value] = odd.get('rate', {}).get('decimal')
            if odd.get('order') == 2:
                odds[bet_place_enums.FootballMatchPlays.ONETWO.value] = odd.get('rate', {}).get('decimal')
            if odd.get('order') == 3:
                odds[bet_place_enums.FootballMatchPlays.XTWO.value] = odd.get('rate', {}).get('decimal')

        return odds