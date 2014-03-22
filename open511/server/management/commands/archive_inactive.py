"""
To be executed in a cron job: find all ACTIVE events which don't have
any scheduled times in the future and archives them.
"""

from django.core.management.base import BaseCommand

from open511.server.models import RoadEvent


class Command(BaseCommand):

    def handle(self, **options):

        count = 0

        ids_to_deactivate = []

        for rdev in RoadEvent.objects.filter(active=True, jurisdiction__external_url=''):
            if not rdev.has_remaining_periods():
                ids_to_deactivate.append(rdev.id)

        if ids_to_deactivate:
            count = RoadEvent.objects.filter(active=True, id__in=ids_to_deactivate).update(active=False)

        if count:
            print '%s event%s archived' % (count, 's' if count > 1 else '')
