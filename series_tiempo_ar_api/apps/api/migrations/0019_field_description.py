# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-12-07 15:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_auto_20171130_1027'),
    ]

    operations = [
        migrations.AddField(
            model_name='field',
            name='description',
            field=models.CharField(default='', max_length=2000),
            preserve_default=False,
        ),
    ]