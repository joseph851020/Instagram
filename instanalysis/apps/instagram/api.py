import logging
import requests
import json
import time
from datetime import datetime

from django.conf import settings
from django.core.urlresolvers import reverse

logger = logging.getLogger(__name__)

class APIGramException(Exception):
    pass

def get_access_token():
    """ Retrieves an OAUTH access token for Instagram
    """
    from instanalysis.models import Setting
    from instanalysis.tasks import calculate_api_quotas

    logger.info("Asking for a OAuth token to instagram")
    code = Setting.objects.get_value('instagram_code')
    api = InstagramAPI()
    calculate_api_quotas.delay()
    payload = {
        'client_secret': settings.INSTAGRAM_SECRET_ID,
        'grant_type': 'authorization_code',
        'scope': 'public_content',
        'redirect_uri': "http://%s%s" % (settings.MAIN_DOMAIN, reverse('instagram-api-token')),
        'code': code,
        'client_id': settings.INSTAGRAM_CLIENT_ID
    }
    data = api._post_to_api("https://api.instagram.com/oauth/access_token", payload)
    username = data.get("user").get("username")
    access_token = data.get('access_token')
    logger.info("Access token obtained for user %s" % username)
    access_token_setting = Setting.objects.get(name='access_token')
    access_token_setting.value = access_token
    access_token_setting.save()


class InstagramAPI(object):

    def _get_from_api(self, url, retry=0):
        """ Queries to the API url provided by parameter and returns a JSON object with the result
        """
        from instanalysis.models import InstagramRequest, Setting
        access_token = Setting.objects.get_value('access_token')
        url = "%s&access_token=%s" % (url, access_token)

        logger.info("Querying API. URL is `%s`" % url)
        response = requests.get(url)
        if (response.status_code == 503 and retry < 3):
            time.sleep(10)
            data = self._get_from_api(url, retry=retry+1)
        elif (response.status_code == 503 and retry >= 3):
            # Could not retrieve after many attempts
            raise APIGramException(response.content)
        elif (response.status_code != 200):
            logger.error("Unexpected response from Instagram API. Status code is `%s`" % response.status_code)
            logger.error("Message is: %s" % response.content)
            raise APIGramException(response.content)
        try:
            response_data = json.loads(response.content)
        except ValueError:
            raise APIGramException("Data could not be parsed to json: %s" % response.content)
        InstagramRequest().save()
        return response_data

    def _post_to_api(self, url, data):
        """ Posts data to the instagram API
        """
        logger.debug("Querying API. URL is `%s`, data is `%s`" % (url, data))
        r = requests.post(url, data=data)
        InstagramRequest().save()
        if r.status_code != 200:
            logger.error("Access token not given. Response is: %s" % r.content)
            raise Exception("Access token could not be given: %s" % r.content)
        else:
            return json.loads(r.content)

    def getPostsByLocation(self, lat, lng, radius, start_date, end_date):
        """ Obtains all posts by location from Instagram. We obtain the latest
        2000 posts at the most if the parameter is not specified.
        """
        logger.debug("Obtaining publications by location %s, %s" % (lat, lng))

        url = "https://api.instagram.com/v1/media/search?lat=%s"\
              "&lng=%s&distance=%s" % (lat, lng, radius)
        return self._get_from_api(url)

    def getLocations(self, lat, lng, radius=750):
        """ Obtains a list of locations around the point passed by parameter.
        Example:
        >>> api.getLocations(42.2, 2.12)
        [...]
        """
        logger.debug("Obtaining locations nearby %s, %s" % (lat, lng))
        url = "https://api.instagram.com/v1/locations/search?lat=%s"\
              "&lng=%s&distance=%s" % (lat, lng, radius)
        return self._get_from_api(url)

    def getLatestPostsInfo(self, location_id, min_id=None, is_adhoc=False, start_date=None):
        """ Obtains a list of media submitted from the location passed by parameter.
        When min_id is provided, the function returns ALL publications created after the publication's id defined
        by min_id. When this parameter is not provided, only the latest results are provided. However, if the
        result is adhoc, we obtain all results and stop when we get posts after start_date
        """
        from instanalysis.utils import created_from_timestamp_instagram

        logger.debug("Obtaining media from Instagram's location `%s`, min_id is `%s`" % (location_id, min_id))
        start_date_d = datetime(start_date.year, start_date.month, start_date.day) if start_date else None
        # We check if this is the first retirval of data for this location
        # Id that is the case, we do not do more queries as instagram API returns the 
        # URL for the next page. We would be asking for all past media for this event
        is_first_query = min_id is None or min_id == ''
        min_id_parameter = "min_id=%s" % min_id if min_id is not None else "min_id="
        url = "https://api.instagram.com/v1/locations/%s/media/recent?count=200&%s" % (location_id, min_id_parameter)
        media = []
        condition = True
        pages = 10
        while condition:
            try:
                data = self._get_from_api(url)
            except APIGramException:
                break
            # We only use pagination on subsequent calls on certain situation.
            try:
                data['data']
            except KeyError:
                break
            if len(data['data']) > 0:
                date_first_post = created_from_timestamp_instagram(data['data'][0]['created_time'])
                date_first_post = datetime(date_first_post.year, date_first_post.month, date_first_post.day)
            else:
                date_first_post = datetime(2000, 1, 1)
            is_city_search_and_is_page_under_ten = (pages > 0)
            there_is_pagination = 'pagination' in data and bool(data['pagination'])
            is_within_range = data['data'] is not None and start_date is not None and date_first_post >= start_date_d
            logger.info("First date of posting is `%s`. Start date is: `%s`" % (date_first_post, start_date))
            logger.info("Page number is aboce 0 %s" % is_city_search_and_is_page_under_ten)
            logger.info("Pagination? %s" % there_is_pagination)
            logger.info("Limit on date for adhoc %s" % is_within_range)
            if is_adhoc:
                condition = there_is_pagination and is_within_range
            else:
                condition = there_is_pagination and is_city_search_and_is_page_under_ten
            logger.debug("Condition is `%s`" % condition)
            if condition:
                url = data['pagination']['next_url']
            if 'data' not in data:
                logger.warning("No data retrieved from instagram. Returned message is %s" %
                               data['meta']['error_message'])
            else:
                media += data['data']
            pages = pages - 1

        new_min_id = media[0]['id'] if len(media) > 0 else None

        return (media, new_min_id)
