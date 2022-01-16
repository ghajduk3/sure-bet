from bettings.models import odds as betting_odd_model


def update_or_create_bet_odds(client, odds, match_id):
    return betting_odd_model.BetOdds.objects.update_or_create(
        betting_institution=client,
        match_id=match_id,
        defaults={'odds': odds}
    )


def find_odds_by_match(match_id):
    return betting_odd_model.BetOdds.objects.filter(
        match_id=match_id,
    )