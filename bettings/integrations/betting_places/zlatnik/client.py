import datetime
import logging
import re
import time
import typing

from django.conf import settings
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common import exceptions as selenium_exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places import exceptions as betting_exceptions

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[ZLATNIK_CLIENT]"


class ZlatnikBaseClient(object):
    def __init__(self, sport):
        # type: (betting_enums.Sports) -> None
        self.url = settings.CLIENT_SPORT_URLS[
            betting_enums.BettingInstitutions.ZLATNIK.name.upper()
        ][sport.name.upper()]
        self.driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))


class ZlatnikSoccerClient(ZlatnikBaseClient):
    def __init__(self):
        super(ZlatnikSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)
        time.sleep(5)

    def _get_football_leagues(self):
        # type: () -> typing.Optional[typing.List]
        x_path = '//app-sportbetting//app-prematch-offer/div[1]/div/div'
        football_leagues = self._get_elements(self.driver, x_path)
        logger.info(
            "{} Found {} football leagues.".format(_LOG_PREFIX, len(football_leagues))
        )
        return football_leagues

    def get_matches_odds_all(self):
        for league in self._get_football_leagues():
            for tournament in self._get_football_tournaments(league):
                try:
                    league_name, tournament_name = self._get_league_tournament_name(tournament)
                    for match in self._get_tournament_matches(tournament):
                        try:
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
                        except betting_exceptions.XpathBaseException:
                            continue
                except betting_exceptions.XpathBaseException:
                    continue
        self.driver.close()

    @classmethod
    def _get_football_tournaments(cls, driver_element):
        x_path = './div'
        football_tournaments = cls._get_elements(driver_element, x_path)
        logger.info(
            "{} Found {} football tournaments.".format(_LOG_PREFIX, len(football_tournaments))
        )
        return football_tournaments

    @classmethod
    def _get_tournament_matches(cls, driver_element):
        x_path = './div'
        tournament_matches = cls._get_elements(driver_element, x_path)
        logger.info(
            "{} Found {} football tournaments.".format(_LOG_PREFIX, len(tournament_matches))
        )
        return tournament_matches

    @classmethod
    def _get_league_tournament_name(cls, driver_element):
        x_path = './/div/div/span[@title]'
        name = cls._get_element(driver_element, x_path).get_attribute("title").split("/")
        return name[0], name[1]

    @classmethod
    def _get_match_players(cls, driver_element):
        x_path = "./app-match/div[1]/div[@title]"
        # parse this to get both match players
        players = cls._get_element(driver_element, x_path).get_attribute("title")
        if players:
            home_player, away_player = players.split(" - ")
            return home_player, away_player
        return players

    @classmethod
    def _get_match_date_time(cls, driver_element):
        x_path_time = './app-match/div[1]/div[1]/div[contains(@class, "match-time")]/div[2]'
        x_path_date = './app-match/div[1]/div[1]/div[contains(@class, "match-time")]/div[1]'
        # Get date and combine
        match_time_raw = cls._get_element(driver_element, x_path_time).text
        match_date_raw = cls._get_element(driver_element, x_path_date).text

        if match_time_raw and match_date_raw:
            parsed_date_time = match_date_raw.split('.')[:3]
            day, month, year = parsed_date_time

            hour, minutes = match_time_raw.split(":")
            match_date_time = datetime.datetime(
                int(year), int(month), int(day), int(hour), int(minutes)
            )
            return match_date_time
        return None

    @classmethod
    def _get_match_odds(cls, driver_element):
        odds_xpath = './app-match/div[1]/div[2]/div/div'
        match_odds = [cls._get_element(odd, './/div[contains(@class, "odd-value")]/span').text for odd in cls._get_elements(driver_element, odds_xpath)]

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
    def _get_element(driver, x_path):
        try:
            return driver.find_element(By.XPATH, x_path)
        except selenium_exceptions.NoSuchElementException as e:
            raise betting_exceptions.XpathElementNotFoundException(str(e))
        except Exception as e:
            raise betting_exceptions.XpathGeneralException(str(e))

    @staticmethod
    def _get_elements(driver, x_path):
        try:
            elements = driver.find_elements(By.XPATH, x_path)
            if not elements:
                raise betting_exceptions.XpathElementsNotFoundError()
            return elements
        except Exception as e:
            raise betting_exceptions.XpathGeneralException(str(e))


    # TODO: Write init driver method