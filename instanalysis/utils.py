import logging
import string
import random
from datetime import date, timedelta, datetime
from django.utils import timezone
from django.template import defaultfilters
from django.utils.timezone import is_aware, utc
from django.utils.translation import pgettext, ugettext as _, ungettext
from pytz.exceptions import AmbiguousTimeError

logger = logging.getLogger(__name__)


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def _get_init_datetime_location():
    """ Returns a random instant in the past to set the update_at value
    """
    from instanalysis.models import Setting
    now = timezone.now()
    time_last_update = now - timedelta(seconds=60)
    return time_last_update

def created_from_timestamp_instagram(created_time):
    """ converts to timestamp
    """
    try:
        created_timestamp = datetime.fromtimestamp(int(created_time))
        created_timestamp = timezone.make_aware(created_timestamp)
    except ValueError, TypeError:
        created_timestamp = datetime(2016, 01, 01)
        created_timestamp = timezone.make_aware(created_timestamp)
        logger.error("Created_time failed. USing 01/01/2016 instead")
    except AmbiguousTimeError:
        created_timestamp = datetime(2016, 01, 01)
        created_timestamp = timezone.make_aware(created_timestamp)
    return created_timestamp


def naturaltime(value):
    """
    For date and time values shows how many seconds, minutes or hours ago
    compared to current timestamp returns representing string.
    """
    if not isinstance(value, date):  # datetime is a subclass of date
        return value

    now = datetime.now(utc if is_aware(value) else None)
    if value < now:
        delta = now - value
        if delta.days != 0:
            return pgettext(
                'naturaltime', '%(delta)s ago'
            ) % {'delta': defaultfilters.timesince(value, now)}
        elif delta.seconds == 0:
            return _('now')
        elif delta.seconds < 60:
            return ungettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a second ago', '%(count)s seconds ago', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds // 60 < 60:
            count = delta.seconds // 60
            return ungettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a minute ago', '%(count)s minutes ago', count
            ) % {'count': count}
        else:
            count = delta.seconds // 60 // 60
            return ungettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'an hour ago', '%(count)s hours ago', count
            ) % {'count': count}
    else:
        delta = value - now
        if delta.days != 0:
            return pgettext(
                'naturaltime', '%(delta)s from now'
            ) % {'delta': defaultfilters.timeuntil(value, now)}
        elif delta.seconds == 0:
            return _('now')
        elif delta.seconds < 60:
            return ungettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a second from now', '%(count)s seconds from now', delta.seconds
            ) % {'count': delta.seconds}
        elif delta.seconds // 60 < 60:
            count = delta.seconds // 60
            return ungettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'a minute from now', '%(count)s minutes from now', count
            ) % {'count': count}
        else:
            count = delta.seconds // 60 // 60
            return ungettext(
                # Translators: please keep a non-breaking space (U+00A0)
                # between count and time unit.
                'an hour from now', '%(count)s hours from now', count
            ) % {'count': count}