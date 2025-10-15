"""Warehouse routes - URL configuration"""
from django.urls import path
from layers.controllers import warehouse_controller

urlpatterns = [
    # Warehouse CRUD
    path('', warehouse_controller.list_warehouses, name='warehouse-list'),
    path('create/', warehouse_controller.create_warehouse, name='warehouse-create'),
    path('<int:warehouse_id>/', warehouse_controller.get_warehouse, name='warehouse-detail'),
    path('<int:warehouse_id>/update/', warehouse_controller.update_warehouse, name='warehouse-update'),
    path('<int:warehouse_id>/delete/', warehouse_controller.delete_warehouse, name='warehouse-delete'),
    
    # Warehouse stocks
    path('<int:warehouse_id>/stocks/', warehouse_controller.get_warehouse_stocks, name='warehouse-stocks'),
    
    # Stock operations
    path('stocks/product/<int:product_id>/', warehouse_controller.get_product_stocks, name='product-stocks'),
    path('stocks/adjust/', warehouse_controller.adjust_stock, name='stock-adjust'),
    path('stocks/transfer/', warehouse_controller.transfer_stock, name='stock-transfer'),
    path('stocks/low-stock/', warehouse_controller.get_low_stock_items, name='stock-low'),
    path('stocks/out-of-stock/', warehouse_controller.get_out_of_stock_items, name='stock-out'),
    
    # Stock movements
    path('movements/', warehouse_controller.list_stock_movements, name='stock-movements'),
    
    # Statistics
    path('stats/', warehouse_controller.warehouse_statistics, name='warehouse-stats'),
]