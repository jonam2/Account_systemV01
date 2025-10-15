"""Contact controller - API endpoints"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from layers.services.contact_service import ContactService
from layers.serializers.contact_serializers import (
    ContactSerializer,
    ContactCreateSerializer,
    ContactUpdateSerializer,
    ContactListSerializer,
    ContactBalanceUpdateSerializer,
    CreditCheckSerializer
)
from core.permissions import IsManager
from core.exceptions import ValidationError, NotFoundError, DuplicateError

contact_service = ContactService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_contacts(request):
    """
    GET /api/v1/contacts/
    
    List all contacts with optional filters
    
    Query Params:
        - contact_type (string): Filter by type (customer, supplier, both)
        - is_active (boolean): Filter by status
        - city (string): Filter by city
        - country (string): Filter by country
        - search (string): Search query
    """
    try:
        filters = {
            'contact_type': request.query_params.get('contact_type'),
            'is_active': request.query_params.get('is_active'),
            'city': request.query_params.get('city'),
            'country': request.query_params.get('country'),
            'search': request.query_params.get('search'),
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        contacts = contact_service.get_all_contacts(filters)
        serializer = ContactListSerializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_contact(request):
    """
    POST /api/v1/contacts/create/
    
    Create new contact
    """
    try:
        # Add created_by from request user
        data = request.data.copy()
        data['created_by'] = request.user.id
        
        serializer = ContactCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        contact = contact_service.create_contact(serializer.validated_data)
        response_serializer = ContactSerializer(contact)
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
@permission_classes([IsAuthenticated])
def get_contact(request, contact_id):
    """
    GET /api/v1/contacts/{id}/
    
    Get contact details
    """
    try:
        contact = contact_service.get_contact_by_id(contact_id)
        serializer = ContactSerializer(contact)
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
def update_contact(request, contact_id):
    """
    PUT/PATCH /api/v1/contacts/{id}/update/
    
    Update contact
    """
    try:
        serializer = ContactUpdateSerializer(
            data=request.data,
            partial=request.method == 'PATCH'
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        contact = contact_service.update_contact(contact_id, serializer.validated_data)
        response_serializer = ContactSerializer(contact)
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
def delete_contact(request, contact_id):
    """
    DELETE /api/v1/contacts/{id}/delete/
    
    Delete contact (soft delete)
    """
    try:
        contact_service.delete_contact(contact_id)
        return Response(
            {'message': 'Contact deleted successfully'},
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
@permission_classes([IsAuthenticated])
def list_customers(request):
    """
    GET /api/v1/contacts/customers/
    
    List all active customers
    """
    try:
        customers = contact_service.get_customers()
        serializer = ContactListSerializer(customers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_suppliers(request):
    """
    GET /api/v1/contacts/suppliers/
    
    List all active suppliers
    """
    try:
        suppliers = contact_service.get_suppliers()
        serializer = ContactListSerializer(suppliers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager])
def contact_statistics(request):
    """
    GET /api/v1/contacts/stats/
    
    Get contact statistics
    """
    try:
        stats = contact_service.get_contact_statistics()
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def update_balance(request, contact_id):
    """
    POST /api/v1/contacts/{id}/balance/
    
    Update contact balance
    
    Body:
        - amount (decimal): Amount to add/subtract
    """
    try:
        serializer = ContactBalanceUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = serializer.validated_data['amount']
        contact = contact_service.update_contact_balance(contact_id, amount)
        response_serializer = ContactSerializer(contact)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_credit_limit(request, contact_id):
    """
    POST /api/v1/contacts/{id}/credit-check/
    
    Check if amount would exceed credit limit
    
    Body:
        - amount (decimal): Amount to check
    """
    try:
        serializer = CreditCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        amount = serializer.validated_data['amount']
        result = contact_service.check_credit_limit(contact_id, amount)
        return Response(result, status=status.HTTP_200_OK)
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )