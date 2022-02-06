import datetime
import logging

from django.conf import settings
import simplejson

from bettings import enums as betting_enums
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.direct import exceptions as direct_exceptions
from bettings.integrations.direct.betting_places import base as base_client

logger = logging.getLogger(__name__)
_LOG_PREFIX = '[ZLATNIK-API-CLIENT]'


class ZlatnikApiSoccerClient(base_client.ApiBaseClient):

    NUMBER_OF_FETCH_DAYS = None
    API_PARAMS = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.ZLATNIK.name][betting_enums.Sports.FOOTBALL.name]['params']
    API_URL = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.ZLATNIK.name][betting_enums.Sports.FOOTBALL.name]['url']

    def __init__(self):
        super(ZlatnikApiSoccerClient, self).__init__()

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
                params=cls._prepare_request_params(),
            ).content
        )

        return raw_matches.get('Response')

    @classmethod
    def _prepare_request_params(cls):
        # prepare from and to date // update params for request
        from_date = datetime.datetime.now()
        to_date = from_date + datetime.timedelta(days=3)

        cls.API_PARAMS.update(
            {
                'DateFrom': from_date.strftime('%Y-%m-%dT%H:%M:00.000Z'),
                'DateTo': to_date.strftime('%Y-%m-%dT%H:%M:00.000Z'),
            }
        )

        return cls.API_PARAMS

    @classmethod
    def _parse_matches_data(cls, raw_league_matches):
        all_matches = []
        for response in raw_league_matches:
            response_name = response.get('Name')
            categories = response.get('Categories')

            if not categories:
                logger.info('{} There are no events for selected timeframe in response {}. Continue.'.format(_LOG_PREFIX, response_name))
                continue

            for category in categories:
                category_name = category.get('Name')
                # league_event_groups = league.get('eventDateGroups')
                leagues = category.get('Leagues')

                if not leagues:
                    logger.info(
                        '{} There are no leagues for selected timeframe in category {}. Continue.'.format(_LOG_PREFIX,
                                                                                                       category_name))
                    continue

                for league in leagues:
                    league_name = league.get('Name')
                    matches = league.get('Matches')
                    if not matches:
                        logger.info('{} There are no events for selected timeframe in league {}. Continue.'.format(_LOG_PREFIX, league_name))
                        continue

                    for match in matches:
                        match_information = cls._parse_match_data(league_name, match)
                        if not match_information:
                            continue
                        all_matches.append(match_information)

        return all_matches

    @classmethod
    def _parse_match_data(cls, league_name, event_information):
        player_home, player_away = cls._get_players(event_information)
        date_time = cls._get_match_date_time(event_information.get('MatchStartTime'))
        try:
            match_odds = {
                'player_home': cls._get_normalized_soccer_team_info(player_home),
                'player_away': cls._get_normalized_soccer_team_info(player_away),
                'player_home_display': player_home,
                'player_away_display': player_away,
                'sport': betting_enums.Sports.FOOTBALL,
                'league': league_name,
                'tournament': '',
                'date_time': date_time,
                'bet_odds': cls._get_match_odds(event_information.get('BasicOffer', {})),
            }
        except Exception as e:
            print("Exc", event_information)
            return None
        return match_odds

    @staticmethod
    def _get_players(match_information):
        return match_information.get('TeamHome'), match_information.get('TeamAway')

    @staticmethod
    def _get_match_date_time(date_time):
        if not date_time:
            msg = 'No date_time information.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)

        return datetime.datetime.strptime(date_time, '%Y-%m-%dT%H:%M:00Z')

    @staticmethod
    def _get_match_odds(match_odd_information):
        if not match_odd_information:
            msg = 'There are no odds data'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)

        odds = {}

        for odd in match_odd_information.get('Odds'):
            if odd.get('Name') == '1':
                odds[bet_place_enums.FootballMatchPlays.ONE.value] = odd.get('Odd')
            if odd.get('Name') == '2':
                odds[bet_place_enums.FootballMatchPlays.TWO.value] = odd.get('Odd')
            if odd.get('Name') == 'X':
                odds[bet_place_enums.FootballMatchPlays.X.value] = odd.get('Odd')
            if odd.get('Name') == '1X':
                odds[bet_place_enums.FootballMatchPlays.ONEX.value] = odd.get('Odd')
            if odd.get('Name') == '12':
                odds[bet_place_enums.FootballMatchPlays.ONETWO.value] = odd.get('Odd')
            if odd.get('Name') == 'X2':
                odds[bet_place_enums.FootballMatchPlays.XTWO.value] = odd.get('Odd')

        return odds