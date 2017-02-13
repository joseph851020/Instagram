import logging
import csv
import os

from django.core.management.base import BaseCommand
from django.conf import settings
from instanalysis.models import Category, Hashtag

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """ This command updates instagram locations in the database

    :param --fake: Do not alter database, but the API query is performed

    :Examples:
        $ python manage.py get_photos

        $ python manage.py get_photos --fake=True
    """
    help = 'Generates the file of categories to download and publishes it in static'

    def handle(self, *args, **options):

        # Get csv header
        categories = Category.objects.all().order_by('label')
        dcat = dict()
        i = 1
        for c in categories:
            dcat[c.id] = {'label': c.label, 'column': i}
            i += 1

        logger.debug(dcat)
        # Moving file to staticfiles folder
        file_output = os.path.join(settings.STATICFILES_PATH, "export_categories.csv")
        logger.debug("Writing file %s" % file_output)

        with open(file_output, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            # Header
            header = []
            for c in categories:
                header.append(c.label.rstrip())
            header.insert(0, 'Hashtag')
            csvwriter.writerow(header)

            # Header rows
            hashtags = Hashtag.objects.all()
            logger.debug("Writing hashtags: %s" % hashtags.count())
            for h in hashtags:
                logger.debug("Writing hashtag %s" % h)
                cat_hashtag = h.categories.all()
                row = ['' for c in range(0, categories.count() + 1)]
                for c in cat_hashtag:
                    row[dcat[c.id]['column']] = 'X'
                row[0] = h.label.encode("utf-8")
                csvwriter.writerow(row)

        # header.insert(0, 'Hashtag')

        # # Create the HttpResponse object with the appropriate CSV header.

        # writer = csv.writer(response)
        # writer.writerow(header)
        # for r in rows:
        #     writer.writerow(r)



