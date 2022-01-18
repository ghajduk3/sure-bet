import datetime

from bettings import enums as betting_enums
from bettings.integrations.betting_places import enums as bet_place_enums
from bettings.services.data import matches as matches_service
from bettings.services.data import odds as odds_service


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
        possible_games = self._possible_games[sport]
        game_odds_mapping = self._game_odds_mapping[sport]

        all_matches = matches_service.find_matches_by_sport(sport=sport, date=datetime.date.today())

        for match in all_matches:
            bet_odd_object = odds_service.find_odds_by_match(match.id)
            raw_match_odds = {odd.betting_institution: odd.odds for odd in list(bet_odd_object)}
            institutions = list(raw_match_odds.keys())
            prepared_odds = self._prepare_odds(raw_match_odds)

            for game in possible_games:
                (first_game, first_max_bet, first_index), (second_game,second_max_bet,second_index) = self._get_maximum_odds(prepared_odds, game, game_odds_mapping)
                tap = self._calculate_TAP(first_max_bet, second_max_bet)
                if tap < 98:
                    print("Arbitrage is possible, TAP: {}! Home player {}, Away player {}, game ({}-{}), bet_place ({}-{}), max_odds ({}-{}), odds {}".format(
                        tap,
                        match.player_home,
                        match.player_away,
                        first_game.name,
                        second_game.name,
                        bet_place_enums.BettingInstitutions(institutions[first_index]).name,
                        bet_place_enums.BettingInstitutions(institutions[second_index]).name,
                        first_max_bet,
                        second_max_bet,
                        prepared_odds
                        )
                    )

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