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
_LOG_PREFIX = '[MAXBET-API-CLIENT]'


class MaxBetApiSoccerClient(base_client.ApiBaseClient):

    NUMBER_OF_FETCH_DAYS = None
    API_URL_EVENTS = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.MAXBET.name][betting_enums.Sports.FOOTBALL.name]['url']

    def __init__(self):
        super(MaxBetApiSoccerClient, self).__init__()

    def get_matches_odds_all(self, number_of_days=3):
        self.NUMBER_OF_FETCH_DAYS = number_of_days

        all_odd_events = {}

        try:
            base_odd_events = self._parse_league_matches_base_bet()
            all_odd_events.update(self._parse_league_matches_double_chance_bet(base_odd_events))
        except Exception as e:
            print("Error while fetching parsing data", str(e))

        return list(all_odd_events.values())

    @classmethod
    def _get_raw_league_matches_per_bet(cls, bet_code):
        url = cls.API_URL_EVENTS
        # get all matches from the api
        raw_matches = simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.GET.value,
                url=url.format(bet_code=bet_code),
            ).content
        )

        return raw_matches


    @classmethod
    def _parse_league_matches_base_bet(cls):
        raw_match_events_base = cls._get_raw_league_matches_per_bet(direct_constants.MAXBET_BASE_ODDS_CODE)

        all_base_bets = {}

        if not raw_match_events_base:
            msg = '{} There are no match events for today {}'.format(_LOG_PREFIX, datetime.date.today())
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for league in raw_match_events_base:
            league_name = league.get('name')

            matches = league.get('matchList', [])

            if not matches:
                msg = '{} There are no matches for league {}'.format(_LOG_PREFIX, league_name)
                logger.exception(msg)
                raise direct_exceptions.ApiNoDataError(msg)

            for match in matches:
                try:
                    player_home = match.get('home')
                    player_away = match.get('away')
                    date_time = cls._get_match_date_time(match.get('kickOffTimeString'))
                    match_odds = cls._get_match_base_odds(match.get('odBetPickGroups', [])[0])
                    event_name = player_home + ' ' + player_away

                    all_base_bets[event_name] = {
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
                except Exception as e:
                    print("Exception occured while parsing match {}. Error: {}".format(event_name, str(e)))
                    continue
        return all_base_bets



    @classmethod
    def _get_match_base_odds(cls, base_odd_informations):
        if not base_odd_informations:
            msg = 'No base oddd data.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)

        odds = {}
        for odd in base_odd_informations.get('tipTypes'):
            if odd.get('tipType') == 'KI_1':
                odds[bet_place_enums.FootballMatchPlays.ONE.value] = odd.get('value')
            if odd.get('tipType') == 'KI_X':
                odds[bet_place_enums.FootballMatchPlays.X.value] = odd.get('value')
            if odd.get('tipType') == 'KI_2':
                odds[bet_place_enums.FootballMatchPlays.TWO.value] = odd.get('value')

        return odds

    @classmethod
    def _get_match_double_chance_odds(cls, double_chance_odd_informations):
        if not double_chance_odd_informations:
            msg = 'No base oddd data.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)
        odds = {}

        for odd in double_chance_odd_informations.get('tipTypes'):
            if odd.get('tipType') == 'DS_1X':
                odds[bet_place_enums.FootballMatchPlays.ONEX.value] = odd.get('value')
            if odd.get('tipType') == 'DS_12':
                odds[bet_place_enums.FootballMatchPlays.ONETWO.value] = odd.get('value')
            if odd.get('tipType') == 'DS_X2':
                odds[bet_place_enums.FootballMatchPlays.XTWO.value] = odd.get('value')
        return odds

    @classmethod
    def _get_players(cls, team_information):
        return team_information[0].get('name'), team_information[1].get('name')

    @staticmethod
    def _get_match_date_time(date_time):
        if not date_time:
            msg = 'No date_time information.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)

        return datetime.datetime.strptime('2022.' + str(date_time), direct_constants.LOB_DATE_FORMAT) - datetime.timedelta(hours=1)

    @classmethod
    def _parse_league_matches_double_chance_bet(cls, base_odds):
        raw_match_events_base = cls._get_raw_league_matches_per_bet(direct_constants.MAXBET_DOUBLE_CHANCE_CODE)

        if not raw_match_events_base:
            msg = '{} There are no match events for today {}'.format(_LOG_PREFIX, datetime.date.today())
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for league in raw_match_events_base:
            league_name = league.get('name')

            matches = league.get('matchList', [])

            if not matches:
                msg = '{} There are no matches for league {}'.format(_LOG_PREFIX, league_name)
                logger.exception(msg)
                raise direct_exceptions.ApiNoDataError(msg)

            for match in matches:
                try:
                    player_home = match.get('home')
                    player_away = match.get('away')
                    match_odds = cls._get_match_double_chance_odds(match.get('odBetPickGroups', [])[0])
                    event_name = player_home + ' ' + player_away
                    base_odds[event_name]['bet_odds'].update(match_odds)
                except Exception as e:
                    print("Exception occured while parsing match {}".format(event_name))
                    continue

        return base_odds
