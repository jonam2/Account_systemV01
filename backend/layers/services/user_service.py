"""User service with business logic"""
import re
from typing import List, Optional, Dict
from django.contrib.auth.hashers import make_password
from layers.repositories.user_repository import UserRepository
from layers.models.user_models import User
from core.exceptions import ValidationError, NotFoundError, DuplicateError

class UserService:
    """Handles all user-related business logic"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def get_all_users(self, filters: Optional[Dict] = None) -> List[User]:
        """
        Get all users with optional filters
        
        Args:
            filters: Optional filters (role, department, is_active, search)
            
        Returns:
            List of User objects
        """
        if not filters:
            return self.user_repo.get_all()
        
        users = self.user_repo.get_all()
        
        # Apply filters
        if filters.get('role'):
            users = users.filter(role=filters['role'])
        
        if filters.get('department'):
            users = users.filter(department=filters['department'])
        
        if filters.get('is_active') is not None:
            users = users.filter(is_active=filters['is_active'])
        
        if filters.get('search'):
            search = filters['search']
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        
        return users
    
    def get_user_by_id(self, user_id: int) -> User:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object
            
        Raises:
            NotFoundError: If user doesn't exist
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        return user
    
    def create_user(self, data: Dict) -> User:
        """
        Create new user with validations
        
        Args:
            data: User data dictionary
            
        Returns:
            Created User object
            
        Raises:
            ValidationError: If validation fails
            DuplicateError: If username/email already exists
        """
        # Validation 1: Required fields
        required_fields = ['username', 'email', 'password', 'role']
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")
        
        # Validation 2: Email format
        if not self._is_valid_email(data['email']):
            raise ValidationError("Invalid email format")
        
        # Validation 3: Password strength
        if len(data['password']) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        # Validation 4: Check username uniqueness
        if self.user_repo.get_by_username(data['username']):
            raise DuplicateError("Username already exists")
        
        # Validation 5: Check email uniqueness
        if self.user_repo.get_by_email(data['email']):
            raise DuplicateError("Email already exists")
        
        # Business Rule 1: Minimum salary for managers
        if data['role'] == 'manager' and data.get('salary', 0) < 10000:
            raise ValidationError("Manager salary must be at least 10,000")
        
        # Business Rule 2: Department is required for non-sales roles
        if data['role'] != 'sales' and not data.get('department'):
            raise ValidationError(f"Department is required for {data['role']} role")
        
        # Hash password
        data['password'] = make_password(data['password'])
        
        # Create user
        user = self.user_repo.create(**data)
        return user
    
    def update_user(self, user_id: int, data: Dict) -> User:
        """
        Update user with validations
        
        Args:
            user_id: User ID
            data: Updated data
            
        Returns:
            Updated User object
            
        Raises:
            NotFoundError: If user doesn't exist
            ValidationError: If validation fails
        """
        # Check if user exists
        user = self.get_user_by_id(user_id)
        
        # Validation: Email format
        if data.get('email') and not self._is_valid_email(data['email']):
            raise ValidationError("Invalid email format")
        
        # Validation: Email uniqueness (if changing)
        if data.get('email') and data['email'] != user.email:
            if self.user_repo.get_by_email(data['email']):
                raise DuplicateError("Email already exists")
        
        # Business Rule: Manager salary
        if data.get('role') == 'manager' and data.get('salary', 0) < 10000:
            raise ValidationError("Manager salary must be at least 10,000")
        
        # Hash password if provided
        if data.get('password'):
            data['password'] = make_password(data['password'])
        
        # Update user
        updated_user = self.user_repo.update(user_id, **data)
        return updated_user
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete user
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
            
        Raises:
            NotFoundError: If user doesn't exist
        """
        user = self.get_user_by_id(user_id)
        return self.user_repo.delete(user_id)
    
    def get_user_statistics(self) -> Dict:
        """
        Calculate user statistics
        
        Returns:
            Dictionary with statistics
        """
        total_users = self.user_repo.count()
        active_users = self.user_repo.count(is_active=True)
        inactive_users = total_users - active_users
        
        total_salaries = self.user_repo.get_total_salaries(is_active=True)
        average_salary = total_salaries / active_users if active_users > 0 else 0
        
        by_role = self.user_repo.get_stats_by_role()
        by_department = self.user_repo.get_stats_by_department()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'total_salaries': float(total_salaries),
            'average_salary': float(average_salary),
            'by_role': by_role,
            'by_department': by_department,
        }
    
    def search_users(self, query: str) -> List[User]:
        """
        Search users
        
        Args:
            query: Search query
            
        Returns:
            List of matching users
        """
        return self.user_repo.search(query)
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(pattern, email) is not None