from django import db as django_db
from bettings.models import match
from django.db.models import Q


def find_match_by_filters(player_home, player_away, sport, batch):
    return match.Match.objects.filter(
        ~Q(batch=batch),
        (Q(player_away=player_away) | Q(player_home=player_home)),
        sport=sport,
    ).first()


def find_matches_by_sport(sport, date):
    return match.Match.objects.filter(
        sport=sport,
        date_time__date__gte=date,
    )


def get_or_create_match(match_fields, batch, client_id):
    if 'everton' in match_fields.get('player_away', []) or 'everton' in match_fields.get('player_home', []):
        print("Bet isnt", client_id, match_fields.get('player_away'), match_fields.get('player_home'))

    existing_matches = match.Match.objects.filter(
        Q(player_away=match_fields.get('player_away')) | Q(player_home=match_fields.get('player_home')),
        ~Q(betting_institution__contains=str(client_id)),
        date_time=match_fields.get('date_time'),
        # batch=batch,
    )

    if len(existing_matches) >= 2:
        existing_match = _get_matches_tiebreak(existing_matches, match_fields)
    else:
        existing_match = existing_matches.first()

    if existing_match:
        existing_match.betting_institution = existing_match.betting_institution + str(client_id)
        existing_match.save(update_fields=['betting_institution'])
    else:
        same_match = match.Match.objects.filter(
            Q(player_away=match_fields.get('player_away')) & Q(player_home=match_fields.get('player_home')),
            batch=batch
        ).first()

        if same_match:
            return same_match


        match_fields.update({'batch': batch, 'betting_institution': str(client_id)})
        return match.Match.objects.create(
            **match_fields
        )

    return existing_match

def _get_matches_tiebreak(existing_matches, match_fields):
    existing_match = existing_matches.filter(
        Q(player_away=match_fields.get('player_away')) & Q(player_home=match_fields.get('player_home')),
        date_time=match_fields.get('date_time')
    ).first()
    return existing_match
