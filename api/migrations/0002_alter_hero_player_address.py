# Generated by Django 5.1.1 on 2024-09-18 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hero',
            name='player_address',
            field=models.CharField(blank=True, max_length=42, null=True),
        ),
    ]
