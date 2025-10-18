"""
Authentication Service - Complete Business Logic Layer
Handles authentication and authorization operations
"""
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
import logging

from layers.repositories.user_repository import UserRepository
from core.exceptions import AuthenticationError, ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def login(self, username, password):
        """
        Authenticate user and return tokens
        
        Args:
            username (str): Username
            password (str): Password
            
        Returns:
            dict: User data and tokens
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Authenticate user
            user = authenticate(username=username, password=password)
            
            if not user:
                logger.warning(f"Failed login attempt for username: {username}")
                raise AuthenticationError("Invalid username or password")
            
            if not user.is_active:
                logger.warning(f"Login attempt for inactive user: {username}")
                raise AuthenticationError("User account is inactive")
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            logger.info(f"User logged in: {username}")
            
            return {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'full_name': user.full_name,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            raise AuthenticationError("Login failed. Please try again.")
    
    def logout(self, refresh_token):
        """
        Logout user by blacklisting refresh token
        
        Args:
            refresh_token (str): JWT refresh token
            
        Returns:
            bool: Success status
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            logger.info("User logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}", exc_info=True)
            # Don't raise error on logout failure
            return False
    
    def refresh_token(self, refresh_token):
        """
        Refresh access token
        
        Args:
            refresh_token (str): JWT refresh token
            
        Returns:
            dict: New access token
        """
        try:
            refresh = RefreshToken(refresh_token)
            
            return {
                'access': str(refresh.access_token),
            }
            
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
            raise AuthenticationError("Invalid or expired refresh token")
    
    def change_password(self, user_id, old_password, new_password):
        """
        Change user password
        
        Args:
            user_id (int): User ID
            old_password (str): Current password
            new_password (str): New password
            
        Returns:
            bool: Success status
        """
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")
            
            # Verify old password
            if not check_password(old_password, user.password):
                raise ValidationError("Current password is incorrect")
            
            # Validate new password
            if len(new_password) < 8:
                raise ValidationError("New password must be at least 8 characters long")
            
            if old_password == new_password:
                raise ValidationError("New password must be different from current password")
            
            # Update password
            from django.contrib.auth.hashers import make_password
            user.password = make_password(new_password)
            user.save()
            
            logger.info(f"Password changed for user: {user.username}")
            return True
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Password change failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error changing password: {str(e)}", exc_info=True)
            raise ValidationError("Failed to change password")
    
    def reset_password(self, username, new_password):
        """
        Reset user password (admin function)
        
        Args:
            username (str): Username
            new_password (str): New password
            
        Returns:
            bool: Success status
        """
        try:
            user = self.user_repo.find_by_username(username)
            if not user:
                raise NotFoundError(f"User {username} not found")
            
            # Validate new password
            if len(new_password) < 8:
                raise ValidationError("Password must be at least 8 characters long")
            
            # Update password
            from django.contrib.auth.hashers import make_password
            user.password = make_password(new_password)
            user.save()
            
            logger.info(f"Password reset for user: {username}")
            return True
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Password reset failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error resetting password: {str(e)}", exc_info=True)
            raise ValidationError("Failed to reset password")
    
    def verify_token(self, token):
        """
        Verify JWT token validity
        
        Args:
            token (str): JWT access token
            
        Returns:
            dict: Token payload if valid
        """
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            
            user_id = access_token['user_id']
            user = self.user_repo.get_by_id(user_id)
            
            if not user or not user.is_active:
                raise AuthenticationError("Invalid token")
            
            return {
                'valid': True,
                'user_id': user_id,
                'username': user.username,
                'role': user.role,
            }
            
        except Exception as e:
            logger.warning(f"Token verification failed: {str(e)}")
            raise AuthenticationError("Invalid or expired token")
    
    def check_permission(self, user, required_role):
        """
        Check if user has required role
        
        Args:
            user: User object
            required_role (str): Required role
            
        Returns:
            bool: True if user has permission
        """
        try:
            # Superuser has all permissions
            if user.is_superuser:
                return True
            
            # Manager has most permissions
            if user.role == 'manager':
                return True
            
            # Check specific role
            return user.role == required_role
            
        except Exception as e:
            logger.error(f"Permission check error: {str(e)}", exc_info=True)
            return False
    
    def get_user_permissions(self, user):
        """
        Get user permissions based on role
        
        Args:
            user: User object
            
        Returns:
            dict: Permissions dictionary
        """
        permissions = {
            'can_manage_users': False,
            'can_manage_products': False,
            'can_manage_contacts': False,
            'can_manage_warehouses': False,
            'can_approve_invoices': False,
            'can_manage_orders': False,
            'can_manage_production': False,
            'can_view_reports': False,
        }
        
        # Superuser and Manager have all permissions
        if user.is_superuser or user.role == 'manager':
            return {key: True for key in permissions.keys()}
        
        # Accountant permissions
        if user.role == 'accountant':
            permissions.update({
                'can_manage_contacts': True,
                'can_approve_invoices': True,
                'can_manage_orders': True,
                'can_view_reports': True,
            })
        
        # Sales permissions
        elif user.role == 'sales':
            permissions.update({
                'can_manage_contacts': True,
                'can_manage_orders': True,
                'can_view_reports': True,
            })
        
        # Warehouse Manager permissions
        elif user.role == 'warehouse_manager':
            permissions.update({
                'can_manage_products': True,
                'can_manage_warehouses': True,
                'can_manage_production': True,
                'can_view_reports': True,
            })
        
        return permissions