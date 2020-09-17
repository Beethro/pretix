# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.hashers import make_password
from django.db import migrations, models


def initial_data(apps, schema_editor):
    Organizer = apps.get_model("pretixbase", "Organizer")
    org = Organizer()
    org.name = 'TU Wien Bibliothek'
    org.slug = 'tuw'
    org.save()

    # default admin user
    User = apps.get_model("pretixbase", "User")
    user = User.objects.get(pk=1)

    Team = apps.get_model("pretixbase", "Team")
    team = Team()
    team.organizer = org
    team.name = 'Administrators'
    team.all_events = True
    team.can_create_events = True
    team.can_change_teams = True
    team.can_change_organizer_settings = True
    team.can_manage_gift_cards = True
    team.can_change_event_settings = True
    team.can_change_items = True
    team.can_view_orders = True
    team.can_change_orders = True
    team.can_view_vouchers = True
    team.can_change_vouchers = True
    team.save()

    team.members.add(user)
    team.save()


class Migration(migrations.Migration):

    dependencies = [
        ('pretixbase', '0156_cartposition_override_tax_rate'),
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
