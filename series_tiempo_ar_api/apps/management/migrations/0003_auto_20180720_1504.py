# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-07-20 18:04
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0002_auto_20180510_1709'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='node',
            name='admins',
        ),
        migrations.DeleteModel(
            name='Node',
        ),
    ]
