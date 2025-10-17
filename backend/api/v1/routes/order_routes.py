"""Order URL routes"""
from django.urls import path
from layers.controllers import order_controller

urlpatterns = [
    # Order list endpoints
    path('', order_controller.get_all_orders, name='order-list'),
    path('sales/', order_controller.get_sales_orders, name='sales-order-list'),
    path('purchases/', order_controller.get_purchase_orders, name='purchase-order-list'),
    path('stats/', order_controller.get_order_statistics, name='order-stats'),
    
    # Order CRUD endpoints
    path('create/', order_controller.create_order, name='order-create'),
    path('<int:order_id>/', order_controller.get_order_by_id, name='order-detail'),
    path('<int:order_id>/update/', order_controller.update_order, name='order-update'),
    path('<int:order_id>/delete/', order_controller.delete_order, name='order-delete'),
    
    # Order status endpoints
    path('<int:order_id>/status/', order_controller.update_order_status, name='order-status-update'),
    path('<int:order_id>/confirm/', order_controller.confirm_order, name='order-confirm'),
    path('<int:order_id>/cancel/', order_controller.cancel_order, name='order-cancel'),
    
    # Order conversion
    path('<int:order_id>/convert-to-invoice/', order_controller.convert_to_invoice, name='order-convert-invoice'),
    
    # Order item endpoints
    path('<int:order_id>/items/add/', order_controller.add_order_item, name='order-item-add'),
    path('items/<int:item_id>/update/', order_controller.update_order_item, name='order-item-update'),
    path('items/<int:item_id>/delete/', order_controller.delete_order_item, name='order-item-delete'),
]