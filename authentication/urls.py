from django.conf.urls import url, include
from django.contrib import admin

from django.contrib.auth import views
from authentication.views import Login, Logout

urlpatterns = [
    
    url(r'^login/$', Login.as_view(), name="login" ),
    url(r'^logout/$', Logout.as_view(), name='logout'),
    url('^', include('django.contrib.auth.urls')),

    # ^login/$ [name='login']
    # ^logout/$ [name='logout']
    # ^password_change/$ [name='password_change']
    # ^password_change/done/$ [name='password_change_done']
    # ^password_reset/$ [name='password_reset']
    # ^password_reset/done/$ [name='password_reset_done']
    # ^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$ [name='password_reset_confirm']
    # ^reset/done/$ [name='password_reset_complete']
]
