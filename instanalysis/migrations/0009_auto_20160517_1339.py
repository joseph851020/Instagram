# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-17 11:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('instanalysis', '0008_instagramlocation_spot'),
    ]

    operations = [
        migrations.RenameField(
            model_name='instagramuser',
            old_name='instagtamID',
            new_name='instagramID',
        ),
        migrations.AddField(
            model_name='instagramlocation',
            name='latest_media_id',
            field=models.CharField(blank=True, help_text=b'', max_length=256, null=True),
        ),
        migrations.AlterField(
            model_name='publication',
            name='author',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='instanalysis.InstagramUser'),
        ),
        migrations.AlterField(
            model_name='publication',
            name='location',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='instanalysis.InstagramLocation'),
        ),
    ]
