# Generated by Django 4.0.1 on 2022-02-05 17:17

import bettings.enums
import bettings.integrations.enums
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player_home', models.CharField(max_length=50)),
                ('player_away', models.CharField(max_length=50)),
                ('player_home_display', models.CharField(max_length=50)),
                ('player_away_display', models.CharField(max_length=50)),
                ('date_time', models.DateTimeField()),
                ('sport', models.IntegerField(choices=[(1, 'FOOTBALL')], default=bettings.enums.Sports['FOOTBALL'])),
                ('league', models.CharField(blank=True, max_length=150, null=True)),
                ('tournament', models.CharField(blank=True, max_length=100, null=True)),
                ('batch', models.IntegerField(default=0, null=True)),
                ('betting_institution', models.CharField(default='1', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'sport_match',
            },
        ),
        migrations.CreateModel(
            name='BetOdds',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('betting_institution', models.IntegerField(choices=[(1, 'OLIMP'), (2, 'ZLATNIK'), (3, 'ADMIRAL'), (4, 'MERIDIAN'), (5, 'VOLCANO'), (6, 'SBBET'), (7, 'PREMIER')], default=bettings.integrations.enums.BettingInstitutions['OLIMPWIN'])),
                ('odds', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bettings.match')),
            ],
            options={
                'db_table': 'sport_match_odds',
            },
        ),
    ]
