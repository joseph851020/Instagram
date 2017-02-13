import logging

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.template.response import TemplateResponse

from authentication import forms as auth_forms

logger = logging.getLogger("yoinable")


class Login(View):
    template_name = "registration/login.html"

    def get(self, request, *args, **kwargs):
        context_data = dict()
        context_data["form"] = auth_forms.LoginForm()
        return TemplateResponse(request, self.template_name, context_data)

    def post(self, request, *args, **kwargs):
        """ User is loggin in
        """
        username = request.POST['username']
        password = request.POST['password']
        context_data = dict()
        form = auth_forms.LoginForm(request.POST)

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                # Redirect to a success page.
                return redirect(reverse("project_list"))
            else:
                # Return a 'disabled account' error message
                logger.debug("Account {} is disabled".format(user))
                form.error_msg = _("Account is disabled")
        else:
            # Return an 'invalid login' error message.
            logger.debug("Invalid login for username {}".format(username))
            form.error_msg = _("Invalid username or password")
        context_data['form'] = form
        return TemplateResponse(request, self.template_name, context_data)


class Logout(View):

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse("go_hireluther"))
