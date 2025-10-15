"""Auth service - Authentication business logic"""
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from layers.repositories.user_repository import UserRepository
from core.exceptions import AuthenticationError, ValidationError


class AuthService:
    """Handles authentication business logic"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def login(self, username, password):
        """
        Authenticate user and return tokens
        
        Args:
            username (str): User's username
            password (str): User's password
            
        Returns:
            dict: User data and JWT tokens
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if not user:
            raise AuthenticationError("Invalid username or password")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }
    
    def logout(self, refresh_token):
        """
        Logout user by blacklisting refresh token
        
        Args:
            refresh_token (str): JWT refresh token
            
        Returns:
            bool: True if successful
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return True
        except Exception:
            # If blacklist fails, just return False
            # This could happen if token is already blacklisted or invalid
            return False
    
    def refresh_token(self, refresh_token):
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token (str): JWT refresh token
            
        Returns:
            dict: New access token
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            refresh = RefreshToken(refresh_token)
            return {
                'access': str(refresh.access_token),
            }
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {str(e)}")
    
    def change_password(self, user_id, old_password, new_password):
        """
        Change user password
        
        Args:
            user_id (int): User ID
            old_password (str): Current password
            new_password (str): New password
            
        Returns:
            bool: True if successful
            
        Raises:
            ValidationError: If old password is incorrect or validation fails
        """
        user = self.user_repo.get_by_id(user_id)
        
        if not user:
            raise ValidationError("User not found")
        
        # Verify old password
        if not user.check_password(old_password):
            raise ValidationError("Current password is incorrect")
        
        # Validate new password
        if len(new_password) < 8:
            raise ValidationError("New password must be at least 8 characters long")
        
        if old_password == new_password:
            raise ValidationError("New password must be different from current password")
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return True