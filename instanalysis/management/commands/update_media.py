

import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Q
from django.core.management.base import BaseCommand

from instanalysis import models

logger = logging.getLogger("worker_publications")

class Command(BaseCommand):
    """ This command updates the latest media for all or an specific location

    :param --commit: Do not alter database if assigned to False
    :param --all: Updates all locations
    :param --location: Updates only an specific location

    :Examples:
        $ python manage.py update_media
        $ python manage.py update_media --commit=True
        $ python manage.py update_media --location
    """
    help = 'Obtain instagram photos for all locations'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--commit',
                            dest='commit',
                            default=True,
                            help='Perform changes in database')
        parser.add_argument('--all',
                            dest='all',
                            default=False,
                            help='Update media for all locations')
        parser.add_argument('--location',
                            dest='location',
                            default=None,
                            help='Update media for an specific location')

    def handle(self, *args, **options):
        if not bool(options["commit"]):
            logger.info("No changes in the database will be performed.")
        if options['all'] and options['location'] is None:
            logger.info("Updating media for all locations in the system")
        elif options['all'] and options['location'] is not None:
            logger.error("You cannot pretend to update all and an specific location. Exiting...")
            exit(1)

        if options['location'] is None:
            interval_updates = models.Setting.objects.get_value('interval_updates')
            #logger.debug("Retrieving locations that where updated more than `%s` minutes ago" % interval_updates)
            #time_ago = timezone.now() - timedelta(seconds=60 * int(interval_updates))
            locations = models.InstagramLocation.objects.filter(spot__city__isnull=False)
            locations = locations.order_by('updated_at')
        else:
            try:
                locations = models.InstagramLocation.objects.filter(pk=options['location'])
            except models.InstagramLocation.DoesNotExist:
                logger.error("Location with id `%s` not found" % options['location'])


        location = locations.first()
        logger.info("Updating location %s" % location)
        if location is None:
            logger.debug("No locations eligible to be updated")
        else:
            logger.debug("Updating media for location %s" % location)
            location.get_latest_media(commit=True)
