# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.hashers import make_password
from django.db import migrations, models


def initial_organizer(apps, schema_editor):
    Organizer = apps.get_model("pretixbase", "Organizer")
    org = Organizer()
    org.name = 'TU Wien Bibliothek'
    org.slug = 'tuw'
    org.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pretixbase', '0156_cartposition_override_tax_rate'),
    ]

    operations = [
        migrations.RunPython(initial_organizer),
    ]
