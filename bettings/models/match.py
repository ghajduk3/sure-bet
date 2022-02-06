from django.db import models

from bettings import enums as betting_enums


class Match(models.Model):
    player_home = models.CharField(max_length=50)
    player_away = models.CharField(max_length=50)
    player_home_display = models.CharField(max_length=50)
    player_away_display = models.CharField(max_length=50)
    date_time = models.DateTimeField()
    sport = models.IntegerField(
        choices=betting_enums.Sports.choices(), default=betting_enums.Sports.FOOTBALL
    )
    league = models.CharField(max_length=150, blank=True, null=True)
    tournament = models.CharField(max_length=100, blank=True, null=True)
    batch = models.IntegerField(null=True, default=0)
    betting_institution = models.CharField(max_length=100, default='1')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "sport_match"


