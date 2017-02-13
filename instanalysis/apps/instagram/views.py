import logging

from django.views.generic import View
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from instanalysis.models import Setting
from .api import get_access_token

logger = logging.getLogger(__name__)

class InstagramAPIToken(View):

    def get(self, request):
        """ Returning from instagram callback
        """
        code = request.GET.get("code")
        # Storing new code
        s = Setting.objects.get(name="instagram_code")
        s.value = code
        s.save()
        logger.debug("Code stored in database, generating access_token")
        get_access_token()
        return redirect(reverse("admin:instanalysis_setting_changelist"))
