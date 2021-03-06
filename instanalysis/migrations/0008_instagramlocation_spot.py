# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-13 15:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('instanalysis', '0007_auto_20160513_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='instagramlocation',
            name='spot',
            field=models.ForeignKey(default=1, help_text=b'Spot where this location is associated.', on_delete=django.db.models.deletion.CASCADE, to='instanalysis.Spot'),
            preserve_default=False,
        ),
    ]
