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
_LOG_PREFIX = '[MERIDIAN-API-CLIENT]'


class MeridianApiSoccerClient(base_client.ApiBaseClient):

    NUMBER_OF_FETCH_DAYS = None
    API_URL_EVENTS = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.MERIDIAN.name][betting_enums.Sports.FOOTBALL.name]['url']['events']
    API_URL_LEAGUES = settings.DIRECT_CLIENT_SPORT_URLS[
        bet_place_enums.BettingInstitutions.MERIDIAN.name][betting_enums.Sports.FOOTBALL.name]['url']['leagues']

    def __init__(self):
        super(MeridianApiSoccerClient, self).__init__()

    def get_matches_odds_all(self, number_of_days=3):
        self.NUMBER_OF_FETCH_DAYS = number_of_days
        league_name_ids = self._parse_league_information()

        if not league_name_ids:
            logger.info('{} There are no leagues to be parsed'.format(_LOG_PREFIX))
            return {}

        all_match_data = self._parse_matches_data(league_name_ids)
        return list(all_match_data.values())

    @classmethod
    def _get_raw_league_information(cls):
        # Request to the url
        league_information = simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.GET.value,
                url=cls.API_URL_LEAGUES,
            ).content
        )
        return league_information.get('sports')

    @classmethod
    def _parse_league_information(cls):
        # get the raw data
        # parse raw data and return league ids with events
        raw_league_information = cls._get_raw_league_information()
        football_information = None
        all_league_ids = []
        for sport in raw_league_information:
            if sport.get('id') == direct_constants.MERIDIAN_SPORT_FOOTBALL_ID:
                football_information = sport

        if not football_information:
            msg = '{} There are no data for football league ids'.format(_LOG_PREFIX)
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for region in football_information.get('regions', []):
            if not region:
                msg = '{} There are no data for football league ids'.format(_LOG_PREFIX)
                logger.exception(msg)
                raise direct_exceptions.ApiNoDataError(msg)

            for league in region.get('leagues', []):
                number_of_events = league.get('numberOfEvents')
                if number_of_events > 1:
                    league_name = league.get('name')
                    league_id = league.get('id')
                    all_league_ids.append((league_name, league_id))

        return all_league_ids

    @classmethod
    def _get_raw_league_matches_per_bet(cls):
        # get all matches from the api
        raw_matches = simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.GET.value,
                url=cls.API_URL_EVENTS,
            ).content
        )

        return raw_matches.get('locations')

    @classmethod
    def _parse_matches_data(cls, league_ids_with_names):
        all_odd_events = {}

        for league_name, league_id in league_ids_with_names:
            try:
                base_odd_events = cls._parse_league_matches_base_bet(league_name, league_id)
                all_odd_events.update(cls._parse_league_matches_double_chance_bet(league_name, league_id, base_odd_events))
            except Exception as e:
                print("Error while fetching match data for league", league_name, str(e))
                continue

        return all_odd_events

    @classmethod
    def _parse_league_matches_base_bet(cls, league_name, league_id):
        base_url = cls._get_parsed_event_url(league_id, 0)
        raw_match_events_base = cls._get_raw_match_events(base_url)
        all_base_bets = {}
        if not raw_match_events_base:
            msg = '{} There are no league events for league {}'.format(_LOG_PREFIX, league_name)
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for raw_match_event in raw_match_events_base:
            for event in raw_match_event.get('events'):
                try:
                    event_name = event.get('name')
                    player_home, player_away = cls._get_players(event.get('team', []))
                    date_time = cls._get_match_date_time(event.get('startTime'))
                    match_odds = cls._get_match_base_odds(event.get('standardShortMarkets'))

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
                    print("Exception occured", event_name, str(e))
                    continue
        return all_base_bets

    @classmethod
    def _get_match_base_odds(cls, base_odd_informations):
        if not base_odd_informations:
            msg = 'No base oddd data.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)
        odds = {}
        for market in base_odd_informations:
            if market is None:
                continue

            if market.get('templateName', '') != '1x2':
                continue

            selection = market.get('selection')
            for odd in selection:
                if odd.get('name') == '[[Rival1]]':
                    odds[bet_place_enums.FootballMatchPlays.ONE.value] = float(odd.get('price'))
                if odd.get('name') == 'draw':
                    odds[bet_place_enums.FootballMatchPlays.X.value] = float(odd.get('price'))
                if odd.get('name') == '[[Rival2]]':
                    odds[bet_place_enums.FootballMatchPlays.TWO.value] = float(odd.get('price'))

        return odds

    @classmethod
    def _get_match_double_chance_odds(cls, double_chance_odd_informations):
        if not double_chance_odd_informations:
            msg = 'No base oddd data.'
            logger.exception('{} {}'.format(_LOG_PREFIX, msg))
            raise direct_exceptions.InvalidMatchDataError(msg)
        odds = {}
        for market in double_chance_odd_informations:
            if market is None:
                continue

            if market.get('templateName') != 'Double chance':
                continue

            selection = market.get('selection')
            for odd in selection:
                if odd.get('name') == '1X':
                    odds[bet_place_enums.FootballMatchPlays.ONEX.value] = float(odd.get('price'))
                if odd.get('name') == '12':
                    odds[bet_place_enums.FootballMatchPlays.ONETWO.value] = float(odd.get('price'))
                if odd.get('name') == 'X2':
                    odds[bet_place_enums.FootballMatchPlays.XTWO.value] = float(odd.get('price'))

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

        return datetime.datetime.strptime(date_time, direct_constants.MERIDIAN_DATE_FORMAT)

    @classmethod
    def _get_raw_match_events(cls, url):
        return simplejson.loads(
            cls._request(
                method=bet_place_enums.HttpRequestMethods.GET.value,
                url=url
            ).content
        ).get('events')

    @classmethod
    def _parse_league_matches_double_chance_bet(cls, league_name, league_id, base_odds):
        double_chance_url = cls._get_parsed_event_url(league_id, 1)
        raw_match_events_double = cls._get_raw_match_events(double_chance_url)

        if not raw_match_events_double:
            msg = '{} There are no league events for league {}'.format(_LOG_PREFIX, league_name)
            logger.exception(msg)
            raise direct_exceptions.ApiNoDataError(msg)

        for raw_match_event in raw_match_events_double:
            for event in raw_match_event.get('events'):
                try:
                    event_name = event.get('name')
                    match_odds = cls._get_match_double_chance_odds(event.get('standardShortMarkets'))

                    base_odds[event_name]['bet_odds'].update(match_odds)
                except Exception as e:
                    print("Exception occured", event_name, str(e))
                    continue

        return base_odds

    @classmethod
    def _combine_match_information_per_bet(cls):
        pass

    @classmethod
    def _get_parsed_event_url(cls, league_id, bet_odd):
        now = datetime.datetime.now()
        parsed_datetime = datetime.datetime.strftime(now, direct_constants.MERIDIAN_DATE_FORMAT)

        return cls.API_URL_EVENTS.format(
            league_id=league_id,
            date=parsed_datetime,
            bet_group=bet_odd,
        )
