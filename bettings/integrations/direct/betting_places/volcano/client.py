import datetime
import logging

from django.conf import settings
import simplejson

from bettings import enums as betting_enums
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.direct import exceptions as direct_exceptions
from bettings.integrations.direct.betting_places import base as base_client

logger = logging.getLogger(__name__)
_LOG_PREFIX = '[VOLCANO-API-CLIENT]'


class VolcanoApiSoccerClient(base_client.ApiBaseClient):

    NUMBER_OF_FETCH_DAYS = None
    API_PARAMS = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.VOLCANO.name][betting_enums.Sports.FOOTBALL.name]['params']
    API_URL = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.VOLCANO.name][betting_enums.Sports.FOOTBALL.name]['url']

    def __init__(self):
        super(VolcanoApiSoccerClient, self).__init__()

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

        return raw_matches.get('locations')

    @classmethod
    def _prepare_request_params(cls):
        # prepare from and to date // update params for request
        from_date = datetime.datetime.now()
        to_date = from_date + datetime.timedelta(days=3)

        cls.API_PARAMS.update(
            {
                'from': from_date.strftime('%Y-%m-%dT%H:%M:00.000Z'),
                'to': to_date.strftime('%Y-%m-%dT%H:%M:00.000Z'),
            }
        )

        return cls.API_PARAMS

    @classmethod
    def _parse_matches_data(cls, raw_location_league_matches):
        all_matches = []
        for location in raw_location_league_matches:
            location_name = location.get('name')
            leagues = location.get('leagues')

            if not leagues:
                logger.info('{} There are no events for selected timeframe in league {}. Continue.'.format(_LOG_PREFIX, location_name))
                continue

            for league in leagues:
                league_name = league.get('name')
                league_event_groups = league.get('eventDateGroups')

                if not league_event_groups:
                    logger.info('{} There are no events for selected timeframe in league {}. Continue.'.format(_LOG_PREFIX, league_name))
                    continue

                for event_group in league_event_groups:
                    for event in event_group.get('events'):
                        match_information = cls._parse_match_data(league_name, event)
                        if not match_information:
                            continue
                        all_matches.append(match_information)

        return all_matches

    @classmethod
    def _parse_match_data(cls, league_name, event_information):
        player_home, player_away = cls._get_players(event_information.get('fixture', {}))
        date_time = cls._get_match_date_time(event_information.get('fixture', {}).get('startDate'))
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
                'bet_odds': cls._get_match_odds(event_information.get('markets', [])),
            }
        except Exception as e:
            print("Exc", event_information)
            return None
        return match_odds

    @staticmethod
    def _get_players(match_information):
        participants = match_information.get('participants')
        return participants[0].get('name'), participants[1].get('name')

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

        base_game_odd_info = {}
        double_chance_odd_info = {}
        for market in match_odd_information:
            if market.get('name') == 'Osnovna ponuda':
                base_game_odd_info = market.get('picks', {})

            if market.get('name') == 'Dupla šansa':
                double_chance_odd_info = market.get('picks', {})
        odds = {}

        for odd in base_game_odd_info:
            if odd.get('name') == '1':
                odds[bet_place_enums.FootballMatchPlays.ONE.value] = odd.get('odds')
            if odd.get('name') == '2':
                odds[bet_place_enums.FootballMatchPlays.TWO.value] = odd.get('odds')
            if odd.get('name') == 'x':
                odds[bet_place_enums.FootballMatchPlays.X.value] = odd.get('odds')

        for odd in double_chance_odd_info:
            if odd.get('name') == '1x':
                odds[bet_place_enums.FootballMatchPlays.ONEX.value] = odd.get('odds')
            if odd.get('name') == '12':
                odds[bet_place_enums.FootballMatchPlays.ONETWO.value] = odd.get('odds')
            if odd.get('name') == 'x2':
                odds[bet_place_enums.FootballMatchPlays.XTWO.value] = odd.get('odds')

        return odds