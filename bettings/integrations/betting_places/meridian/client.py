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
from bettings.integrations.betting_places import base as base_integration


logger = logging.getLogger(__name__)
_LOG_PREFIX = "[MERIDIAN_CLIENT]"


class MeridianBaseClient(base_integration.IntegrationBaseClient):
    def __init__(self, sport, headless=False):
        # type: (betting_enums.Sports, bool) -> None
        super(MeridianBaseClient, self).__init__(headless)
        self.url = settings.CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.MERIDIAN.name.upper()
        ][sport.name.upper()]


class MeridianSoccerClient(MeridianBaseClient):

    def __init__(self):
        super(MeridianSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)
        time.sleep(5)

    def get_matches_odds_all(self):
        time.sleep(1)
        self.driver.execute_script("arguments[0].click();", self._get_element(self.driver, '//*[@id="sidebar"]/div/active-sidebar-sport-component/div/div[1]/a'))
        time.sleep(1)


        position = 0
        all_match_odds = []

        all_elements_wrapper = self._get_elements(self.driver, '//div[@id="events"]/*', )
        new_position_element = all_elements_wrapper[-1]
        current_scroll_position_element = None

        while new_position_element != current_scroll_position_element:
            for index, event in enumerate(all_elements_wrapper[position:]):
                time.sleep(1)
                event_type = event.get_attribute('id')
                print("Events ({}), ({}), ({}), ({})".format(index, event_type, event.get_attribute('class'), len(all_elements_wrapper)))
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
                            print("League_name", league_name)

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
                        except Exception:
                            continue
                        match_position = match_counter
                    time.sleep(1)
                    print("Fetched matches", position, len(all_match_odds))
                    position += match_position

            current_scroll_position_element = new_position_element
            self._scroll_page_down(self.driver, current_scroll_position_element)

            all_elements_wrapper = self._get_elements(self.driver, '//div[@id="events"]/*', )
            new_position_element = all_elements_wrapper[-1]

        self.driver.close()
        return all_match_odds

    def _get_match_odds(self, driver_element):
        game_names = self._get_elements(self.driver, '//div[@class="games g3"]/div[contains(@class, "game")]')
        game_option_names = self._get_element(
            game_names[0], './div[contains(@class,"game-name")]'
        )

        action_chains.ActionChains(self.driver).move_to_element(game_option_names).perform()
        time.sleep(0.5)

        options = game_names[0].find_elements(
            By.XPATH, './div[contains(@class, "dropdown")]/div[1]/div'
        )

        base_games = options[0]
        double_chance = options[1]
        # self.driver.execute_script("arguments[0].click();", base_games)
        action_chains.ActionChains(self.driver).move_to_element(base_games).click().perform()
        time.sleep(0.5)
        # base_games.click()

        base_odds = [self._parse_odd(odd.get_attribute("innerHTML")) for odd in self._get_elements(
                driver_element,
                './standard-item-games/div[1]//div[contains(@class, "odds")]',
            )
        ]
        if not base_odds:
            raise betting_exceptions.BetIntegrationGeneralException()

        one, ex, two = base_odds




        # Switch to double chance so able to grab other odds
        # self.driver.execute_script("arguments[0].click();", double_chance)
        action_chains.ActionChains(self.driver).move_to_element(double_chance).click().perform()
        time.sleep(1)
        double_chance_odds = [
            self._parse_odd(odd.get_attribute("innerHTML"))
            for odd in self._get_elements(
                driver_element,
                './standard-item-games/div[1]//div[contains(@class, "odds")]',
            )
        ]

        if not double_chance_odds:
            raise betting_exceptions.BetIntegrationGeneralException()

        oneex, extwo, onetwo = double_chance_odds


        return {
            bet_place_enums.FootballMatchPlays.ONE.value: float(one),
            bet_place_enums.FootballMatchPlays.X.value: float(ex),
            bet_place_enums.FootballMatchPlays.TWO.value: float(two),
            bet_place_enums.FootballMatchPlays.ONEX.value: float(oneex),
            bet_place_enums.FootballMatchPlays.XTWO.value: float(extwo),
            bet_place_enums.FootballMatchPlays.ONETWO.value: float(onetwo),
        }

    @classmethod
    def _scroll_page_down(cls, driver_element, element):
        driver_element.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(3)

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
    def _parse_odd(odd):
        return odd.strip().replace('\n', '')