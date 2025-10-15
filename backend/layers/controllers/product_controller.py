"""Product controller"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from layers.services.product_service import ProductService, CategoryService
from layers.serializers.product_serializers import (
    ProductSerializer, ProductCreateSerializer, ProductUpdateSerializer,
    CategorySerializer, CategoryCreateSerializer
)
from core.permissions import IsManager, IsAccountant, IsWarehouseManager
from core.exceptions import ValidationError, NotFoundError, DuplicateError

product_service = ProductService()
category_service = CategoryService()

# ==================== PRODUCT ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_products(request):
    """
    GET /api/v1/products/
    
    List all products with optional filters
    """
    try:
        filters = {
            'category_id': request.query_params.get('category_id'),
            'is_active': request.query_params.get('is_active'),
            'search': request.query_params.get('search'),
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        
        products = product_service.get_all_products(filters)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_product(request):
    """
    POST /api/v1/products/create/
    
    Create new product
    """
    try:
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product = product_service.create_product(serializer.validated_data)
        response_serializer = ProductSerializer(product)
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
def get_product(request, product_id):
    """
    GET /api/v1/products/{id}/
    
    Get product details
    """
    try:
        product = product_service.get_product_by_id(product_id)
        serializer = ProductSerializer(product)
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
def update_product(request, product_id):
    """
    PUT/PATCH /api/v1/products/{id}/update/
    
    Update product
    """
    try:
        serializer = ProductUpdateSerializer(
            data=request.data, 
            partial=request.method == 'PATCH'
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product = product_service.update_product(product_id, serializer.validated_data)
        response_serializer = ProductSerializer(product)
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
def delete_product(request, product_id):
    """
    DELETE /api/v1/products/{id}/delete/
    
    Delete product (soft delete)
    """
    try:
        product_service.delete_product(product_id)
        return Response(
            {'message': 'Product deleted successfully'},
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
def product_statistics(request):
    """
    GET /api/v1/products/stats/
    
    Get product statistics
    """
    try:
        stats = product_service.get_product_statistics()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== CATEGORY ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_categories(request):
    """
    GET /api/v1/products/categories/
    
    List all categories
    """
    try:
        categories = category_service.get_all_categories()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_category(request):
    """
    POST /api/v1/products/categories/create/
    
    Create new category
    """
    try:
        serializer = CategoryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        category = category_service.create_category(serializer.validated_data)
        response_serializer = CategorySerializer(category)
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
def get_category(request, category_id):
    """
    GET /api/v1/products/categories/{id}/
    
    Get category details
    """
    try:
        category = category_service.get_category_by_id(category_id)
        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )