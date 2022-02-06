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
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.scrapers import exceptions as betting_exceptions
from bettings.integrations.scrapers.betting_places import base as base_integration

logger = logging.getLogger(__name__)
_LOG_PREFIX = "[ZLATNIK-CLIENT]"


class ZlatnikBaseClient(base_integration.IntegrationBaseClient):
    def __init__(self, sport, headless=False):
        # type: (betting_enums.Sports, bool) -> None
        super(ZlatnikBaseClient, self).__init__(headless)
        self.url = settings.SCRAPER_CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.ZLATNIK.name.upper()
        ][sport.name.upper()]


class ZlatnikSoccerClient(ZlatnikBaseClient):
    def __init__(self):
        super(ZlatnikSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)

    def _get_football_leagues(self):
        # type: () -> typing.Optional[typing.List]
        x_path = '//app-sportbetting//app-prematch-offer/div[1]/div/div'
        football_leagues = self._get_elements(self.driver, x_path)
        logger.info(
            "{} Found {} football leagues.".format(_LOG_PREFIX, len(football_leagues))
        )
        return football_leagues

    def get_matches_odds_all(self, days=3):
        self._switch_to_days(days)
        return self.get_matches_odds()

    def get_matches_odds(self):
        all_match_odds = []
        all_leagues = self._get_football_leagues()
        new_position_element = all_leagues[-1]
        current_scroll_position_element = None

        while new_position_element != current_scroll_position_element:
            print("Start fetching")

            for league in all_leagues:
                for tournament in self._get_football_tournaments(league):
                    try:
                        league_name, tournament_name = self._get_league_tournament_name(tournament)
                        for match in self._get_tournament_matches(tournament):
                            try:
                                player_home, player_away = self._get_match_players(match)
                                date_time = self._get_match_date_time(match)
                                bet_odds = self._get_match_odds(match)
                                match_odds = {
                                    "player_home": self._get_normalized_soccer_team_info(player_home),
                                    "player_away": self._get_normalized_soccer_team_info(player_away),
                                    'player_home_display': player_home,
                                    'player_away_display': player_away,
                                    "sport": betting_enums.Sports.FOOTBALL,
                                    "league": league_name,
                                    "tournament": tournament_name,
                                    "date_time": date_time,
                                    "bet_odds": bet_odds,
                                }
                                all_match_odds.append(match_odds)
                            except betting_exceptions.XpathBaseException:
                                continue
                            # Has to be changed to specific, just dirty fix
                            except Exception as e:
                                continue
                    except betting_exceptions.XpathBaseException:
                        continue

            current_scroll_position_element = new_position_element
            self._scroll_page_down(self.driver, current_scroll_position_element)

            time.sleep(5)
            all_leagues = self._get_football_leagues()
            new_position_element = all_leagues[-1]
            print("Current, previous", new_position_element == current_scroll_position_element)

        self.driver.close()
        return all_match_odds

    def _switch_to_days(self, days):
        hours = days * 24
        self.driver.get(self.url.format(hours))
        time.sleep(5)

    @classmethod
    def _scroll_page_down(cls, driver_element, element):
        # action_chains.ActionChains(driver_element).move_to_element(element).perform()
        driver_element.execute_script("arguments[0].scrollIntoView();", element)

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
        x_path_time = './/app-match/div[1]/div[1]/div[contains(@class, "match-time")]/div[2]'
        x_path_date = './/app-match/div[1]/div[1]/div[contains(@class, "match-time")]/div[1]'
        # Get date and combine
        match_time_raw = cls._get_element(driver_element, x_path_time).get_attribute("innerHTML")
        match_date_raw = cls._get_element(driver_element, x_path_date).get_attribute("innerHTML")

        if match_time_raw and match_date_raw:
            parsed_date_time = match_date_raw.split('.')[:3]
            day, month, year = parsed_date_time

            hour, minutes = match_time_raw.split(":")
            match_date_time = datetime.datetime(
                int('20' + year), int(month), int(day), int(hour), int(minutes)
            )
            return match_date_time
        return None

    @classmethod
    def _get_match_odds(cls, driver_element):
        odds_xpath = './/div[contains(@class, "match-odds")]//div[contains(@class, "odd-value")]'
        odd_wrappers = cls._get_elements(driver_element, odds_xpath)

        def parse_match_odds(odds):
            match_odds = []
            for odd in odds:
                match_odd = cls._get_element(odd, './/span').get_attribute("innerHTML")
                match_odd = match_odd.strip().replace(',', '.')
                match_odds.append(float(match_odd))
            return match_odds

        match_odds_all = parse_match_odds(odd_wrappers)

        if len(match_odds_all) == 6:
            one, ex, two, oneex, extwo, onetwo = match_odds_all
            return {
                bet_place_enums.FootballMatchPlays.ONE.value: one,
                bet_place_enums.FootballMatchPlays.X.value: ex,
                bet_place_enums.FootballMatchPlays.TWO.value: two,
                bet_place_enums.FootballMatchPlays.ONEX.value: oneex,
                bet_place_enums.FootballMatchPlays.XTWO.value: extwo,
                bet_place_enums.FootballMatchPlays.ONETWO.value: onetwo,
            }
        else:
            raise betting_exceptions.XpathGeneralException

        return {}