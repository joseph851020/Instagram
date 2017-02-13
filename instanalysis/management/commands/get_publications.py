
import time
import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Q
from django.core.management.base import BaseCommand
from django.core.management import call_command

from instanalysis import models

logger = logging.getLogger("worker_publications")

class Command(BaseCommand):

    help = 'Obtain instagram photos for all locations (worker)'


    def handle(self, *args, **options):
        """ Script that gets publications from instagram """

        # interval update in seconds
        interval = int(models.Setting.objects.get_value('interval_updates'))
        
        locations_errors = dict()
        time_update_dates = timezone.now()
        last_api_call = timezone.now()
        while True:
            is_adhoc_running = models.Setting.objects.get_value('is_adhoc_running') == '1'
            if is_adhoc_running:
                # We wait while ahdoc query happens
                logger.info("Adhoc query is running")
                time.sleep(60)
                continue

            locations = models.InstagramLocation.objects.filter(spot__city__isnull=False) \
                                                        .exclude(id__in=locations_errors.keys())\
                                                        .exclude(instagramID='0')
            locations = locations.order_by('updated_at')
            location = locations.first()
            try:
                last_api_call = timezone.now()
                call_command('update_media', location = location.id)
                if location.id in locations_errors.keys():
                    locations_errors.pop(location.id)
            except Exception as e:
                #logger.error("There is an error updating location: %s. Error is `%s`" % (location.id, e))
                locations_errors[location.id] = timezone.now()

            time_to_process = (timezone.now() - last_api_call).seconds
            logger.debug("It took %s to process the call" % time_to_process)
            if time_to_process < interval and interval - time_to_process > 0:
                timediff = interval - time_to_process
                logger.debug("Sleeping for %s seconds" % timediff)
                time.sleep(timediff)

            if (timezone.now() - time_update_dates).seconds >= 3600:  # Every hour we do this
                # Every two hours we clean the dictionary 
                logger.debug("Cleaning locations that were not processed")
                locations_errors = dict()
                time_update_dates = timezone.now()
