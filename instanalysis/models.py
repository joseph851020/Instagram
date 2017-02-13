import logging
import StringIO
from pytz.exceptions import AmbiguousTimeError

from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django_extensions.db.models import TimeStampedModel
from django.core.exceptions import MultipleObjectsReturned


from xlsxwriter.workbook import Workbook

from . import api
from .utils import _get_init_datetime_location, created_from_timestamp_instagram

logger = logging.getLogger(__name__)


class PublicationManager(models.Manager):

    def export_to_excel(self, data_publications, data_tags):
        """ Export the current queryset to CSV.
        Data is a Queryset of Publication, these are the publications that will be taken into account.
        """
        # create a workbook in memory
        output = StringIO.StringIO()
        book = Workbook(output)
        sheet = book.add_worksheet('Media')
        # Adding media page
        titles = ["Type", "City", "Date", "Instagram Id", "Instagram URL", "caption", "likes",
                  "author", "location id", "location name", "lat", "lng"]
        i = 0
        for title in titles:
            sheet.write(0, i, title)
            i += 1
        row_index = 1
        # We improve the performance making sure that we query by related data using select_related
        # and prefetch_related when needed
        data_publications = data_publications.select_related('location__spot__city', 'author', 'location')
        for el in data_publications:
            # ["Type", "Date", "Instagram Id", "Instagram URL", "caption", "likes", "author", "author_profile",
            #      "location id", "location name", "lat", "lng"]
            mediaType = 'Photo' if el.mediaType == '1' else 'Video'
            city = el.location.spot.city.name if el.location is not None and el.location.spot.city is not None else "Undefined"
            publication_date = el.publication_date.strftime("%d/%m/%Y %H:%M")
            username = el.author.username if el.author is not None else "Undefined"
            location_id = el.location.instagramID if el.location is not None else "Undefined"
            location_name = el.location.name if el.location is not None else "Undefined"
            location_lat = el.location.position.y if el.location is not None else "Undefined"
            location_lng = el.location.position.x if el.location is not None else "Undefined"

            row = [mediaType, city, publication_date, el.instagramID, el.instagram_url, el.caption, el.likes,
                   username, location_id, location_name, location_lat,
                   location_lng]
            column_index = 0
            for value in row:
                sheet.write(row_index, column_index, value)
                column_index += 1
            row_index += 1

        # Adding tag page
        sheet = book.add_worksheet('Tags')
        titles = ["Hashtag", "Quantity"]
        i = 0
        for title in titles:
            sheet.write(0, i, title)
            i += 1
        row_index = 1
        if data_tags is not None:
            for el in data_tags:
                sheet.write(row_index, 0, el.get('label'))
                sheet.write(row_index, 1, el.get('publications'))
                row_index += 1
        else:
            sheet.write(1, 0, "No hashtags in query")

        book.close()

        # construct response
        output.seek(0)
        return output


class Publication(TimeStampedModel):
    """ Information related to a publication from a city
    """
    _mt_video, _mt_photo = range(0, 2)
    _choices_mediaType = ((_mt_video, 'Video'), (_mt_photo, 'Photo'))

    instagramID = models.CharField(max_length=60, help_text="Publication ID in instagram")
    publication_date = models.DateTimeField()
    mediaType = models.CharField(max_length=1, choices=_choices_mediaType)

    instagram_url = models.URLField()
    caption = models.CharField(max_length=2200, null=True)
    likes = models.PositiveIntegerField()

    author = models.ForeignKey('InstagramUser', null=True)
    location = models.ForeignKey('InstagramLocation', null=True)
    adhocsearch = models.ForeignKey('ADHOCSearch', null=True)

    objects = PublicationManager()

    def __unicode__(self):
        _type = self._choices_mediaType[int(self.mediaType)][1]
        return "<Media %s: %s %s>" % (_type, self.instagramID, self.publication_date)


class PublicationADHOC(PublicationManager):
    pass


class PublicationADHOC(Publication):
    """ Model that stores adhoc publications, so we can use Publication methods and querysets
    """
    objects = PublicationADHOC()


class ADHOCSearch(TimeStampedModel):

    _mt_progress, _mt_finished, _mt_error = range(0, 3)
    _choices_status = ((_mt_progress, 'In progress'), (_mt_finished, 'Completed'), (_mt_error, 'Error'))
    status = models.CharField(max_length=1, choices=_choices_status, default=_mt_progress)

    position = models.PointField()
    radius = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    month = models.PositiveIntegerField(null=True, blank=True)
    weekday = models.PositiveIntegerField(null=True, blank=True)
    slotrange = models.PositiveIntegerField(null=True, blank=True)
    hashtags = models.ManyToManyField('Hashtag', null=True,blank=True)
    categories = models.ManyToManyField('Category', null=True, blank=True)
    query_url = models.TextField()
    traceback = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return "AdhocSearch %s" % self.id


class Category(TimeStampedModel):
    """
    Stores all categories
    """
    label = models.CharField(max_length=250, unique=True)

    def __unicode__(self):
        return "<Category `%s`>" % self.label


class Hashtag(TimeStampedModel):
    """ Stores all hashtags that have been stored
    """
    label = models.CharField(db_index=True, max_length=250, unique=True)
    publications = models.ManyToManyField(Publication, null=True, blank=True)
    categories = models.ManyToManyField(Category, blank=True)

    def __unicode__(self):
        return "<Hashtag `#%s`" % self.label


class InstagramUser(TimeStampedModel):
    """ Instagram users account information
    """
    username = models.CharField(max_length=256)
    instagramID = models.CharField(max_length=300)

    def __unicode__(self):
        return "<InstagramUser: %s>" % self.username


class InstagramLocation(TimeStampedModel):
    """ Instagram location information
    """
    name = models.CharField(db_index=True, max_length=300)
    instagramID = models.CharField(max_length=200)
    position = models.PointField()
    spot = models.ForeignKey('instanalysis.Spot',
                             help_text='Spot where this location is associated.', related_name='locations')
    latest_media_id = models.CharField(max_length=256, blank=True, null=True,
                                       help_text='Last id obtained, useful for pagination')
    updated_at = models.DateTimeField(blank=True, null=True, default=_get_init_datetime_location)

    def __unicode__(self):
        return "<InstagramLocation: `%s`, InstagramID: `%s`>" % (self.name, self.instagramID)

    def get_latest_media(self, commit=True):
        """ Obtains and updates the posts for this location and Stores them in the database
        """

        logger.debug("Getting latest posts from location `%s`" % self.name)
        data, new_min_id = api.getLatestPostsInfo(self.instagramID, min_id=self.latest_media_id)
        for media_post in data:
            if Publication.objects.filter(instagramID=media_post['id']).count() > 0:
                logger.warning("Publication with id `%s` already in database" % media_post['id'])
            else:
                publication = self.add_media_from_api(media_post)
                logger.debug("Publication's instagram ID is `%s`" % publication.instagramID)

        logger.debug("Updating min_id for location. New min_id is %s" % new_min_id)
        self.latest_media_id = new_min_id
        self.updated_at = timezone.now()
        self.save()

    def get_media_between_dates(self, start_date, end_date, adhoc_id):
        """ Retrieves media from this location and stores only those that belongs to the dates passed by parameter
        """
        logger.debug("Getting media from %s and %s por location %s" % (start_date, end_date, self))
        data, new_min_id = api.getLatestPostsInfo(self.instagramID, min_id=self.latest_media_id,
                                                  is_adhoc=True, start_date=start_date)
        for media_post in data:
            c = created_from_timestamp_instagram(media_post['created_time'])
            created_time = datetime(c.year, c.month, c.day)
            logger.debug("Publication with date `%s`" % created_time)
            publication = self.add_media_from_api(media_post, adhoc_id=adhoc_id)

    def add_media_from_api(self, data, adhoc_id=None):
        """ Creates a new Publication item from data provided by a dictionary. The dictionary contains the
        information as described as in https://www.instagram.com/developer/endpoints/media/#get_media
        Returns the created publication
        """
        created_timestamp = created_from_timestamp_instagram(data['created_time'])
        mediaType = Publication._mt_photo if data['type'] == 'image' else Publication._mt_video
        try:
            author, created = InstagramUser.objects.get_or_create(username=data['user']['username'],
                                                                  instagramID=data['user']['id'])
        except MultipleObjectsReturned:
            author = InstagramUser.objects.filter(username=data['user']['username'],
                                                  instagramID=data['user']['id']).first()

        logger.info("Publication with id %s saved!!!" % data['id'])
        p = Publication(instagramID=data['id'],
                       publication_date=created_timestamp,
                       mediaType=mediaType,
                       instagram_url=data['link'],
                       caption=data['caption']['text'] if data['caption'] is not None else None,
                       likes=data['likes']['count'],
                       author=author,
                       location=self,
                       adhocsearch=ADHOCSearch.objects.get(id=adhoc_id) if adhoc_id is not None else None)
        p.save()
        # Linking hashtags
        for hashtag in data['tags']:
            hashtag, created = Hashtag.objects.get_or_create(label=hashtag)
            hashtag.publications.add(p)

        return p

    class Meta:
        ordering = None

class City(TimeStampedModel):
    """ Stores cities where we will provide fixed data
    """
    name = models.CharField(max_length=250, unique=True)
    center = models.PointField()
    zoom = models.PositiveIntegerField()


class Spot(TimeStampedModel):
    """ Stores spots within a city that we will use to retrieve locations
    """
    position = models.PointField()
    city = models.ForeignKey(City, blank=True, null=True)
    is_adhoc = models.BooleanField(blank=True, default=False)

    def update_locations(self, location_data, is_adhoc=False):
        """ Update the locations related to this spot. location_data is a structure that contains locations in
        instagram. See https://www.instagram.com/developer/endpoints/locations/#get_locations_search
        """
        for location in location_data['data']:
            logger.debug("Storing location with id %s" % location['id'])
            location_in_db = InstagramLocation.objects.filter(instagramID=location['id'])
            if location_in_db.count() == 0 or is_adhoc:
                logger.info("New instagram location found named `%s`" % location['name'])
                position = Point(location['longitude'], location['latitude'])
                new_location = InstagramLocation(name=location['name'], instagramID=location['id'],
                                                 position=position, spot=self)
                new_location.save()

    def __unicode__(self):
        if self.city is not None:
            return "City of %s (Spot %s)" % (self.city.name, self.id)
        else:
            return "Unassigned spot with id %s" % self.id


class SettingManager(models.Manager):

    def get_value(self, option):
        """ Returns the option
        """
        return Setting.objects.get(name=option).value

    def set_value(self, option, value):
        """ Returns the option
        """
        s = Setting.objects.get(name=option)
        s.value = value
        s.save()

class Setting(TimeStampedModel):
    """ Application information
    """
    name = models.CharField(max_length=256, blank=False)
    value = models.CharField(max_length=2000, blank=True)
    help = models.TextField(max_length=500, blank=True)

    objects = SettingManager()


class InstagramRequest(TimeStampedModel):
    """ Requests done to nstagram API
    """
    pass


class ExportForm(TimeStampedModel):
    """ Controlling export functions
    """
    _mt_progress, _mt_finished = range(0, 2)
    _choices_status = ((_mt_progress, 'In progress'), (_mt_finished, 'Completed'))
    status = models.CharField(max_length=1, choices=_choices_status, default=_mt_progress)
    url_file = models.CharField(max_length=500, blank=True, null=True)

    def get_absolute_url(self):
        from django.core.urlresolvers import reverse
        return reverse('api-progress-excel', args=[str(self.id)])