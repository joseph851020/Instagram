import logging
import time

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from instanalysis.models import City, Spot

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
        #madrid = City.objects.get(name='Madrid')
        barcelona = City.objects.get(name='Barcelona')
        Spot.objects.filter(city__name='Barcelona').delete()
        spot = Spot(position=barcelona.center, city=barcelona)
        spot.save()
        center_spot = spot
        for i in range(-2, 2):
            spot_x = Spot(position=Point(center_spot.position.x+(0.0178*i), center_spot.position.y), city=barcelona)
            if i != 0:
                spot_x.save()
            for j in range(-2, 2):
                if j == 0:
                    continue
                spot_y = Spot(position=Point(spot_x.position.x, spot_x.position.y+(0.0134*j)), city=barcelona)
                spot_y.save()
