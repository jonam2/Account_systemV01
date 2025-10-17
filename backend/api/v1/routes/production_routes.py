# """Production URL routes"""
# from django.urls import path
# from layers.controllers import production_controller

# urlpatterns = [
#     # BOM endpoints
#     path('bom/', production_controller.get_all_boms, name='bom-list'),
#     path('bom/create/', production_controller.create_bom, name='bom-create'),
#     path('bom/<int:bom_id>/', production_controller.get_bom_by_id, name='bom-detail'),
#     path('bom/<int:bom_id>/update/', production_controller.update_bom, name='bom-update'),
#     path('bom/<int:bom_id>/delete/', production_controller.delete_bom, name='bom-delete'),
    
#     # BOM component endpoints
#     path('bom/<int:bom_id>/components/add/', production_controller.add_bom_component, name='bom-component-add'),
#     path('bom/components/<int:component_id>/update/', production_controller.update_bom_component, name='bom-component-update'),
#     path('bom/components/<int:component_id>/delete/', production_controller.delete_bom_component, name='bom-component-delete'),
    
#     # Component availability check
#     path('check-availability/', production_controller.check_component_availability, name='check-availability'),
    
#     # Production order endpoints
#     path('orders/', production_controller.get_all_production_orders, name='production-order-list'),
#     path('orders/create/', production_controller.create_production_order, name='production-order-create'),
#     path('orders/<int:order_id>/', production_controller.get_production_order_by_id, name='production-order-detail'),
#     path('orders/<int:order_id>/status/', production_controller.update_production_order_status, name='production-order-status'),
#     path('orders/<int:order_id>/cancel/', production_controller.cancel_production_order, name='production-order-cancel'),
    
#     # Production processing
#     path('assembly/<int:order_id>/process/', production_controller.process_assembly, name='process-assembly'),
#     path('disassembly/<int:order_id>/process/', production_controller.process_disassembly, name='process-disassembly'),
    
#     # Statistics
#     path('stats/', production_controller.get_production_statistics, name='production-stats'),
# ]
from django.urls import path
from layers.controllers import production_controller

urlpatterns = [
    # ==================== BOM Routes ====================
    path('bom/', production_controller.list_boms, name='list_boms'),
    path('bom/create/', production_controller.create_bom, name='create_bom'),
    path('bom/<int:pk>/', production_controller.get_bom, name='get_bom'),
    path('bom/<int:pk>/update/', production_controller.update_bom, name='update_bom'),
    path('bom/<int:pk>/delete/', production_controller.delete_bom, name='delete_bom'),
    path('bom/<int:pk>/cost-breakdown/', production_controller.get_bom_cost_breakdown, name='bom_cost_breakdown'),
    path('bom/check-availability/', production_controller.check_component_availability, name='check_component_availability'),
    
    # ==================== Production Order Routes ====================
    path('orders/', production_controller.list_production_orders, name='list_production_orders'),
    path('orders/<int:pk>/', production_controller.get_production_order, name='get_production_order'),
    path('orders/<int:pk>/delete/', production_controller.delete_production_order, name='delete_production_order'),
    path('orders/<int:pk>/cancel/', production_controller.cancel_production_order, name='cancel_production_order'),
    
    # ==================== Assembly Routes ====================
    path('assembly/create/', production_controller.create_assembly_order, name='create_assembly_order'),
    path('assembly/<int:pk>/confirm/', production_controller.confirm_assembly_order, name='confirm_assembly_order'),
    path('assembly/<int:pk>/start/', production_controller.start_assembly_order, name='start_assembly_order'),
    path('assembly/<int:pk>/complete/', production_controller.complete_assembly_order, name='complete_assembly_order'),
    
    # ==================== Disassembly Routes ====================
    path('disassembly/create/', production_controller.create_disassembly_order, name='create_disassembly_order'),
    path('disassembly/<int:pk>/start/', production_controller.start_disassembly_order, name='start_disassembly_order'),
    path('disassembly/<int:pk>/complete/', production_controller.complete_disassembly_order, name='complete_disassembly_order'),
    
    # ==================== Statistics & Reports ====================
    path('stats/', production_controller.get_production_statistics, name='production_statistics'),
    path('history/<int:product_id>/', production_controller.get_production_history, name='production_history'),
]