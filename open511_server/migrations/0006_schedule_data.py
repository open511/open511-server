# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.db import models, migrations

from lxml import etree
from lxml.builder import E

def convert_schedule(orig_schedule):
    # Takes an lxml Element for <schedules>, returns a new <schedule> Element
    nu = etree.Element('schedule')
    recurring = etree.Element('recurring_schedules')
    specific = []
    for child in orig_schedule:
        if child.xpath('specific_dates'):
            specific = child.xpath('specific_dates/specific_date/text()')
        else:
            child.tag = 'recurring_schedule'
            for sched_tag in child:
                if sched_tag.tag in ('start_time', 'end_time'):
                    sched_tag.tag = 'daily_' + sched_tag.tag
            recurring.append(child)
    if len(recurring):
        nu.append(recurring)
        if specific:
            nu.append(E.exceptions(*[E.exception(str(s)) for s in specific]))
    elif specific:
        # We have exceptions but no recurring schedules.
        intervals = E.intervals()
        for s in specific:
            date, _, times = s.partition(' ')
            for timepair in times.split(' '):
                start_time, end_time = timepair.split('-')
                intervals.append(E.interval('{}T{}/{}T{}'.format(date, start_time, date, end_time)))
        assert len(intervals)
        nu.append(intervals)
    else:
        raise ValueError("Invalid schedule data: %s" % etree.tostring(orig_schedule))
    return nu

def update_schedule_data(apps, schema_editor):
    RoadEvent = apps.get_model("open511", "RoadEvent")
    for event in RoadEvent.objects.all():
        elem = etree.fromstring(event.xml_data)
        try:
            old_sched = elem.xpath('schedules')[0]
        except IndexError:
            print(etree.tostring(elem))
            raise
        new_sched = convert_schedule(old_sched)
        elem.remove(old_sched)
        elem.append(new_sched)
        event.xml_data = etree.tostring(elem)
        event.save()


class Migration(migrations.Migration):

    dependencies = [
        ('open511', '0005_roadevent'),
    ]

    operations = [
        migrations.RunPython(update_schedule_data)
    ]
