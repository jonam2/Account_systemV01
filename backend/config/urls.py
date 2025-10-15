"""Main URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include('api.v1.urls')),

    path('api/v1/contacts/', include('api.v1.routes.contact_routes')),

    path('api/v1/warehouses/', include('api.v1.routes.warehouse_routes'))
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)