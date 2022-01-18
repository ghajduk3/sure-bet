from django import db as django_db
from bettings.models import match
from django.db.models import Q


def find_match_by_filters(player_home, player_away, sport):
    return match.Match.objects.filter(
        (Q(player_away=player_away) | Q(player_home=player_home)),
        sport=sport,
    ).first()


def find_matches_by_sport(sport, date):
    return match.Match.objects.filter(
        sport=sport,
        date_time__date=date,
    )

def create_match(fields):
    return match.Match.objects.create(**fields)

