from django.db import models

from bettings import enums as betting_enums
from bettings.models import match


class BetOdds(models.Model):
    betting_institution = models.IntegerField(
        choices=betting_enums.BettingInstitutions.choices(),
        default=betting_enums.BettingInstitutions.OLIMPWIN,
    )
    odds = models.JSONField()
    match = models.ForeignKey(match.Match, on_delete=models.CASCADE, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sport_match_odds"
