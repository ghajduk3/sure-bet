import datetime
import logging
import re
import time
import typing

from django.conf import settings
from selenium import webdriver
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox import options
from selenium.webdriver.common import action_chains

from bettings import enums as betting_enums
from bettings.integrations import enums as bet_place_enums
from bettings.integrations.scrapers import exceptions as betting_exceptions
from bettings.integrations.scrapers.betting_places import base as base_integration


logger = logging.getLogger(__name__)
_LOG_PREFIX = "[OLIMP_CLIENT]"


class OlimpBaseClient(base_integration.IntegrationBaseClient):
    def __init__(self, sport, headless=True):
        # type: (betting_enums.Sports, bool) -> None
        super(OlimpBaseClient, self).__init__(headless)
        self.url = settings.SCRAPER_CLIENT_SPORT_URLS[
            bet_place_enums.BettingInstitutions.OLIMPWIN.name.upper()
        ][sport.name.upper()]


class OlimpSoccerClient(OlimpBaseClient):
    def __init__(self):
        super(OlimpSoccerClient, self).__init__(betting_enums.Sports.FOOTBALL)
        self.driver.get(self.url)

    def get_matches_odds_all(self, days=3):
        days_to_fetch = [datetime.date.today() + datetime.timedelta(days=day) for day in range(days)]
        match_odds_all_days = []
        for date in days_to_fetch:
            try:
                self._switch_to_date_football(self.driver, date)
                match_odds_all_days.extend(self.get_matches_odds())
            except betting_exceptions.XpathGeneralException:
                continue

        self.driver.close()
        return match_odds_all_days

    def get_matches_odds(self):
        all_match_odds = []
        for league in self.get_football_leagues():
            league_name = self._get_league_name(league)
            tournament_name = self._get_tournament_name(league)

            for match in self.get_league_matches(league):
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
                except betting_exceptions.XpathGeneralException:
                    continue
        return all_match_odds

    def get_football_leagues(self):
        # type: () -> typing.Optional[typing.List]
        x_path = '//*[@id="ctl00_ucOdds_fullPonuda"]/div[@class="liga 2"]'
        football_leagues = self._get_elements(self.driver, x_path)
        logger.info(
            "{} Found {} football leagues.".format(_LOG_PREFIX, len(football_leagues))
        )
        return football_leagues

    @classmethod
    def _switch_to_date_football(cls, driver_element, date):
        date_formatted = 'Weak{}{}{}'.format(date.day, date.month, date.year)
        x_path_date ='//table[@id="dani"]/tbody//td[@id="{}"]'.format(date_formatted)
        date_element = cls._get_element(driver_element, x_path_date)
        action_chains.ActionChains(driver_element).move_to_element(date_element).click().perform()

        time.sleep(2)
        x_path_football = '//*[@id="v_m_sportovi"]/tbody/tr[2]/th/div[1]/table/tbody/tr/td[1]/a'
        football_element = cls._get_element(driver_element, x_path_football)
        action_chains.ActionChains(driver_element).move_to_element(football_element).click().perform()


    @classmethod
    def _get_match_odds(cls, driver_element):
        # for now only base odds 1,x,2,1x,x2
        x_path = './td[@class="tgp"]'
        # parse and return dict
        match_odds = [
            cls._parse_match_odd(odd.text)
            for odd in cls._get_elements(driver_element, x_path)
        ]
        if len(match_odds) == 6:
            one, ex, two, oneex, extwo, onetwo = match_odds
            return {
                bet_place_enums.FootballMatchPlays.ONE.value: one,
                bet_place_enums.FootballMatchPlays.X.value: ex,
                bet_place_enums.FootballMatchPlays.TWO.value: two,
                bet_place_enums.FootballMatchPlays.ONEX.value: oneex,
                bet_place_enums.FootballMatchPlays.XTWO.value: extwo,
                bet_place_enums.FootballMatchPlays.ONETWO.value: onetwo,
            }
        else:
            raise betting_exceptions.XpathGeneralException()

    @classmethod
    def get_league_matches(cls, driver_element):
        # type: () -> typing.Optional[typing.List]
        x_path = './/table[@class="parovi"]/tbody/tr[@ot]'
        league_matches = cls._get_elements(driver_element, x_path)
        logger.info(
            "{} Found {} league matches.".format(_LOG_PREFIX, len(league_matches))
        )
        return league_matches

    @classmethod
    def _get_league_name(cls, driver_element):
        x_path = './/div[1]/table/tbody/tr/td[@class="grupa"]/span[2]'
        return cls._get_element(driver_element, x_path).text

    @classmethod
    def _get_tournament_name(cls, driver_element):
        x_path = './/div[1]/table/tbody/tr/td[@class="grupa"]/span[3]'
        return cls._get_element(driver_element, x_path).text

    @classmethod
    def _get_match_players(cls, driver_element):
        x_path = "./td[@title]"
        # parse this to get both match players
        players = cls._get_element(driver_element, x_path).text
        if players:
            home_player, away_player = players.split(" - ")
            return home_player, away_player

        return players

    @classmethod
    def _get_match_date_time(cls, driver_element):
        x_path_time = './td[@class="datumPar"]'
        x_path_date = '//td[@class="cal current"]'
        # Get date and combine
        match_time_raw = cls._get_element(driver_element, x_path_time).text
        match_date_raw = cls._get_element(
            driver_element, x_path_date
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
