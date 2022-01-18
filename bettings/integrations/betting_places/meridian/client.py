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
from selenium.webdriver.support import select
from selenium.webdriver.common import action_chains

from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places import constants as bet_place_constants
from bettings.integrations.betting_places import exceptions as betting_exceptions

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[MERIDIAN_CLIENT]"


class MeridianBaseClient(object):
    def __init__(self, sport, headless=True):
        # type: (betting_enums.Sports, typing.Dict) -> None
        self.url = settings.CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.MERIDIAN.name.upper()
        ][sport.name.upper()]
        self.driver = self._get_driver(headless)

    def _get_driver(self, headless):
        fireFoxOptions = options.Options()
        fireFoxOptions.headless = headless
        return webdriver.Firefox(options=fireFoxOptions, service=Service(GeckoDriverManager().install()))


class MeridianSoccerClient(MeridianBaseClient):

    def __init__(self):
        super(MeridianSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)

    def get_matches_odds_all(self):
        all_elements_wrapper = self._get_elements(self.driver,  '//div[@id="events"]/*')

        position = 0
        all_match_odds = []
        for index, event in enumerate(all_elements_wrapper[position:]):
            event_type = event.get_attribute('id')
            if "matches" in event_type:
                match_position = 0

                for match_counter, match in enumerate(all_elements_wrapper[index+1:]):
                    if "event" not in match.get_attribute("class"):
                        break
                    try:
                        match_date_time = self._get_match_date_time(match)
                        league_name, tournament_name= self._get_league_tournament(match)
                        player_home, player_away = self._get_players(match)
                        bet_odds = self._get_match_odds(match)

                        match_odds = {
                            "player_home": self._get_normalized_soccer_team_info(player_home),
                            "player_away": self._get_normalized_soccer_team_info(player_away),
                            "sport": betting_enums.Sports.FOOTBALL,
                            "league": league_name,
                            "tournament": tournament_name,
                            "date_time": match_date_time,
                            "bet_odds": bet_odds,
                        }
                        all_match_odds.append(match_odds)
                    except betting_exceptions.XpathElementsNotFoundError:
                        continue

                    match_position = match_counter
                print("Fetched matches", position, len(all_match_odds))
                position += match_position
        return all_match_odds

    def _get_match_odds(self, driver_element):
        base_odds = [odd.get_attribute("innerHTML") for odd in self._get_elements(
                driver_element,
                './standard-item-games/div[1]//div[contains(@class, "odds")]',
            )
        ]
        if not base_odds:
            raise betting_exceptions.BetIntegrationGeneralException()

        one, ex, two = base_odds

        game_names = self._get_elements(self.driver, '//div[@class="games g3"]/div[contains(@class, "game")]')
        game_option_names = self._get_element(
            game_names[0], './div[contains(@class,"game-name")]'
        )
        action_chains.ActionChains(self.driver).move_to_element(game_option_names).perform()

        options = game_names[0].find_elements(
            By.XPATH, './div[contains(@class, "dropdown")]/div[1]/div'
        )

        base_games = options[0]
        double_chance = options[1]

        # Switch to double chance so able to grab other odds
        self.driver.execute_script("arguments[0].click();", double_chance)
        time.sleep(1)
        double_chance_odds = [
            odd.get_attribute("innerHTML")
            for odd in self._get_elements(
                driver_element,
                './standard-item-games/div[1]//div[contains(@class, "odds")]',
            )
        ]
        if not double_chance_odds:
            raise betting_exceptions.BetIntegrationGeneralException()

        oneex, extwo, onetwo = double_chance_odds

        action_chains.ActionChains(self.driver).move_to_element(
            game_option_names
        ).perform()

        base_games.click()

        return {
            bet_place_enums.FootballMatchPlays.ONE.value: one,
            bet_place_enums.FootballMatchPlays.X.value: ex,
            bet_place_enums.FootballMatchPlays.TWO.value: two,
            bet_place_enums.FootballMatchPlays.ONEX.value: oneex,
            bet_place_enums.FootballMatchPlays.XTWO.value: extwo,
            bet_place_enums.FootballMatchPlays.ONETWO.value: onetwo,
        }

    @classmethod
    def _get_players(cls, driver_element):
        x_path_player_home = './div[contains(@class, "details")]/div[contains(@class, "rivals")]/div[contains(@class, "home")]'
        x_path_player_away = './div[contains(@class, "details")]/div[contains(@class, "rivals")]/div[contains(@class, "away")]'

        player_home = cls._get_element(driver_element, x_path_player_home).get_attribute("innerHTML")
        player_away = cls._get_element(driver_element, x_path_player_away).get_attribute("innerHTML")

        return player_home, player_away
    @classmethod
    def _get_league_tournament(cls, driver_element):
        x_path = './div[contains(@class, "details")]/div[contains(@class, "rivals")]/div[contains(@class, "league")]'
        league_tournamet = cls._get_element(driver_element, x_path).get_attribute("innerHTML").split('-')

        return league_tournamet[0], league_tournamet[1]
    @classmethod
    def _get_match_date_time(cls, driver_element):
        x_path_time = './div[contains(@class, "details")]//div[contains(@class, "time")]'
        x_path_date = './div[contains(@class, "details")]//div[contains(@class, "date")]'

        time = cls._get_element(driver_element, x_path_time).get_attribute("innerHTML")
        date = cls._get_element(driver_element, x_path_date).get_attribute("innerHTML")

        hour, minutes = time.split(":")
        day, month, _ = date.split(".")

        return datetime.datetime(datetime.date.today().year, int(month), int(day), int(hour), int(minutes))
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

    @staticmethod
    def _switch_frame(driver, frame):
        try:
            driver.switch_to.frame(frame)
        except selenium_exceptions.NoSuchFrameException as e:
            raise betting_exceptions.XpathFrameNotFoundException(str(e))
        except Exception as e:
            raise betting_exceptions.XpathGeneralException(str(e))

    @classmethod
    def _select_element_by_visible_text(cls, driver, x_path, text):
        try:
            select_element = select.Select(cls._get_element(driver, x_path))
            select_element.select_by_visible_text(text=text)
        except selenium_exceptions.NoSuchElementException as e:
            raise betting_exceptions.XpathElementNotFoundException(e)
        except Exception as e:
            raise betting_exceptions.XpathGeneralException(e)

    @staticmethod
    def _get_normalized_soccer_team_info(team_name):
        text = re.sub(r"[^a-zA-Z0-9\sčČšŠžŽ]", "", team_name)
        # remove multiple white spaces
        text = re.sub(' +', ' ', text)
        # convert all letters to lower case
        text = text.lower().strip()
        text = sorted(text.split(' '), key=len)
        if len(text) >= 2:
            first, second = text[-2:]
            if len(first) == len(second):
                return first + " " + second
            else:
                return second

        return text[0]

