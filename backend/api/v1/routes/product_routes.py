"""Product routes"""
from django.urls import path
from layers.controllers import product_controller

urlpatterns = [
    # Product endpoints
    path('', product_controller.list_products, name='product-list'),
    path('create/', product_controller.create_product, name='product-create'),
    path('<int:product_id>/', product_controller.get_product, name='product-detail'),
    path('<int:product_id>/update/', product_controller.update_product, name='product-update'),
    path('<int:product_id>/delete/', product_controller.delete_product, name='product-delete'),
    path('stats/', product_controller.product_statistics, name='product-stats'),
    
    # Category endpoints
    path('categories/', product_controller.list_categories, name='category-list'),
    path('categories/create/', product_controller.create_category, name='category-create'),
    path('categories/<int:category_id>/', product_controller.get_category, name='category-detail'),
]