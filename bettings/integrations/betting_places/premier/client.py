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
_LOG_PREFIX = "[PREMIER-CLIENT]"


class PremierBaseClient(base_integration.IntegrationBaseClient):
    def __init__(self, sport, headless=False):
        # type: (betting_enums.Sports, bool) -> None
        super(PremierBaseClient, self).__init__(headless)
        self.url = settings.CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.PREMIER.name.upper()
        ][sport.name.upper()]

    def get_matches_odds_all(self):
        raise NotImplemented


class PremierSoccerClient(PremierBaseClient):
    def __init__(self):
        super(PremierSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)
        time.sleep(10)
        self._setup_page()

    def _setup_page(self):
        self._change_page_time_frame(self.driver)

    @classmethod
    def _change_page_time_frame(cls, driver_element):
        time_filter_xpath = '//div[contains(@class, "sport-menu")]//div[contains(@class, "filters")]/div'
        try:
            time_filters = cls._get_elements(driver_element,
                time_filter_xpath,
            )
            action_chains.ActionChains(driver_element).move_to_element(time_filters[2]).click().perform()
            time.sleep(3)
        except betting_exceptions.XpathElementNotFoundException:
            logger.info("{} Cannot switch to daily time frame. Continue with all mathces".format(_LOG_PREFIX))

    def get_matches_odds_all(self):
        all_matches = self._get_all_matches(self.driver)
        current_scroll_position = ''
        new_scroll_position_elmnt = all_matches[-1]
        new_scroll_position = new_scroll_position_elmnt.get_attribute("class")
        all_match_odds = []
        while current_scroll_position != new_scroll_position:
            for match in all_matches:
                match_details = self._get_match_details(match)

                if "first-row" not in match_details.get_attribute("class"):
                    logger.info("{} Match is not loaded yet. Continue!")
                    continue
                try:
                    match_time = self._get_match_time(match_details)
                    league_name = self._get_league_name(match_details)
                    player_home, player_away = self._get_players(match_details)
                    bet_odds = self._get_match_odds(match_details)
                    match_details = {
                        "player_home": self._get_normalized_soccer_team_info(player_home),
                        "player_away": self._get_normalized_soccer_team_info(player_away),
                        "sport": betting_enums.Sports.FOOTBALL,
                        "league": league_name,
                        "tournament": '',
                        "date_time": self._combine_date_time(match_time),
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
            self.driver.execute_script("arguments[0].scrollIntoView();", new_scroll_position_elmnt)
            current_scroll_position = new_scroll_position
            all_matches = self._get_all_matches(self.driver)
            new_scroll_position_elmnt = all_matches[-1]
            new_scroll_position = new_scroll_position_elmnt.get_attribute("class")
            
        self.driver.close()
        return all_match_odds

    @staticmethod
    def _combine_date_time(time):
        hour, minute = time.split(':')
        return datetime.datetime.combine(datetime.date.today(), datetime.time(int(hour), int(minute)))

    @classmethod
    def _get_all_matches(cls, driver_element):
        x_path = '//section[@class="events-container"]//div[@class="main-nolive-events"]//div[@class="events-list"]/div[contains(@class, "event-id")][div]'
        return cls._get_elements(driver_element, x_path)

    @classmethod
    def _get_match_details(cls, driver_element):
        x_path = './div[1]'
        return cls._get_element(driver_element, x_path)

    @classmethod
    def _get_match_time(cls, driver_element):
        x_path = './div[@class="event-participants-wrapper"]/div[1]/div[2]'
        return cls._get_element(driver_element, x_path).get_attribute('innerHTML')

    @classmethod
    def _get_league_name(cls, driver_element):
        x_path = './div[@class="event-participants-wrapper"]/div[2]/div[1]'
        return cls._get_element(driver_element, x_path).get_attribute('title')

    @classmethod
    def _get_players(cls, driver_element):
        x_path_home = './div[@class="event-participants-wrapper"]/div[3]/div[@class="participant host"]'
        x_path_away = './div[@class="event-participants-wrapper"]/div[3]/div[@class="participant guest"]'
        return cls._get_element(driver_element, x_path_home).get_attribute('innerHTML'), cls._get_element(driver_element, x_path_away).get_attribute('innerHTML')

    @classmethod
    def _get_match_odds(cls, driver_element):
        x_path_base_odds = './div[@class="event-tips-container no-select"]/div[@class="event-tips"]/div[1]/div'
        x_path_double_chance_odds = './div[@class="event-tips-container no-select"]/div[@class="event-tips"]/div[5]/div'

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
