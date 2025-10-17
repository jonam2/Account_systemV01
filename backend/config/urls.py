"""Main URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

"""API v1 URL Configuration"""

urlpatterns = [
     # Admin panel
    path('admin/', admin.site.urls),
    # Authentication routes
    path('auth/', include('api.v1.routes.auth_routes')),
    
    # User management routes
    path('users/', include('api.v1.routes.user_routes')),
    
    # Product management routes
    path('products/', include('api.v1.routes.product_routes')),
    
    # Contact management routes (customers/suppliers)
    path('contacts/', include('api.v1.routes.contact_routes')),
    
    # Warehouse & inventory routes
    path('warehouses/', include('api.v1.routes.warehouse_routes')),
    
    # Invoice routes (sales/purchase)
    path('invoices/', include('api.v1.routes.invoice_routes')),
    
    # Order routes (sales/purchase)
    path('orders/', include('api.v1.routes.order_routes')),
    
    # Production routes (BOM, assembly, disassembly)
    path('production/', include('api.v1.routes.production_routes')),
]


# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# urlpatterns = [
#     # Admin panel
#     path('admin/', admin.site.urls),
    
#     # API v1
#     path('api/v1/', include('api.v1.urls')),

#     path('api/v1/contacts/', include('api.v1.routes.contact_routes')),

#     path('api/v1/warehouses/', include('api.v1.routes.warehouse_routes'))

# ]

# # Serve media files in development
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)