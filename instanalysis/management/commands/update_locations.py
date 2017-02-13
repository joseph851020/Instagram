import logging
import time

from django.core.management.base import BaseCommand

from instanalysis.models import City
from instanalysis.apps.instagram.api import InstagramAPI

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """ This command updates instagram locations in the database

    :param --fake: Do not alter database, but the API query is performed

    :Examples:
        $ python manage.py get_photos

        $ python manage.py get_photos --fake=True
    """
    help = 'Obtain instagram photos for all locations'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--fake',
                            dest='fake',
                            default=False,
                            help='Do not perform changes in database')

    def handle(self, *args, **options):
        if bool(options["fake"]):
            logger.info("No changes in the database will be performed.")

        logger.info("Updating Instagram locations")
        api = InstagramAPI()
        for city in City.objects.filter(name="Madrid"):
            logger.info("Updating locations for city `%s`" % city.name)
            for spot in city.spot_set.all():
                lat = spot.position.y
                lng = spot.position.x
                locations = api.getLocations(lat, lng)
                spot.update_locations(locations)
                time.sleep(1)

        logger.info("Process finishes")
