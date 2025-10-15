"""User repository - Data access layer"""
from django.db.models import Q, Count
from layers.repositories.base_repository import BaseRepository
from layers.models.user_models import User


class UserRepository(BaseRepository):
    """Repository for User data operations"""
    
    def __init__(self):
        super().__init__(User)
    
    def find_by_username(self, username):
        """Find user by username"""
        return self.model.objects.filter(username=username).first()
    
    def find_by_email(self, email):
        """Find user by email"""
        return self.model.objects.filter(email=email).first()
    
    def find_by_role(self, role):
        """Find users by role"""
        return self.model.objects.filter(role=role)
    
    def get_active_users(self):
        """Get all active users"""
        return self.model.objects.filter(is_active=True)
    
    def filter_users(self, filters):
        """
        Filter users with multiple criteria
        
        Args:
            filters (dict): Filter parameters
                - role (str): User role
                - department (str): Department
                - is_active (bool): Active status
                - search (str): Search query
        
        Returns:
            QuerySet: Filtered users
        """
        queryset = self.model.objects.all()
        
        if 'role' in filters:
            queryset = queryset.filter(role=filters['role'])
        
        if 'department' in filters:
            queryset = queryset.filter(department__icontains=filters['department'])
        
        if 'is_active' in filters:
            is_active = str(filters['is_active']).lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if 'search' in filters:
            search_query = filters['search']
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        return queryset
    
    def get_user_statistics(self):
        """Get user statistics"""
        return {
            'total_users': self.model.objects.count(),
            'active_users': self.model.objects.filter(is_active=True).count(),
            'inactive_users': self.model.objects.filter(is_active=False).count(),
            'by_role': dict(
                self.model.objects.values('role').annotate(count=Count('id')).values_list('role', 'count')
            ),
            'by_department': dict(
                self.model.objects.exclude(department='').values('department').annotate(count=Count('id')).values_list('department', 'count')
            )
        }