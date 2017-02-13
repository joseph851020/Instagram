# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-15 07:14
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('instanalysis', '0016_auto_20160519_1108'),
    ]

    operations = [
        migrations.CreateModel(
            name='ADHOCSearch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('status', models.CharField(choices=[(0, b'In progress'), (1, b'Completed')], max_length=1)),
                ('position', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('radius', models.PositiveIntegerField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('month', models.PositiveIntegerField()),
                ('weekday', models.PositiveIntegerField()),
                ('slotrange', models.PositiveIntegerField()),
                ('categories', models.ManyToManyField(to='instanalysis.Category')),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
        ),
        migrations.AlterField(
            model_name='hashtag',
            name='categories',
            field=models.ManyToManyField(blank=True, to='instanalysis.Category'),
        ),
        migrations.AddField(
            model_name='adhocsearch',
            name='hashtags',
            field=models.ManyToManyField(to='instanalysis.Hashtag'),
        ),
        migrations.AddField(
            model_name='publication',
            name='adhocsearch',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='instanalysis.ADHOCSearch'),
        ),
    ]