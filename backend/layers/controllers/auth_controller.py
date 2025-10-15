"""Auth controller - Authentication API endpoints"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from layers.services.auth_service import AuthService
from layers.serializers.user_serializers import UserSerializer
from core.exceptions import AuthenticationError, ValidationError

auth_service = AuthService()


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    POST /api/v1/auth/login/
    
    Login user and return JWT tokens
    
    Body:
        - username (string): Username
        - password (string): Password
    
    Returns:
        - user: User information
        - tokens: Access and refresh tokens
    """
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = auth_service.login(username, password)
        return Response(result, status=status.HTTP_200_OK)
        
    except AuthenticationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    POST /api/v1/auth/logout/
    
    Logout user by blacklisting refresh token
    
    Body:
        - refresh_token (string): JWT refresh token
    
    Returns:
        - message: Success message
    """
    try:
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service.logout(refresh_token)
        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    GET /api/v1/auth/me/
    
    Get current authenticated user details
    
    Returns:
        - User information
    """
    try:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    POST /api/v1/auth/change-password/
    
    Change user password
    
    Body:
        - old_password (string): Current password
        - new_password (string): New password
    
    Returns:
        - message: Success message
    """
    try:
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old and new passwords are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        auth_service.change_password(request.user.id, old_password, new_password)
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )
        
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )