from django.conf import settings
from django.conf.urls.static import static as django_static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls, name='admin'),
    path('', include('bidpazari.core.urls')),
]

if settings.DEBUG:
    # In production environments, /media/ should be hosted by nginx
    urlpatterns += django_static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
