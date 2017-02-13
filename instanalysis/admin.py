from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import humanize

from instanalysis import models
from instanalysis.utils import naturaltime


class UserManager(UserAdmin):
    list_display = ('email',)


class SettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'value_short', 'help')

    def value_short(self, instance):
        return "%s..." % instance.value[0:20] if len(instance.value) > 20 else instance.value


class CategoriesAdmin(admin.ModelAdmin):
    list_display = ('label',)
    fields = ('label',)


class HashtagsAdmin(admin.ModelAdmin):
    list_display = ('label',)
    fields = ('label', 'publications', 'categories')
    readonly_fields = ('publications',)


class SpotInline(admin.StackedInline):
    model = models.Spot
    readonly_fields = ('created', 'modified',)
    ordering = ('id',)
    extra = 1


class CityManager(admin.ModelAdmin):
    list_display = ('id', 'name', 'last_date', 'last_downloaded_date')
    readonly_fields = ('created', 'modified',)
    inlines = (SpotInline,)

    def last_date(self, instance):

        return models.InstagramLocation.objects.filter(spot__city=instance).order_by('updated_at').first().updated_at

    def last_downloaded_date(self, instance):

        d = models.Publication.objects.filter(location__spot__city=instance).order_by('-publication_date').first().created
        return naturaltime(d)




class InstagramLocationManager(admin.ModelAdmin):
    list_display = ('id', 'name', 'updated_at', 'city_name')
    list_filter = ('spot__city__name',)
    readonly_fields = ('created', 'modified')
    ordering = ('-updated_at', )

    def city_name(self, instance):
        if instance.spot.city is not None:
            return instance.spot.city.name
        else:
            return "---"


class PublicationModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'instagram_url', 'publication_date', 'created', 'hashtags', 'city_name')
    list_filter = ('location__spot__city__name',)
    readonly_fields = ('created', 'modified', 'hashtags', 'location', 'author')
    ordering = ('-publication_date',)
    
    def hashtags(self, instance):
        return ", ".join(["#%s" % h.label for h in instance.hashtag_set.all()])

    def city_name(self, instance):
        if instance.location is not None and instance.location.spot.city is not None:
            return instance.location.spot.city.name
        else:
            return "--"


class InstagramUserModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'instagramID', 'created', 'num_publications')
    readonly_fields = ('username', 'instagramID')
    ordering = ('created',)

    def num_publications(self, instance):
        return instance.publication_set.count()


class SettingManager(admin.ModelAdmin):
    list_display = ('id', 'name', 'value')
    readonly_fields = ('created', 'modified',)


class ADHOCSearchManager(admin.ModelAdmin):
    list_display = ('id', 'statusa', 'position', 'radius', 'start_date', 'end_date', 'month', 'weekday', 'slotrange',
                    'get_hashtags', 'get_categories')
    readonly_fields = ('created', 'modified', 'hashtags', )

    def get_hashtags(self, instance):
        return ", ".join([h.label for h in instance.hashtags.all()])

    def get_categories(self, instance):
        return ", ".join([c.label for c in instance.categories.all()])

    def statusa(self, instance):
        return instance.status

admin.site.register(models.Setting, SettingManager)
admin.site.register(models.Hashtag, HashtagsAdmin)
admin.site.register(models.Category, CategoriesAdmin)
admin.site.register(models.City, CityManager)
admin.site.register(models.Publication, PublicationModelAdmin)
admin.site.register(models.PublicationADHOC, PublicationModelAdmin)
admin.site.register(models.InstagramUser, InstagramUserModelAdmin)
admin.site.register(models.InstagramLocation, InstagramLocationManager)
admin.site.register(models.ADHOCSearch, ADHOCSearchManager)
admin.site.register(models.ExportForm)
