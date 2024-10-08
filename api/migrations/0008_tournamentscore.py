# Generated by Django 5.1.1 on 2024-10-02 08:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_alter_hero_volume'),
    ]

    operations = [
        migrations.CreateModel(
            name='TournamentScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('index', models.IntegerField()),
                ('score', models.FloatField()),
                ('hero', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tournament_scores', to='api.hero')),
            ],
            options={
                'unique_together': {('hero', 'index')},
            },
        ),
    ]
