import logging

from datetime import datetime, timedelta
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.views.generic import View
from django.db import connection

from instanalysis import api
from instanalysis.models import City, Publication, Hashtag, InstagramUser
from instanalysis.models import Setting, InstagramLocation, Category, PublicationADHOC

logger = logging.getLogger(__name__)

# Cursor for the database
cursor = connection.cursor()

class MapView(View):
    """ A class generic view to be used on the map view.
    """

    def getMapInfo(self, request, adhoc_search=None):
        """ Returns the map information to be used in the view. When no queries are performed, we just
        return the information in order to center the map on Spain, without markers and any sourrinding stuff.
        We return the appropiate center, markers and pivots for successfull queries
        adhoc_search is set on the response of an adhoc search.
        """
        using_filters = False
        location = request.GET.get('location')
        showpivots = request.GET.get('showpivots', 0) == "1"
        showlocations = request.GET.get('showlocations', "1") == "1"
        month = request.GET.get('month')
        day = request.GET.get('day')
        slot = request.GET.get('slot')
        try:
            month = int(month) if month is not None else None
        except ValueError:
            month = None
        try:
            day = int(day) if day is not None else None
        except ValueError:
            day = None
        try:
            day = int(day) if day is not None else None
        except ValueError:
            day = None
        try:
            slot = int(slot) if slot is not None else None
        except ValueError:
            slot = None
        is_adhoc = request.GET.get('latitude', '') != ''
        radius_pivots = 750
        if is_adhoc and request.GET.get('adhoc_id', '') != '':
            # Getting results of an adhoc_search
            adhoc_id = request.GET.get('adhoc_id')  # here!!! result
            map_center = {"lat": float(request.GET.get('latitude')), "lng": float(request.GET.get('longitude'))}
            zoom = 12
            pivots = [map_center]
            showpivots = True
            radius_pivots = int(750 if request.GET.get('radius', '') == '' else request.GET.get('radius'))
            publications = Publication.objects.filter(adhocsearch__id=int(adhoc_id))
            locations_q = InstagramLocation.objects.filter(id__in=publications.values('location_id'))
        elif location is None:
            # Default query, initial view
            map_center = {"lat": 40.421363, "lng": -3.727398}
            zoom = 6
            pivots = []
            publications = Publication.objects.none()
            locations_q = InstagramLocation.objects.none()
        else:
            # Searching by a city
            city = get_object_or_404(City, name=location)
            map_center = {"lat": city.center.coords[1], "lng": city.center.coords[0]}
            zoom = city.zoom
            if showpivots:
                pivots = [{"id": l.id,
                           "position": {"lat": l.position.y, "lng": l.position.x}
                           } for l in city.spot_set.all()]
            else:
                pivots = []
            publications = Publication.objects.filter(location__spot__city__name=location)
            locations_q = InstagramLocation.objects.filter(id__in=publications.values('location_id'))
        # Before filtering, we get the oldest location without updating
        last_location_to_update = publications.order_by('location__updated_at').first()
        if last_location_to_update is not None and last_location_to_update.location is not None:
            oldest_location = last_location_to_update.location.updated_at.strftime("%d/%m/%Y %H:%M")
        else:
            oldest_location = None

        # Filters
        if request.GET.get('start_date', '') != '':
            logger.debug("Filtering by start_date `%s`" % request.GET.get('start_date', ''))
            start_date = datetime.strptime(request.GET.get('start_date'), "%d/%m/%Y")
            publications = publications.filter(publication_date__gte=start_date)

        if request.GET.get('end_date', '') != '':
            logger.debug("Filtering by end_date `%s`" % request.GET.get('end_date', ''))
            end_date = datetime.strptime(request.GET.get('end_date'), "%d/%m/%Y")
            next_day = end_date + timedelta(hours=24)
            # adding 24 hours 
            publications = publications.filter(publication_date__lte=next_day)
        if request.GET.getlist('hashtag', '') != '':
            logger.debug("Filtering by hashtag `%s`" % request.GET.get('hashtag', ''))
            using_filters = True
            for el in request.GET.getlist('hashtag', ''):
                publications = publications.filter(hashtag__label=el)
        if request.GET.get('category', '') != '':
            logger.debug("Filtering by category `%s`" % request.GET.get('category', ''))
            using_filters = True
            logger.debug("Publications before filtering: %s" % publications.count())
            publications = publications.filter(hashtag__categories__label__in=request.GET.getlist('category'))
            logger.debug("Publications after filtering: %s" % publications.count())
        if month is not None:
            logger.debug("Filtering by month `%s`" % month)
            using_filters = True
            logger.debug("Filtering publications by date range: %s" % month)
            publications = publications.filter(publication_date__month__gte= month,
                                               publication_date__month__lte= month)
        if day is not None:
            logger.debug("Filtering by day `%s`" % day)
            using_filters = True
            logger.debug("Filtering publications by day range: %s" % day)
            publications = publications.filter(publication_date__week_day= day)
        if slot is not None:
            logger.debug("Filtering by slot `%s`" % slot)
            using_filters = True
            hours_range = ",".join([str(l + ((slot - 1) * 6)) for l in range(0, 6)])
            logger.debug("Filtering publications by slot range: %s" % hours_range)
            publications = publications.extra(where=['extract(hour from publication_date) in (%s)' % hours_range])
        using_filters = False
        likes = publications.aggregate(total_likes=Sum('likes')).get('total_likes', 0)
        if likes is None:
            likes = 0
        elif likes > 1000 * 1000:
            likes = "%sk" % (likes/1000)

        # This query requires a lot of operations: GROUP BY and COUNT.
        # This 
        # cursor.execute("set work_mem = '250MB';")
        # cursor.execute('SHOW work_mem')
        hashtags = publications.values('hashtag__label').annotate(count=Count('hashtag')).order_by('-count')[0:100]
        data = ({
            "last_location_update": oldest_location,
            "zoom": zoom,
            "center": map_center,
            "locations": [{'lat': l['position'].y, 'lng': l['position'].x} for l in locations_q.values('position')],
            "pivots": pivots,
            "showpivots": showpivots,
            "showlocations": showlocations,
            "num_publications": publications.count(),
            "num_authors": publications.values('author').annotate(count=Count('author')).count(),
            # HERE!!!! Change the author to display the number of authors in this query!!!!
            "queries_api": Setting.objects.get_value('instagram_hourly'),
            "total_posts": Publication.objects.filter(location__spot__city__name=location).count(),
            "num_hashtags": Hashtag.objects.filter(publications__id__in=publications.values('id')).count(),
            "likes": 0 if likes is None else likes,
            "all_categories": list(Category.objects.all().values('label')),
            "using_filters": using_filters,  # Determining if filters are used,
            "radius_pivots": radius_pivots,
            "selected_categories": request.GET.getlist('category'),
            "selected_hashtags": request.GET.getlist('hashtag')
        }, publications, hashtags)
        return data
        # Other data
