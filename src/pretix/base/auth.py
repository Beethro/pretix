import re
import requests
import uuid
import time

from collections import OrderedDict
from importlib import import_module

from django import forms
from django.conf import settings
from django.contrib.auth import (
    authenticate, login as auth_login, logout as auth_logout,
)
from django.utils.translation import gettext_lazy as _

from pretix.base.models import User


def get_auth_backends():
    backends = {}
    for b in settings.PRETIX_AUTH_BACKENDS:
        mod, name = b.rsplit('.', 1)
        b = getattr(import_module(mod), name)()
        backends[b.identifier] = b
    return backends


class BaseAuthBackend:
    """
    This base class defines the interface that needs to be implemented by every class that supplies
    an authentication method to pretix. Please note that pretix authentication backends are different
    from plain Django authentication backends! Be sure to read the documentation chapter on authentication
    backends before you implement one.
    """

    @property
    def identifier(self):
        """
        A short and unique identifier for this authentication backend.
        This should only contain lowercase letters and in most cases will
        be the same as your package name.
        """
        raise NotImplementedError()

    @property
    def verbose_name(self):
        """
        A human-readable name of this authentication backend.
        """
        raise NotImplementedError()

    @property
    def visible(self):
        """
        Whether or not this backend can be selected by users actively. Set this to ``False``
        if you only implement ``request_authenticate``.
        """
        return True

    @property
    def login_form_fields(self) -> dict:
        """
        This property may return form fields that the user needs to fill in to log in.
        """
        return {}

    def form_authenticate(self, request, form_data):
        """
        This method will be called after the user filled in the login form. ``request`` will contain
        the current request and ``form_data`` the input for the form fields defined in ``login_form_fields``.
        You are expected to either return a ``User`` object (if login was successful) or ``None``.
        """
        return

    def request_authenticate(self, request):
        """
        This method will be called when the user opens the login form. If the user already has a valid session
        according to your login mechanism, for example a cookie set by a different system or HTTP header set by a
        reverse proxy, you can directly return a ``User`` object that will be logged in.

        ``request`` will contain the current request.
        You are expected to either return a ``User`` object (if login was successful) or ``None``.
        """
        return

    def authentication_url(self, request):
        """
        This method will be called to populate the URL for your authentication method's tab on the login page.
        For example, if your method works through OAuth, you could return the URL of the OAuth authorization URL the
        user needs to visit.

        If you return ``None`` (the default), the link will point to a page that shows the form defined by
        ``login_form_fields``.
        """
        return

    def get_next_url(self, request):
        """
        This method will be called after a successful login to determine the next URL. Pretix in general uses the
        ``'next'`` query parameter. However, external authentication methods could use custom attributes with hardcoded
        names for security purposes. For example, OAuth uses ``'state'`` for keeping track of application state.
        """
        if "next" in request.GET:
            return request.GET.get("next")
        return None


class NativeAuthBackend(BaseAuthBackend):
    identifier = 'native'
    verbose_name = _('Admin')
    order = 3

    @property
    def login_form_fields(self) -> dict:
        """
        This property may return form fields that the user needs to fill in
        to log in.
        """
        d = OrderedDict([
            ('email', forms.EmailField(label=_("E-mail"), max_length=254,
                                       widget=forms.EmailInput(attrs={'autofocus': 'autofocus'}))),
            ('password', forms.CharField(label=_("Password"), widget=forms.PasswordInput)),
        ])
        return d

    def form_authenticate(self, request, form_data):
        u = authenticate(request=request, email=form_data['email'].lower(), password=form_data['password'])
        if u and u.auth_backend == self.identifier:
            return u


# authentication for external users not covered by sso
# create user in database with random password to not break things
class AlmaAuthBackend(BaseAuthBackend):
    identifier = 'alma'
    verbose_name = _('external library users')
    order = 2

    @property
    def login_form_fields(self) -> dict:
        """
        This property may return form fields that the user needs to fill in
        to log in.
        """
        d = OrderedDict([
            ('barcode', forms.CharField(label=_("barcode / TUcard-Id"), max_length=254,
                                       widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))),
            ('password', forms.CharField(label=_("Password"), widget=forms.PasswordInput)),
        ])
        return d

    def form_authenticate(self, request, form_data):
        url = settings.TUW_ALMA_EXTERNAL_URL
        params = {
            "barcode" : form_data['barcode'],
            "verification" : form_data['password'],
        }
        r = requests.get(url, params=params)
        if (r.status_code == 200):
            match = re.search('<body>(.+)</body>',r.text)
            if match:
                pairs = match[1].split(":")
                d = { }
                for p in pairs:
                    key, val = p.split('=')
                    d[key] = val

                mail = d['mail']
                users = User.objects.filter(email=mail)
                if not users:
                    user = User.objects.create_user(
                        d['mail'], uuid.uuid4(),
                        fullname=d['displayName'],
                        locale=request.LANGUAGE_CODE,
                        timezone=request.timezone if hasattr(request, 'timezone') else settings.TIME_ZONE,
                        auth_backend=self.identifier,
                    )
                    user.log_action('pretix.control.auth.user.created', user=user)
                else:
                    user=users[0]
                
                auth_login(request, user)
                request.session['pretix_auth_login_time'] = int(time.time())
                request.session['pretix_auth_long_session'] = (
                    settings.PRETIX_LONG_SESSIONS and form_data.cleaned_data.get('keep_logged_in', False)
                )  
               
                return user

class SSOAuthBackend(BaseAuthBackend):
    identifier = 'sso'
    verbose_name = _('single sign on')
    order = 1

    def authentication_url(self, request):
        return "https://some.url"


   