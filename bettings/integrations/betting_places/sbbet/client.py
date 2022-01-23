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
from selenium.webdriver.common import action_chains


from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places import exceptions as betting_exceptions
from bettings.integrations.betting_places import base as base_integration
from bettings.integrations.betting_places.sbbet import constants

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[SBBET-CLIENT]"


class SbbetBaseClient(base_integration.IntegrationBaseClient):
    def __init__(self, sport, headless=True):
        # type: (betting_enums.Sports, bool) -> None
        super(SbbetBaseClient, self).__init__(headless)
        self.url = settings.CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.SBBET.name.upper()
        ][sport.name.upper()]

    def get_matches_odds_all(self):
        raise NotImplemented


class SbbetSoccerClient(SbbetBaseClient):
    def __init__(self):
        super(SbbetSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)
        time.sleep(7)
        self._setup_page()

    def _setup_page(self):
        self._change_page_time_frame(self.driver)
        try:
            self._switch_to_double_chance_odds(self.driver)
        except Exception as e:
            raise betting_exceptions.XpathGeneralException(str(e))

    @classmethod
    def _change_page_time_frame(cls, driver_element):
        time_filter_xpath = '//div[@class="sports-time-filter"]/span[3]'
        try:
            time_filter = cls._get_element(driver_element,
                time_filter_xpath,
            )
            action_chains.ActionChains(driver_element).move_to_element(time_filter).click().perform()
            time.sleep(3)
        except betting_exceptions.XpathElementNotFoundException:
            logger.info("{} Cannot switch to daily time frame. Continue with all mathces".format(_LOG_PREFIX))

    @classmethod
    def _switch_to_double_chance_odds(cls, driver_element):
        x_path_sport_content = '//div[@class="sport__content"]/div[@class="sport__table-wrapper"]//div[@class="offer"]'
        x_path_double_chance_dropdown = './div[1]/div[1]/div[2]//div[@class="offer__header__market"][2]'
        x_path_double_chance_switch = '/html/body/div//li[contains(text(), "Dupla")]'
        sport_content = cls._get_element(
            driver_element,
            x_path_sport_content,
        )

        # double chance drop down click
        cls._get_element(
            sport_content, x_path_double_chance_dropdown
        ).click()

        # double chance swithc
        cls._get_element(
            driver_element, x_path_double_chance_switch
        ).click()

    def get_matches_odds_all(self):
        match_date = None
        all_match_odds = []
        for match in self._get_all_matches(self.driver):
            match_details = self._get_element(match, "./div[1]")
            if "row" not in match_details.get_attribute("class"):
                match_date = match_details.get_attribute('innerHTML')
                logger.info("{} Match date found!".format(_LOG_PREFIX))
                continue

            try:
                match_time = self._get_match_time(match_details)
                bet_odds = self._get_match_odds(match_details)
                match_date_time = self._combine_match_date_time(match_date, match_time)
                player_home, player_away = self._get_players(match_details)

                match_details = {
                    "player_home": self._get_normalized_soccer_team_info(player_home),
                    "player_away": self._get_normalized_soccer_team_info(player_away),
                    "sport": betting_enums.Sports.FOOTBALL,
                    "league": '',
                    "tournament": '',
                    "date_time": match_date_time,
                    "bet_odds": bet_odds,
                }
                all_match_odds.append(match_details)
            except (betting_exceptions.XpathElementNotFoundException, betting_exceptions.XpathElementsNotFoundError):
                continue
            except betting_exceptions.XpathGeneralException:
                continue
            except Exception:
                # temporary. Has to be changed
                continue
        self.driver.close()
        return all_match_odds

    @classmethod
    def _get_match_odds(cls, driver_element):
        x_path_base_odds = './div[contains(@class,"column")][1]/div[contains(@class, "cell odd-cell")]/span'
        x_path_double_chance_odds = './div[contains(@class,"column")][2]/div[contains(@class, "cell odd-cell")]/span'

        base_odds = [odd.get_attribute('innerHTML') for odd in cls._get_elements(driver_element, x_path_base_odds)]
        double_chance_odds = [odd.get_attribute('innerHTML') for odd in cls._get_elements(driver_element, x_path_double_chance_odds)]

        if len(base_odds) == 3 and len(double_chance_odds) == 3:
            one, ex, two = base_odds
            oneex, extwo, onetwo = double_chance_odds
            return {
                bet_place_enums.FootballMatchPlays.ONE.value: float(one),
                bet_place_enums.FootballMatchPlays.X.value: float(ex),
                bet_place_enums.FootballMatchPlays.TWO.value: float(two),
                bet_place_enums.FootballMatchPlays.ONEX.value: float(oneex),
                bet_place_enums.FootballMatchPlays.XTWO.value: float(extwo),
                bet_place_enums.FootballMatchPlays.ONETWO.value: float(onetwo),
            }

        return {}


    @classmethod
    def _get_match_time(cls, driver_element):
        x_path = './div[@class="event"]/div[1]/div[1]/div[1]/div[1]'
        return cls._get_element(driver_element, x_path).get_attribute('innerHTML')

    @classmethod
    def _get_players(cls, driver_element):
        x_path_home_player = './div[@class="event"]/div[1]/div[3]/div[1]/div[1]'
        x_path_away_player = './div[@class="event"]/div[1]/div[3]/div[1]/div[2]'
        return cls._get_element(driver_element, x_path_home_player).get_attribute('innerHTML'), cls._get_element(driver_element, x_path_away_player).get_attribute('innerHTML')

    @classmethod
    def _get_all_matches(cls, driver_element):
        x_path_sport_content = '//div[@class="sport__content"]/div[@class="sport__table-wrapper"]//div[@class="offer"]'
        sport_content = cls._get_element(
            driver_element,
            x_path_sport_content,
        )
        return cls._get_elements(sport_content, './div[1]/div[1]/div[1]//div[@data-index]')

    @staticmethod
    def _combine_match_date_time(date, time):
        hour, minute = time.split(':')
        day_name, day, month = date.split(" ")
        day = day.replace('.', '')
        month = constants.MONTH_MAPPING.get(month, 1)
        return datetime.datetime(datetime.date.today().year, month, int(day), int(hour), int(minute))