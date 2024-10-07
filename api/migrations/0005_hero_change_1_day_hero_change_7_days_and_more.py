# Generated by Django 5.1.1 on 2024-09-19 14:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_hero_created_at_alter_hero_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='hero',
            name='change_1_day',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='hero',
            name='change_7_days',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='hero',
            name='current_score',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='hero',
            name='median_14_days',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='hero',
            name='median_7_days',
            field=models.FloatField(null=True),
        ),
        migrations.CreateModel(
            name='HeroScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('score', models.FloatField()),
                ('hero', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='api.hero')),
            ],
            options={
                'unique_together': {('hero', 'date')},
            },
        ),
    ]
