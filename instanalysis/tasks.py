from __future__ import absolute_import
import os
import time
import traceback
from datetime import timedelta
from django.utils import timezone
from celery.decorators import task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.conf import settings
from django.db.models import F, Count

from instanalysis.apps.instagram.api import InstagramAPI, APIGramException

from .models import Category, Hashtag, ADHOCSearch, PublicationADHOC, Setting
from .models import InstagramRequest, Setting, Spot, InstagramLocation, ExportForm, Publication

logger = get_task_logger(__name__)


@task
def reset_adhoc():
    """ We reset the adhoc flag
    """
    s = Setting.objects.get(name="is_adhoc_running")
    s.value = '0'
    s.save()


@task()
def calculate_api_quotas():
    """
    Calculates the geonames quotas for the last hour and day
    """
    # Deleting older requests than a day ago
    # day_ago = timezone.now() - timedelta(days=1)
    hour_ago = timezone.now() - timedelta(seconds=60 * 60)

    oldest = InstagramRequest.objects.filter(created__lt=hour_ago)
    num_deleted, deleted_per_object = oldest.delete()
    logger.debug("Deleted `%s` instagram requests" % num_deleted)

    # Caculating instagram quota
    count = InstagramRequest.objects.filter(created__gte=hour_ago).count()
    logger.debug("Instagram API usage quota is `%s`" % count)
    s = Setting.objects.get(name="instagram_hourly")
    s.value = count
    s.save()

    


@task()
def update_media():
    """
    Updates media when necessary
    """
    call_command('update_media')



@task()
def process_csv_file(filepath_local):
    """ Processing csv file offline
    """
    with open(filepath_local, "r") as f:
        lines = f.readlines()

    fileparam = lines
    if len(fileparam) > 0:
        categories = fileparam[0].split(",")
        categories = categories[1:]
        #print categories

        #read the header
        categories_objects = {} #To store the Category model
        for ca in categories:
            c = ca.strip()
            try:
                c_obj = Category.objects.get(label=c)
                categories_objects[c] = c_obj
            except:
                #Create new category
                logger.debug("Creating new category from file `%s`" % c)
                c_obj = Category()
                c_obj.label = c
                c_obj.save()
                categories_objects[c] = c_obj
        #Read the rest of the file
        rows = fileparam[1:]
        for r in rows:

            values = r.split(",")
            if len(values) > 0:

                hashtag_label = values[0].replace("#","") #Delete '#' because the model returns the label with #
                if hashtag_label != '':
                    logger.debug("Processing hashtag %s" % hashtag_label)
                    #Check if hashtag exists
                    h_obj = None #Null object
                    try:
                        h_obj = Hashtag.objects.get(label=hashtag_label)
                    except:
                        #Create a new hashtag
                        h_obj = Hashtag()
                        h_obj.label = hashtag_label
                        h_obj.save()
                    
                    #Delete first column
                    values = values[1:]

                    for i in range(len(values)):
                        c_label = categories[i].strip()
                        c_obj = categories_objects[c_label]
                        val = values[i].lower().strip()
                        if val.lower() != 'x':
                            logger.debug("Removing category `%s` to hashtag `%s`" % (c_label, h_obj.label))
                            if h_obj.categories.filter(label=c_label).exists():
                                h_obj.categories.remove(c_obj)
                        else:
                            logger.debug("Adding category `%s` to hashtag `%s`" % (c_label, h_obj.label))
                            #Check if category does not exists in the ManyToMany
                            if not h_obj.categories.filter(label=c_label).exists():
                                h_obj.categories.add(c_obj)


@task
def process_adhoc_search(adhoc_search_pk):
    """ Makes an adhoc search
    """
    adhoc_search = ADHOCSearch.objects.get(id=adhoc_search_pk)
    try:
        Setting.objects.set_value('is_adhoc_running', '1')
        api = InstagramAPI()

        logger.debug("Celering adhoc search with id `%s`" % adhoc_search.id)
        logger.debug("Creating spots for this search" % adhoc_search.position)
        spot = Spot(position=adhoc_search.position, is_adhoc=True)
        spot.save()
        spots = [spot]

        for spot in spots:
            logger.debug("Obtaining locations first spot " % adhoc_search.position)
            try:
                locations = api.getLocations(spot.position.y, spot.position.x)
                logger.debug("Obtained %s locations here: %s" % (len(locations['data']), spot.position) )
                spot.update_locations(locations, is_adhoc=True)
                for location in spot.locations.all():
                    logger.debug("Obtaining publications for location %s" % location)
                    location.get_media_between_dates(adhoc_search.start_date, adhoc_search.end_date, adhoc_search.id)
            except APIGramException as e:
                logger.warning("APIGramException happened with answer: %s" % e)
                continue

        adhoc_search.status = ADHOCSearch._mt_finished
        adhoc_search.save()
        Setting.objects.set_value('is_adhoc_running', '0')
    except Exception as e:
        raise
        logger.error("Exception occurred on Adhoc Search with id `%s`: Exception is %s" % (adhoc_search_pk, e))
        adhoc_search.status = ADHOCSearch._mt_error
        adhoc_search.traceback = traceback.format_exc()
        adhoc_search.save()
        Setting.objects.set_value('is_adhoc_running', '0')


@task
def export_to_excel(data):
    """ Generates an xls file from the set of publications coming from publications_id
    Attributes:
        publications_id = [123,1223,4]
        exportform_id = 12
    """
    import shutil

    ef = ExportForm.objects.get(id=data['id'])
    if data['publications']:
        publications = Publication.objects.filter(id__in=data['publications'])
    else:
        publications = Publication.objects.none()
    if data['hashtags']:
        hashtags = Hashtag.objects.filter(id__in=data['hashtags'])
    else:
        hashtags = Hashtag.objects.none()
    hashtags = hashtags.values('label').annotate(publications=Count('label')).order_by('-publications')

    output_file = Publication.objects.export_to_excel(publications, hashtags)
    exported_excel_folder = os.path.join(settings.MEDIA_ROOT, "exports")
    file_name_export = "Export_%s.xlsx" % int(time.time())
    file_exported_path = os.path.join(exported_excel_folder, file_name_export)
    with open (file_exported_path, 'w') as fd:
        output_file.seek (0)
        shutil.copyfileobj(output_file, fd)

    ef.status = ExportForm._mt_finished
    ef.url_file = "/media/exports/%s" % file_name_export
    ef.save()


@task
def generate_categories_file():
    """ Generating the file for categories 
    """
    call_command('generate_categories_file')