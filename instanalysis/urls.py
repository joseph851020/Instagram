
from django.conf.urls import url

from instanalysis import views
from instanalysis.apps.instagram import views as views_api

from django.conf import settings

urlpatterns = [
    # url(r'^project/(?P<project_id>[0-9]\d*)/$',
    #     login_required(
    #         views.ProjectView.as_view(),
    #         login_url="/login/"
    #     ),
    #     name='project_view'),
    url(r'^$', views.Home.as_view(), name='home'),
    #url(r'^adhoc-search/(?P<pk>\d+)/$', views.ADHOCSearchView.as_view(), name='adhoc_search'),

    #CSV
    url(r'^export-hashtags-categories/$', views.Csv.as_view(), name='csv-export'),
    url(r'^import-hashtags-categories/$', views.Csv.as_view(), name='csv-import'),

    # Callbacks
    url(r'^callback/instagram-api-token$', views_api.InstagramAPIToken.as_view(), name="instagram-api-token"),

    # Ajax and API calls
    url(r'^api/hashtagSearch', views.HashtagSearch.as_view(), name="api-hashtag-search"),
    url(r'^api/pivot/(?P<pk>\d+)$', views.Pivot.as_view(), name="api-pivot"),
    url(r'^api/checkProgressADHOC/(?P<pk>\d+)$', views.checkProgressADHOC.as_view(), name="api-progress"),
    url(r'^api/checkProgressExport/(?P<pk>\d+)$', views.checkProgressExportExcel.as_view(), name="api-progress-excel"),
    
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', 
            {'document_root': settings.MEDIA_ROOT})]