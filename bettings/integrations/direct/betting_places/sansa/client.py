import datetime
import logging

from django.conf import settings
import simplejson

from bettings import enums as betting_enums
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.direct import exceptions as direct_exceptions
from bettings.integrations.direct.betting_places import base as base_client
from bettings.integrations.direct import constants as direct_constants

logger = logging.getLogger(__name__)
_LOG_PREFIX = '[SANSA-API-CLIENT]'


class SansaApiSoccerClient(base_client.ApiBaseClient):

    NUMBER_OF_FETCH_DAYS = None
    API_URL_EVENTS = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.SANSA.name][betting_enums.Sports.FOOTBALL.name]['url']['events']
    API_URL_LEAGUES = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.SANSA.name][betting_enums.Sports.FOOTBALL.name]['url']['leagues']

    def __init__(self):
        super(SansaApiSoccerClient, self).__init__()

    def get_matches_odds_all(self, number_of_days=3):
        self.NUMBER_OF_FETCH_DAYS = number_of_days
        league_name_ids = self._parse_league_information()

        if not league_name_ids:
            logger.info('{} There are no leagues to be parsed'.format(_LOG_PREFIX))
            return {}

        return self._parse_matches_data(league_name_ids)

    @classmethod
    def _get_raw_league_information(cls):
        # Request to the url
        league_information = simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.POST.value,
                url=cls.API_URL_LEAGUES,
                data="{\"filter\":\"0\",\"activeStyle\":\"img/sports\"}",
                headers={
                      'Content-Type': 'application/json',
                    }
            ).content
        )
        return league_information

    @classmethod
    def _parse_league_information(cls):
        # get the raw data
        # parse raw data and return league ids with events
        raw_league_information = cls._get_raw_league_information()
        football_information = None
        all_league_ids = []
        for sport in raw_league_information:
            if sport.get('SID') == direct_constants.SANSA_SPORT_FOOTBALL_ID:
                football_information = sport

        if not football_information:
            msg = '{} There are no data for football league ids'.format(_LOG_PREFIX)
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for league in football_information.get('L', []):
            if not league:
                msg = '{} There are no data for football league ids'.format(_LOG_PREFIX)
                logger.exception(msg)
                raise direct_exceptions.ApiNoDataError(msg)

            league_name = league.get('LN')
            league_id = league.get('LID')
            all_league_ids.append((league_name, league_id))

        return all_league_ids


    @classmethod
    def _parse_matches_data(cls, league_ids_with_names):
        raw_league_with_matches = cls._get_raw_match_events(league_ids_with_names)
        all_league_odd_events = []
        if not raw_league_with_matches:
            msg = '{} There are no league matches.'.format(_LOG_PREFIX)
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for league in raw_league_with_matches:
            try:
                odd_events = cls._parse_league_matches(league)
                all_league_odd_events.extend(odd_events)
            except Exception as e:
                print("Error while fetching match data for league", str(e))
                continue

        return all_league_odd_events

    @classmethod
    def _parse_league_matches(cls, league_information):
        all_matches = []
        league_name = league_information.get('LN')
        for match in league_information.get('P', []):
            try:
                player_home, player_away = cls._get_players(match.get('PN'))
                date_time = cls._get_match_date_time(match.get('DI'))
                match_odds = cls._get_match_odds(match.get('T', []))
                all_matches.append(
                    {
                    'player_home': cls._get_normalized_soccer_team_info(player_home),
                    'player_away': cls._get_normalized_soccer_team_info(player_away),
                    'player_home_display': player_home,
                    'player_away_display': player_away,
                    'sport': betting_enums.Sports.FOOTBALL,
                    'league': league_name,
                    'tournament': '',
                    'date_time': date_time,
                    'bet_odds': match_odds,
                }
                )
            except Exception as e:
                continue

        return all_matches

    @classmethod
    def _get_raw_match_events(cls, league_ids_with_names):
        league_ids = list(map(lambda pair: pair[1], league_ids_with_names))
        return simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.POST.value,
                url=cls.API_URL_EVENTS,
                data='{' + 'LigaID: {},filter: "0",parId: 0'.format(league_ids) + '}',
                headers={
                    'Content-Type': 'application/json',
                    'Cookie': 'ASP.NET_SessionId=w034vvwwulfv0s23dt4unajx'
                }
            ).content
        )

    @classmethod
    def _get_players(cls, player_info):
        return player_info.replace(' ', '').split(':')

    @classmethod
    def _get_match_date_time(cls, date_time_info):
        return datetime.datetime.strptime(date_time_info, direct_constants.SANSA_PARSE_DATE_FORMAT) - datetime.timedelta(hours=1)

    @classmethod
    def _get_match_odds(cls, match_odd_information):
        odds = {}
        for odd in match_odd_information:
            if odd.get('TP') == '1':
                odds[bet_place_enums.FootballMatchPlays.ONE.value] = float(odd.get('K'))
            if odd.get('TP') == '2':
                odds[bet_place_enums.FootballMatchPlays.TWO.value] = float(odd.get('K'))
            if odd.get('TP') == 'X':
                odds[bet_place_enums.FootballMatchPlays.X.value] = float(odd.get('K'))
            if odd.get('TP') == '1X':
                odds[bet_place_enums.FootballMatchPlays.ONEX.value] = float(odd.get('K'))

            if odd.get('TP') == 'X2':
                odds[bet_place_enums.FootballMatchPlays.XTWO.value] = float(odd.get('K'))

            odds[bet_place_enums.FootballMatchPlays.ONETWO.value] = 0.0

        return odds
