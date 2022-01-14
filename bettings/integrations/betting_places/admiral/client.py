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
from selenium.webdriver.support import select

from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places import exceptions as betting_exceptions

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[ADMIRAL_CLIENT]"


class AdmiralBaseClient(object):
    def __init__(self, sport):
        # type: (betting_enums.Sports) -> None
        self.url = settings.CLIENT_SPORT_URLS[
            betting_enums.BettingInstitutions.ADMIRAL.name.upper()
        ][sport.name.upper()]
        self.driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()))


class AdmiralSoccerClient(AdmiralBaseClient):
    def __init__(self):
        super(AdmiralSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self._prepare_page()

    def _prepare_page(self):
        self.driver.get(self.url)
        time.sleep(5)
        # close cookies popup, raise exception if not available
        try:
            self._get_element(self.driver, '//span[contains(text(), "Razumem")]').click()
        except betting_exceptions.XpathElementNotFoundException as e:
            logger.exception("{} Unable to close consent cookie popup.".format(_LOG_PREFIX))

        try:
            self._switch_frame(self.driver, "sportIframe")
        #     Switch to dupla sansa
            self._select_element_by_visible_text(self.driver, '//*[@id="betTypeName"]', 'Dupla sansa')
        except betting_exceptions.XpathElementNotFoundException as e:
            logger.exception("{} Unable to switch to selected game plays: {}".format(_LOG_PREFIX, str(e)))
            return
        except betting_exceptions.XpathFrameNotFoundException:
            logger.exception("{} Unable to switch to sport frame. Exiting".format(_LOG_PREFIX))
            return
        time.sleep(1)

    def get_matches_odds_all(self):
        all_matches_data = {}
        while True:
            matches_by_day = self._get_matches_by_day()
            if not matches_by_day:
                break
            json_matches = []
            for matches_date, matches in matches_by_day.items():
                for match in matches:
                    try:
                        player_home, player_away = self._get_match_players(match)
                        bet_odds = self._get_match_odds(match)
                    except betting_exceptions.XpathElementNotFoundException:
                        continue
                    json_matches.append(
                        {
                            "player_home": player_home,
                            "player_away": player_away,
                            "sport": betting_enums.Sports.FOOTBALL,
                            "bet_odds": bet_odds,
                        }
                    )

            self._get_next_page()

    @classmethod
    def _get_match_players(cls, driver):
        x_path_home = "./article/div[1]/div[1]/div[contains(@class, 'event-name')]/span[contains(@class, 'home')]"
        x_path_away = "./article/div[1]/div[1]/div[contains(@class, 'event-name')]/span[contains(@class, 'away')]"
        return cls._get_element(driver, x_path_home).text, cls._get_element(driver, x_path_away).text




    def _get_matches_by_day(self):
        league_matches_all_days = self._get_element(self.driver, '//app-events-group//div[contains(@class, "selected-league")]')
        day_info_wraps = self._get_elements(league_matches_all_days, './div[contains(@class, "bet-info-wrap")]')

        logger.info("{} Found {} days that matches are played. ".format(_LOG_PREFIX, len(day_info_wraps)))

        matches_by_day = {}
        last_day = day_info_wraps[-1]
        if len(day_info_wraps) > 1:
            all_days = set()
            for index, day in enumerate(day_info_wraps[1:]):
                try:
                    previous_day = set(self._get_elements(day, "./preceding-sibling::app-event")) - all_days
                    match_date = self._get_match_date(day_info_wraps[index])
                    matches_by_day[match_date] = previous_day
                    all_days = all_days.union(previous_day)
                except betting_exceptions.XpathElementsNotFoundError:
                    logger.exception("{} Error occured while obtaining day matches. Continuing.".format(_LOG_PREFIX))
                    continue
            try:
                last_day_matches = set(self._get_elements(last_day, "./following-sibling::app-event"))
                last_date_match = self._get_match_date(last_day)
                matches_by_day[last_date_match] = last_day_matches
            except betting_exceptions.XpathElementsNotFoundError:
                logger.exception("{} Error occured while obtaining day matches. Terminating.".format(_LOG_PREFIX))
                return
        else:
            try:
                day_matches = self._get_elements(last_day, "./following-sibling::app-event")
                match_date = self._get_match_date(last_day)
                matches_by_day[match_date] = day_matches
            except betting_exceptions.XpathElementsNotFoundError:
                logger.exception("{} There is no day matches. Terminating.".format(_LOG_PREFIX))
                return

        return matches_by_day

    @classmethod
    def _get_match_date(cls, driver):
        x_path = "./div[1]/span"
        match_date = cls._get_element(driver, x_path).text.split(',')[1]
        return match_date

    def _get_next_page(self):
        x_path = '//li[contains(text(), "Sledeća")]'
        self._get_element(self.driver, x_path).click()

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

    @classmethod
    def _get_match_odds(cls, driver):
        one = cls._get_element(
            driver,  "./article/div[1]/div[2]/div[contains(@class, 'bet-type-col')]/span[1]/div[1]").text
        ex = cls._get_element(
            driver, "./article/div[1]/div[2]/div[contains(@class, 'bet-type-col')]/span[2]/div[1]").text
        two = cls._get_element(
            driver, "./article/div[1]/div[2]/div[contains(@class, 'bet-type-col')]/span[3]/div[1]").text
        oneex = cls._get_element(
            driver,"./article/div[1]/div[2]/div[2]/span[1]/div[1]").text
        onetwo = cls._get_element(
            driver,"./article/div[1]/div[2]/div[2]/span[2]/div[1]").text
        extwo = cls._get_element(
            driver, "./article/div[1]/div[2]/div[2]/span[3]/div[1]").text

        return {
            bet_place_enums.FootballMatchPlays.ONE.value: float(one),
            bet_place_enums.FootballMatchPlays.X.value: float(ex),
            bet_place_enums.FootballMatchPlays.TWO.value: float(two),
            bet_place_enums.FootballMatchPlays.ONEX.value: float(oneex),
            bet_place_enums.FootballMatchPlays.XTWO.value: float(extwo),
            bet_place_enums.FootballMatchPlays.ONETWO.value: float(onetwo),
       }

