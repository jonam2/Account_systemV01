"""User controller"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from layers.services.user_service import UserService
from layers.serializers.user_serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer
from core.permissions import IsManager
from core.exceptions import ValidationError, NotFoundError, DuplicateError

user_service = UserService()

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager])
def list_users(request):
    """
    GET /api/v1/users/
    
    List all users with optional filters
    
    Query Params:
        - role (string): Filter by role
        - department (string): Filter by department
        - is_active (boolean): Filter by status
        - search (string): Search query
    """
    try:
        filters = {
            'role': request.query_params.get('role'),
            'department': request.query_params.get('department'),
            'is_active': request.query_params.get('is_active'),
            'search': request.query_params.get('search'),
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        users = user_service.get_all_users(filters)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_user(request):
    """
    POST /api/v1/users/create/
    
    Create new user
    """
    try:
        serializer = UserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = user_service.create_user(serializer.validated_data)
        response_serializer = UserSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except DuplicateError as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager])
def get_user(request, user_id):
    """
    GET /api/v1/users/{id}/
    
    Get user details
    """
    try:
        user = user_service.get_user_by_id(user_id)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsManager])
def update_user(request, user_id):
    """
    PUT/PATCH /api/v1/users/{id}/update/
    
    Update user
    """
    try:
        serializer = UserUpdateSerializer(data=request.data, partial=request.method == 'PATCH')
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = user_service.update_user(user_id, serializer.validated_data)
        response_serializer = UserSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except DuplicateError as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsManager])
def delete_user(request, user_id):
    """
    DELETE /api/v1/users/{id}/delete/
    
    Delete user
    """
    try:
        user_service.delete_user(user_id)
        return Response(
            {'message': 'User deleted successfully'},
            status=status.HTTP_200_OK
        )
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager])
def user_statistics(request):
    """
    GET /api/v1/users/stats/
    
    Get user statistics
    """
    try:
        stats = user_service.get_user_statistics()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )