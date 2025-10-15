"""
Contact Routes - URL Configuration
Path: backend/api/v1/routes/contact_routes.py
"""

from django.urls import path
from layers.controllers import contact_controller

urlpatterns = [
    # List and create
    path('', contact_controller.list_contacts, name='contact-list'),
    path('create/', contact_controller.create_contact, name='contact-create'),
    
    # Customers and suppliers
    path('customers/', contact_controller.list_customers, name='contact-customers'),
    path('suppliers/', contact_controller.list_suppliers, name='contact-suppliers'),
    
    # Statistics
    path('stats/', contact_controller.contact_statistics, name='contact-stats'),
    
    # Detail operations
    path('<int:contact_id>/', contact_controller.get_contact, name='contact-detail'),
    path('<int:contact_id>/update/', contact_controller.update_contact, name='contact-update'),
    path('<int:contact_id>/delete/', contact_controller.delete_contact, name='contact-delete'),
    
    # Balance operations
    path('<int:contact_id>/balance/', contact_controller.update_balance, name='contact-balance'),
    path('<int:contact_id>/credit-check/', contact_controller.check_credit_limit, name='contact-credit-check'),
]