"""API v1 URL configuration"""
from django.urls import path, include

urlpatterns = [
    # Authentication
    path('auth/', include('api.v1.routes.auth_routes')),
    
    # Users
    path('users/', include('api.v1.routes.user_routes')),
    
    # Products
    path('products/', include('api.v1.routes.product_routes')),
    
    # Contacts
    path('contacts/', include('api.v1.routes.contact_routes')),
    
     # warehouses
    path('warehouses/', include('api.v1.routes.warehouse_routes')),

    # invoices
    path('invoices/', include('api.v1.routes.invoice_routes')),
    
    path('orders/', include('api.v1.routes.order_routes')),
    
    path('production/', include('api.v1.routes.production_routes')),
    # Future modules will be added here:
  
    # path('vouchers/', include('api.v1.routes.voucher_routes')),
    # path('reports/', include('api.v1.routes.report_routes')),
    # path('dashboard/', include('api.v1.routes.dashboard_routes')),
]
