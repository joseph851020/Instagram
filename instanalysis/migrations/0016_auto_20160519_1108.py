# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-19 09:08
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import instanalysis.utils
import django_extensions.db.fields

class Migration(migrations.Migration):

    dependencies = [
        ('instanalysis', '0015_auto_20160517_2007'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicationADHOC',
            fields=[
                ('publication_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='instanalysis.Publication')),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
            bases=('instanalysis.publication',),
        ),
        migrations.AlterField(
            model_name='instagramlocation',
            name='updated_at',
            field=models.DateTimeField(blank=True, default=instanalysis.utils._get_init_datetime_location, null=True),
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('label', models.CharField(max_length=250, unique=True)),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
        ),
        migrations.AlterField(
            model_name='hashtag',
            name='publications',
            field=models.ManyToManyField(blank=True, null=True, to='instanalysis.Publication'),
        ),
        migrations.AddField(
            model_name='hashtag',
            name='categories',
            field=models.ManyToManyField(to='instanalysis.Category'),
        ),
    ]
