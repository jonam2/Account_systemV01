"""
User Service - Complete Business Logic Layer
Handles user management operations
"""
from django.db import transaction
from django.contrib.auth.hashers import make_password
import logging

from layers.repositories.user_repository import UserRepository
from core.exceptions import ValidationError, NotFoundError, DuplicateError

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    @transaction.atomic
    def create_user(self, data):
        """
        Create a new user
        
        Args:
            data (dict): User data including username, email, password, etc.
            
        Returns:
            User: Created user
        """
        try:
            # Check for duplicate username
            if self.user_repo.find_by_username(data.get('username')):
                raise DuplicateError(f"Username {data['username']} already exists")
            
            # Check for duplicate email
            if data.get('email') and self.user_repo.find_by_email(data['email']):
                raise DuplicateError(f"Email {data['email']} already exists")
            
            # Validate required fields
            if not data.get('username'):
                raise ValidationError("Username is required")
            if not data.get('password'):
                raise ValidationError("Password is required")
            
            # Hash password
            data['password'] = make_password(data['password'])
            
            # Set defaults
            if 'is_active' not in data:
                data['is_active'] = True
            if 'is_staff' not in data:
                data['is_staff'] = False
            if 'is_superuser' not in data:
                data['is_superuser'] = False
            
            user = self.user_repo.create(data)
            logger.info(f"User created: {user.username}")
            return user
            
        except DuplicateError as e:
            logger.warning(f"User creation failed: {str(e)}")
            raise
        except ValidationError as e:
            logger.warning(f"User creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create user: {str(e)}")
    
    @transaction.atomic
    def update_user(self, user_id, data):
        """Update user"""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")
            
            # Check for duplicate username if changing
            if 'username' in data and data['username'] != user.username:
                if self.user_repo.find_by_username(data['username']):
                    raise DuplicateError(f"Username {data['username']} already exists")
            
            # Check for duplicate email if changing
            if 'email' in data and data['email'] != user.email:
                if data['email'] and self.user_repo.find_by_email(data['email']):
                    raise DuplicateError(f"Email {data['email']} already exists")
            
            # Hash password if being changed
            if 'password' in data:
                data['password'] = make_password(data['password'])
            
            updated = self.user_repo.update(user_id, data)
            logger.info(f"User updated: {updated.username}")
            return updated
            
        except (NotFoundError, DuplicateError, ValidationError) as e:
            logger.warning(f"User update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating user: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update user: {str(e)}")
    
    @transaction.atomic
    def delete_user(self, user_id):
        """Delete user (deactivate instead of hard delete)"""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")
            
            # Don't allow deleting superusers
            if user.is_superuser:
                raise ValidationError("Cannot delete superuser")
            
            # Deactivate instead of delete
            user.is_active = False
            user.save()
            
            logger.info(f"User deactivated: {user.username}")
            return True
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"User deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting user: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete user: {str(e)}")
    
    def get_all_users(self, filters=None):
        """Get all users with filters"""
        try:
            filters = filters or {}
            return self.user_repo.filter_users(filters)
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to list users: {str(e)}")
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user
    
    def get_user_by_username(self, username):
        """Get user by username"""
        user = self.user_repo.find_by_username(username)
        if not user:
            raise NotFoundError(f"User {username} not found")
        return user
    
    def get_user_statistics(self):
        """Get user statistics"""
        return self.user_repo.get_user_statistics()
    
    @transaction.atomic
    def change_user_role(self, user_id, new_role):
        """Change user role"""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")
            
            # Validate role
            from layers.models import User
            if new_role not in dict(User.Roles.choices):
                raise ValidationError(f"Invalid role: {new_role}")
            
            user.role = new_role
            user.save()
            
            logger.info(f"User role changed: {user.username} -> {new_role}")
            return user
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Role change failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error changing role: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to change role: {str(e)}")