from django.conf.urls import url, include
from django.contrib import admin
from django.conf import settings
from django.views.generic import RedirectView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    url(r'^', include('instanalysis.urls')),
    url(r'^', include('authentication.urls')),
    url(r'^admin/', admin.site.urls),
    #url(r'^$', RedirectView.as_view(pattern_name='login')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
