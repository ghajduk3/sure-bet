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



from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.integrations.betting_places import exceptions as betting_exceptions

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[ZLATNIK_CLIENT]"


class IntegrationBaseClient(object):

    def __init__(self, headless=True):
        self.driver = self._get_driver(headless)

    def _get_driver(self, headless):
        driver_options = options.Options()
        driver_options.headless = headless
        return webdriver.Firefox(options=driver_options, service=Service(GeckoDriverManager().install()))

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
