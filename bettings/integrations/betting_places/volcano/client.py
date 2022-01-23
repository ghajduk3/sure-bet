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
from selenium.webdriver.firefox import options



from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places import exceptions as betting_exceptions
from bettings.integrations.betting_places import base as base_integration
from bettings.integrations.betting_places.volcano import constants

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[VOLCANO-CLIENT]"


class VolcanoBaseClient(base_integration.IntegrationBaseClient):
    def __init__(self, sport, headless=True):
        # type: (betting_enums.Sports, bool) -> None
        super(VolcanoBaseClient, self).__init__(headless)
        self.url = settings.CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.VOLCANO.name.upper()
        ][sport.name.upper()]


class VolcanoSoccerClient(VolcanoBaseClient):
    def __init__(self):
        super(VolcanoSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)
        time.sleep(5)

    def get_matches_odds_all(self):
        all_match_odds = []
        for league in self._get_all_leagues(self.driver):
            for tournament in self._get_all_tournaments(league):
                league_name = self._get_league_name(tournament)
                try:
                    matches = self._get_all_matches(tournament)
                except betting_exceptions.XpathElementsNotFoundError:
                    continue
                except betting_exceptions.XpathGeneralException:
                    continue
                time.sleep(1)
                league_date = self._get_match_date(tournament)

                for match in matches:
                    try:
                        player_home, player_away = self._get_players(match)
                        match_date_time = self._combine_match_date_time(league_date, self._get_match_time(match))
                        bet_odds = self._get_match_odds(match)

                        match_details = {
                            "player_home": self._get_normalized_soccer_team_info(player_home),
                            "player_away": self._get_normalized_soccer_team_info(player_away),
                            "sport": betting_enums.Sports.FOOTBALL,
                            "league": league_name,
                            "tournament": '',
                            "date_time": match_date_time,
                            "bet_odds": bet_odds,
                        }
                        all_match_odds.append(match_details)
                    except (betting_exceptions.XpathElementNotFoundException, betting_exceptions.XpathElementNotFoundException):
                        continue
                    except betting_exceptions.XpathGeneralException:
                        continue
        self.driver.close()
        return all_match_odds

    @classmethod
    def _get_all_leagues(cls, driver_element):
        x_path = '//xbet-sport-overview-web//div[@class="ps-content"]/div'
        return cls._get_elements(driver_element, x_path)

    @classmethod
    def _get_all_tournaments(cls, driver_element):
        x_path = './div[1]/div'
        return cls._get_elements(driver_element, x_path)

    @classmethod
    def _get_league_name(cls, driver_element):
        x_path = './div[contains(@class, "league-header")]/div[contains(@class, "league-name-wrapper")]/div[1]'
        return cls._get_element(driver_element, x_path).get_attribute("innerHTML")

    @classmethod
    def _get_match_date(cls, driver_element):
        x_path = './div[contains(@class, "multi-market-wrapper")]/*[1]//div[@class="date"]'
        return cls._get_element(driver_element, x_path).get_attribute("innerHTML")

    @classmethod
    def _get_match_time(cls, driver_element):
        x_path = './/div[contains(@class, "list-game-item")]//span[contains(@class, "game-time")]'
        return cls._get_element(driver_element, x_path).get_attribute('innerHTML')

    @staticmethod
    def _combine_match_date_time(date, time):
        hour, minute = time.split(':')
        day_name, day, month = date.split(" ")
        month = constants.MONTH_MAPPING.get(month, 1)
        return datetime.datetime(datetime.date.today().year, month, int(day), int(hour), int(minute))
    @classmethod
    def _get_all_matches(cls, driver_element):
        x_path = './div[contains(@class, "multi-market-wrapper")]/div'
        return cls._get_elements(driver_element, x_path)

    @classmethod
    def _get_players(cls, driver_element):
        x_path = './/div[contains(@class, "list-game-item")]/ul[contains(@class, "event-wrapper")]//div[contains(@class, "event-info")]/span'
        player_home, player_away = cls._get_elements(driver_element, x_path)
        return player_home.get_attribute('innerHTML'), player_away.get_attribute('innerHTML')

    @classmethod
    def _get_match_odds(cls, driver_element):
        x_path_all_odds = './/div[contains(@class, "list-game-item")]//div[@class="bet-picks-wrapper"]'
        x_path_odds = './/div[contains(@class, "market-container")]//span[contains(@class, "odds")]'

        odds_wrapper = cls._get_elements(driver_element, x_path_all_odds)

        if not odds_wrapper:
            logger.info("{} There are no odds!")
            return {}

        base_odds = cls._get_elements(odds_wrapper[0], x_path_odds)
        double_chance_odds = cls._get_elements(odds_wrapper[1], x_path_odds)

        if len(base_odds) == 3 and len(double_chance_odds) == 3:
            one, ex, two = [cls._parse_odd(odd.get_attribute('innerHTML')) for odd in base_odds]
            oneex, extwo, onetwo = [cls._parse_odd(odd.get_attribute('innerHTML')) for odd in double_chance_odds]

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
    def _parse_odd(odd):
        return float(odd.strip().replace(',', '.'))