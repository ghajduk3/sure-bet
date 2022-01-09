import datetime
import logging
import re
import typing

from django.conf import settings
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[OLIMP_CLIENT]"


class OlimpBaseClient(object):
    def __init__(self, sport):
        # type: (betting_enums.Sports) -> None
        self.url = settings.CLIENT_SPORT_URLS[
            betting_enums.BettingInstitutions.OLIMPWIN.name.upper()
        ][sport.name.upper()]
        self.driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))


class OlimpSoccerClient(OlimpBaseClient):
    def __init__(self):
        super(OlimpSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)

    def get_football_leagues(self):
        # type: () -> typing.Optional[typing.List]
        x_path = '//*[@id="ContentBody_ctl01_ucOffer_ucOdds_fullPonuda"]/div[@class="liga 2"]'
        football_leagues = self.driver.find_elements(By.XPATH, x_path)
        logger.info(
            "{} Found {} football leagues.".format(_LOG_PREFIX, len(football_leagues))
        )
        return football_leagues

    def get_matches_odds_all(self):
        for league in self.get_football_leagues():
            league_name = self._get_league_name(league)
            tournament_name = self._get_tournament_name(league)

            for match in self.get_league_matches(league):
                player_home, player_away = self._get_match_players(match)
                date_time = self._get_match_date_time(match)
                bet_odds = self._get_match_odds(match)

                yield {
                    "player_home": player_home,
                    "player_away": player_away,
                    "sport": betting_enums.Sports.FOOTBALL,
                    "league": league_name,
                    "tournament": tournament_name,
                    "date_time": date_time,
                    "bet_odds": bet_odds,
                }

        self.driver.close()

    @classmethod
    def _get_match_odds(cls, driver_element):
        # type: () -> typing.Optional[typing.Dict]
        # for now only base odds 1,x,2,1x,x2
        x_path = './td[@class="tgp"]'
        # parse and return dict
        match_odds = [
            cls._parse_match_odd(odd.text)
            for odd in driver_element.find_elements(By.XPATH, x_path)
        ]

        if match_odds:
            one, ex, two, oneex, extwo, onetwo = match_odds
            return {
                bet_place_enums.FootballMatchPlays.ONE.value: one,
                bet_place_enums.FootballMatchPlays.X.value: ex,
                bet_place_enums.FootballMatchPlays.TWO.value: two,
                bet_place_enums.FootballMatchPlays.ONEX.value: oneex,
                bet_place_enums.FootballMatchPlays.XTWO.value: extwo,
                bet_place_enums.FootballMatchPlays.ONETWO.value: onetwo,
            }

        return {}

    @staticmethod
    def get_league_matches(driver_element):
        # type: () -> typing.Optional[typing.List]
        x_path = './/table[@class="parovi"]/tbody/tr[@ot]'
        league_matches = driver_element.find_elements(By.XPATH, x_path)
        logger.info(
            "{} Found {} league matches.".format(_LOG_PREFIX, len(league_matches))
        )
        return league_matches

    @staticmethod
    def _get_league_name(driver_element):
        x_path = './/div[1]/table/tbody/tr/td[@class="grupa"]/span[2]'
        return driver_element.find_element(By.XPATH, x_path)

    @staticmethod
    def _get_tournament_name(driver_element):
        x_path = './/div[1]/table/tbody/tr/td[@class="grupa"]/span[3]'
        return driver_element.find_element(By.XPATH, x_path)

    @staticmethod
    def _get_match_players(driver_element):
        x_path = "./td[@title]"
        # parse this to get both match players
        players = driver_element.find_element(By.XPATH, x_path).text
        if players:
            home_player, away_player = players.split(" - ")
            return home_player, away_player

        return players

    @staticmethod
    def _get_match_date_time(driver_element):
        x_path_time = './td[@class="datumPar"]'
        x_path_date = '//td[@class="cal current"]'
        # Get date and combine
        match_time_raw = driver_element.find_element(By.XPATH, x_path_time).text
        match_date_raw = driver_element.find_element(
            By.XPATH, x_path_date
        ).get_attribute("onclick")
        if match_time_raw and match_date_raw:
            parsed_date_time = re.findall("\d{1,2}.\d{1,2}.\d{1,4}", match_date_raw)[
                0
            ].split(".")
            day, month, year = parsed_date_time

            hour, minutes = match_time_raw.split(":")
            match_date_time = datetime.datetime(
                int(year), int(month), int(day), int(hour), int(minutes)
            )
            return match_date_time
        return None

    # TODO: move to util
    @staticmethod
    def _parse_match_odd(odd):
        return float(odd.replace(",", "."))
