"""User routes"""
from django.urls import path
from layers.controllers import user_controller

urlpatterns = [
    # List all users
    path('', user_controller.list_users, name='user-list'),
    
    # Create new user
    path('create/', user_controller.create_user, name='user-create'),
    
    # Get user by ID
    path('<int:user_id>/', user_controller.get_user, name='user-detail'),
    
    # Update user
    path('<int:user_id>/update/', user_controller.update_user, name='user-update'),
    
    # Delete user
    path('<int:user_id>/delete/', user_controller.delete_user, name='user-delete'),
    
    # User statistics (FIXED: changed from user_statistics to user_statistics)
    path('stats/', user_controller.user_statistics, name='user-stats'),
]