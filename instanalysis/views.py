import logging
import csv
import json
import os
import time
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils.translation import ugettext as _
from django.views.generic import View
from django.template.response import TemplateResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.gis.geos import Point
from instanalysis.tasks import process_csv_file, process_adhoc_search, export_to_excel

from django.db.models import F
from .models import Category, Hashtag, City, Publication, Spot, ADHOCSearch, ExportForm
from .forms import PivotEditForm
from .apps.map.views import MapView


logger = logging.getLogger(__name__)


class Home(MapView):
    template_name = "base.html"

    def get(self, request):
        """ Landing page
        """
        context = dict()
        if request.GET.get('latitude', '') != '' and request.GET.get('location', '') != '':
            url = reverse('home')
            msg = _("Select only a city or a latitude and longitude")
            return HttpResponseRedirect("%s?tyT=warn&msT=%s&autohide=4000" % (url, msg))
        mapInfo, publications, hashtags = self.getMapInfo(request)
        if (request.GET.get('latitude', '') == '' and request.GET.get('location', '') == '') \
            or request.GET.get('location', '') != '' or request.GET.get('showresults') == "1":

            context['cities'] = City.objects.all()

            if request.GET.get('export', 0) == "1":
                # When exporting, we will generate the file offline
                # And retrieve the file via ajax
                # Each record weights 70 bytes. We only let exporting files smaller than 15 Mb
                # 15Mb = 220000 publications
                if publications.count() > 220000:
                    msg = _("You cannot export more than 220k publications.")
                    ok = False
                else:
                    ok = True
                    msg = ""
                ef = ExportForm()
                ef.save()
                publications = [p['id'] for p in publications.values('id')]
                hashtags = [h['id'] for h in hashtags.values('id')]
                data = {
                    "publications": None if not publications else publications,
                    "hashtags": None if not hashtags else hashtags,
                    "id": ef.id
                }
                export_to_excel.delay(data)
                msg = "Generating excel file. Please wait..."
                return JsonResponse({"ok": ok, "msg": msg, "ef_id": ef.id, "url": ef.get_absolute_url()})

                #output_file = Publication.objects.export_to_excel(queryset, hashtags)
                # #file_copy = output_file.seek(0, os.SEEK_END)
                # size_bytes = output_file.tell()
                # size_mb = float(size_bytes) / (1024*1024)
                #response = HttpResponse(output_file.read(),
                #                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                #response['Content-Disposition'] = "attachment; filename=results-posteranalytics.xlsx"
                #return response
            else:
                context['mapInfo'] = mapInfo
                context['hashtags'] = hashtags
                context['hashtags_top_hundred'] = hashtags[:100]  #slicing top hundred
                context['mapInfo_json'] = json.dumps(context['mapInfo'], cls=DjangoJSONEncoder)
                return TemplateResponse(request, self.template_name, context)
        else: # adhoc search
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

            position = Point(float(request.GET.get('longitude')), float(request.GET.get('latitude')))
            hashtags = Hashtag.objects.filter(label__in=request.GET.getlist('hashtag', ''))
            categories = Category.objects.filter(label__in=request.GET.getlist('category', ''))

            start_date = datetime.strptime(request.GET.get('start_date'), "%d/%m/%Y")
            end_date = datetime.strptime(request.GET.get('end_date'), "%d/%m/%Y")
            adhoc_search = ADHOCSearch(status=ADHOCSearch._mt_progress,
                                       position=position,
                                       radius=int(750 if request.GET.get('radius', '') == '' else request.GET.get('radius')),
                                       start_date=start_date,
                                       end_date=end_date,
                                       month=month,
                                       weekday=day,
                                       slotrange=slot,
                                       query_url=request.build_absolute_uri())
            url = request.build_absolute_uri()
            url = url.replace("&radius=&", "&radius=750&")
            siblings = ADHOCSearch.objects.filter(query_url=url,
                                                  status=ADHOCSearch._mt_finished)
            if siblings.count() > 0 and end_date.date() == datetime.today().date():
                # When a query already exists, we use its data!!!
                sibling = siblings.first()
                url = sibling.query_url
                if "showresults=" in url:
                    url = url.replace("showresults=", "showresults=1")
                else:
                    url = "%s&showresults=1" % url
                if "adhoc_id=" in url:
                    url = url.replace("adhoc_id=", "adhoc_id=%s" % sibling.id)
                else:
                    url = "%s&adhoc_id=%s" % (url, sibling.id)
                return HttpResponseRedirect(url)

            adhoc_search.save()
            for el in hashtags:
                adhoc_search.hashtags.add(el)
            for el in categories:
                adhoc_search.categories.add(el)
            # Scheduling on celery
            process_adhoc_search.delay(adhoc_search.pk)

            logger.debug("Informing user to wait to finish adhoc search with id `%s`" % adhoc_search.id)
            # ADHOC Search, we tell the user to wait
            context['loadingADHOC'] = True
            context['adhoc_search_id'] = adhoc_search.id
            context['mapInfo'] = mapInfo
            context['hashtags'] = hashtags
            context['mapInfo_json'] = json.dumps([context['mapInfo']], cls=DjangoJSONEncoder)
            return TemplateResponse(request, self.template_name, context)



class Csv(View):
    """
    Class to export/import hashtag-category csv
    """
       
    def post(self, request):
        #Read the csv file
        if request.FILES and 'file' in request.FILES:
            filename_tmp = "upload_%s" % datetime.now().strftime('%s')
            filepath_local = os.path.join('/tmp', filename_tmp)
            with open(filepath_local, 'wb+') as destination:
                for chunk in request.FILES['file'].chunks():
                    destination.write(chunk)



            with open(filepath_local, "r") as f:
                lines = f.readlines()

            fileparam = lines
            if len(fileparam) > 0:
                #Read header categories
                categories = fileparam[0].split(",") # asume that ; is the delimiter
                if len(categories) < 2:
                    url = reverse('home')
                    msg = _("There are no categories in the file.")
                    return HttpResponseRedirect("%s?tyT=ko&msT=%s&autohide=4000" % (url, msg))
                    #return HttpResponse(status=403) #No categories in the file

            #return HttpResponse(status=201) #Created
            process_csv_file.delay(filepath_local)

            url = reverse('home')
            msg = _("The system is updating the hashtags with the categories")
            return HttpResponseRedirect("%s?tyT=ok&msT=%s&autohide=4000" % (url, msg))

                #return HttpResponse(status=403) #Bad request -> no data
        url = reverse('home')
        msg = _("No file to upload.")
        return HttpResponseRedirect("%s?tyT=ko&msT=%s&autohide=4000" % (url, msg))



class HashtagSearch(View):
    """ HashtagSearch view
    """
    def get(self, request, *args, **kwargs):
        """ Called when user asks for data search for hashtags
        """
        query = request.GET.get('q')
        items = Hashtag.objects.filter(label__startswith=query)
        items = [{"id": a.label.replace('\r\n', '').replace('\r', '').replace('\n', ''),
                  "text": "#%s" % a.label.replace('\r\n', '').replace('\r', '').replace('\n', '')} for a in items]
        return JsonResponse({'items': items, 'total_count': list(items)})


class Pivot(View):

    def post(self, request, pk, *args, **kwargs):
        """ Updading a pivot data by latitude and longitude
        """

        logger.debug(pk)
        forms = PivotEditForm(request.POST)
        if forms.is_valid():
            try:
                pivot = Spot.objects.get(id=pk)
                pnt = Point(float(request.POST.get('lng')), float(request.POST.get('lat')))
                pivot.position = pnt
                pivot.save()
            except Spot.DoesNotExist:
                return JsonResponse({"ok": False})
            return JsonResponse({"ok": True})
        else:
            return JsonResponse({"ok": False})


class checkProgressADHOC(View):
    """ Ajax, checking progress on adhoc queries
    """
    def get(self, request, pk, *agrs, **kwargs):
        adhoc_search = get_object_or_404(ADHOCSearch, id=pk)
        return JsonResponse({"ok": True,
                             "finished": int(adhoc_search.status) == ADHOCSearch._mt_finished,
                             "error": int(adhoc_search.status) == ADHOCSearch._mt_error,
                             "url": adhoc_search.query_url})


class checkProgressExportExcel(View):
    """ Ajax, checking progress on exporting queries to excel file
    """
    def get(self, request, pk, *agrs, **kwargs):
        export_form = get_object_or_404(ExportForm, id=pk)
        return JsonResponse({"ok": True, "finished": int(export_form.status) == ExportForm._mt_finished,
                             "url_file": export_form.url_file})