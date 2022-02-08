import json
import random
import logging
import datetime

from bettings import enums as betting_enums
from bettings.integrations import enums as bet_place_enums
from bettings.services.data import matches as matches_service
from bettings.services.data import odds as odds_service


logger = logging.getLogger(__name__)
_LOG_PREFIX = "[MATCH-PROCESSING-SERVICE]"


class ArbitrageBets:
    _possible_games = {
        betting_enums.Sports.FOOTBALL: [
            (
                bet_place_enums.FootballMatchPlays.X,
                bet_place_enums.FootballMatchPlays.ONETWO,
            ),
            (
                bet_place_enums.FootballMatchPlays.ONE,
                bet_place_enums.FootballMatchPlays.XTWO,
            ),
            (
                bet_place_enums.FootballMatchPlays.TWO,
                bet_place_enums.FootballMatchPlays.ONEX,
            ),
        ]
    }

    _game_odds_mapping = {
        betting_enums.Sports.FOOTBALL: {
            bet_place_enums.FootballMatchPlays.ONE: 0,
            bet_place_enums.FootballMatchPlays.TWO: 1,
            bet_place_enums.FootballMatchPlays.X: 2,
            bet_place_enums.FootballMatchPlays.ONETWO: 3,
            bet_place_enums.FootballMatchPlays.ONEX: 4,
            bet_place_enums.FootballMatchPlays.XTWO: 5,
        },
    }

    def calculate_arbitrage_bets_by_sport(self, sport):
        logger.info("{} Calculating arbitrage bets for sport {}".format(_LOG_PREFIX, sport.name))
        possible_games = self._possible_games[sport]
        game_odds_mapping = self._game_odds_mapping[sport]

        all_matches = matches_service.find_matches_by_sport(sport=sport, date=datetime.date.today())
        all_arbitrages = []
        print(len(all_matches))
        for match in all_matches:

            bet_odd_object = odds_service.find_odds_by_match(match.id)
            raw_match_odds = {odd.betting_institution: odd.odds for odd in list(bet_odd_object)}
            institutions = list(raw_match_odds.keys())

            prepared_odds = self._prepare_odds(raw_match_odds)

            for game in possible_games:
                try:
                    (first_game, first_max_bet, first_index), (second_game,second_max_bet, second_index) = self._get_maximum_odds(prepared_odds, game, game_odds_mapping)
                    tap = self._calculate_TAP(first_max_bet, second_max_bet)
                    arb_bet = self._report_arbitrage_bet(
                        match,
                        tap,
                        first_game,
                        first_max_bet,
                        bet_place_enums.BettingInstitutions(institutions[first_index]).name,
                        second_game,
                        second_max_bet,
                        bet_place_enums.BettingInstitutions(institutions[second_index]).name,
                    )
                    if arb_bet:
                        all_arbitrages.append(arb_bet)
                except Exception:
                    continue

        return all_arbitrages

    def _report_arbitrage_bet(self, match, tap, first_game, first_max_bet, first_bet_place, second_game, second_max_bet, second_bet_place):
        arbitrage_bet = {
            'TAP': tap,
            'home_player_display': match.player_home_display,
            'away_player_display': match.player_away_display,
            'home_player': match.player_home,
            'away_player': match.player_away,
            'date_time': match.date_time,
            'league': match.league,
            'game_pair': '{} - {}'.format(first_game.name, second_game.name),
            'bet_odds': '{} - {}'.format(first_max_bet, second_max_bet),
            'bet_place': '{} - {}'.format(first_bet_place, second_bet_place)
        }

        if tap < 100:
            print(arbitrage_bet)
            # logger.info("{} Arbitrage is possible. {}".format(_LOG_PREFIX, json.dumps(arbitrage_bet)))
            return arbitrage_bet

        return None

    @staticmethod
    def _calculate_TAP(first_odd, second_odd):
        return (1 / first_odd) * 100 + (1 / second_odd) * 100

    @staticmethod
    def _prepare_odds(odds):
        return list(zip(*[list(odd.values()) for odd in odds.values()]))

    @classmethod
    def _get_maximum_odds(cls, odds, game, mapping):
        first_game, second_game = game
        first_game_odds = odds[mapping[first_game]]
        first_game_max = max(first_game_odds)
        second_game_odds = odds[mapping[second_game]]
        second_game_max = max(second_game_odds)
        return (first_game, first_game_max, first_game_odds.index(first_game_max)), (
            second_game,
            second_game_max,
            second_game_odds.index(second_game_max),
        )
