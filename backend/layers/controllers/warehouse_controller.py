"""Warehouse controller - API endpoints"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from layers.services.warehouse_service import WarehouseService
from layers.serializers.warehouse_serializers import (
    WarehouseSerializer,
    WarehouseCreateSerializer,
    WarehouseUpdateSerializer,
    StockSerializer,
    StockAdjustmentSerializer,
    StockTransferSerializer,
    StockUpdateSerializer,
    StockMovementSerializer,
    StockMovementListSerializer
)
from core.permissions import IsManager
from core.exceptions import ValidationError, NotFoundError, DuplicateError

warehouse_service = WarehouseService()


# Warehouse endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_warehouses(request):
    """
    GET /api/v1/warehouses/
    
    List all warehouses with optional filters
    
    Query Params:
        - is_active (boolean): Filter by status
        - city (string): Filter by city
        - search (string): Search query
    """
    try:
        filters = {
            'is_active': request.query_params.get('is_active'),
            'city': request.query_params.get('city'),
            'search': request.query_params.get('search'),
        }
        
        filters = {k: v for k, v in filters.items() if v is not None}
        
        warehouses = warehouse_service.get_all_warehouses(filters)
        serializer = WarehouseSerializer(warehouses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_warehouse(request):
    """
    POST /api/v1/warehouses/create/
    
    Create new warehouse
    """
    try:
        serializer = WarehouseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        warehouse = warehouse_service.create_warehouse(serializer.validated_data)
        response_serializer = WarehouseSerializer(warehouse)
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
def get_warehouse(request, warehouse_id):
    """
    GET /api/v1/warehouses/{id}/
    
    Get warehouse details
    """
    try:
        warehouse = warehouse_service.get_warehouse_by_id(warehouse_id)
        serializer = WarehouseSerializer(warehouse)
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
def update_warehouse(request, warehouse_id):
    """
    PUT/PATCH /api/v1/warehouses/{id}/update/
    
    Update warehouse
    """
    try:
        serializer = WarehouseUpdateSerializer(
            data=request.data,
            partial=request.method == 'PATCH'
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        warehouse = warehouse_service.update_warehouse(warehouse_id, serializer.validated_data)
        response_serializer = WarehouseSerializer(warehouse)
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
def delete_warehouse(request, warehouse_id):
    """
    DELETE /api/v1/warehouses/{id}/delete/
    
    Delete warehouse (soft delete)
    """
    try:
        warehouse_service.delete_warehouse(warehouse_id)
        return Response(
            {'message': 'Warehouse deleted successfully'},
            status=status.HTTP_200_OK
        )
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Stock endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_warehouse_stocks(request, warehouse_id):
    """
    GET /api/v1/warehouses/{id}/stocks/
    
    Get all stocks in a warehouse
    """
    try:
        stocks = warehouse_service.get_warehouse_stocks(warehouse_id)
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_stocks(request, product_id):
    """
    GET /api/v1/warehouses/stocks/product/{product_id}/
    
    Get all stocks for a product across warehouses
    """
    try:
        stocks = warehouse_service.get_all_product_stocks(product_id)
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def adjust_stock(request):
    """
    POST /api/v1/warehouses/stocks/adjust/
    
    Adjust stock quantity (manual adjustment)
    
    Body:
        - warehouse_id (int): Warehouse ID
        - product_id (int): Product ID
        - quantity (decimal): Quantity to add/remove
        - notes (string): Adjustment notes
    """
    try:
        serializer = StockAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        stock = warehouse_service.adjust_stock(
            warehouse_id=data['warehouse_id'],
            product_id=data['product_id'],
            quantity=data['quantity'],
            notes=data.get('notes', ''),
            user_id=request.user.id
        )
        
        response_serializer = StockSerializer(stock)
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
@permission_classes([IsAuthenticated, IsManager])
def transfer_stock(request):
    """
    POST /api/v1/warehouses/stocks/transfer/
    
    Transfer stock between warehouses
    
    Body:
        - from_warehouse_id (int): Source warehouse ID
        - to_warehouse_id (int): Destination warehouse ID
        - product_id (int): Product ID
        - quantity (decimal): Quantity to transfer
        - notes (string): Transfer notes
    """
    try:
        serializer = StockTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        result = warehouse_service.transfer_stock(
            from_warehouse_id=data['from_warehouse_id'],
            to_warehouse_id=data['to_warehouse_id'],
            product_id=data['product_id'],
            quantity=data['quantity'],
            notes=data.get('notes', ''),
            user_id=request.user.id
        )
        
        return Response({
            'message': 'Stock transferred successfully',
            'from_stock': StockSerializer(result['from_stock']).data,
            'to_stock': StockSerializer(result['to_stock']).data
        }, status=status.HTTP_200_OK)
        
    except NotFoundError as e:
        return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_low_stock_items(request):
    """
    GET /api/v1/warehouses/stocks/low-stock/
    
    Get items with low stock
    
    Query Params:
        - warehouse_id (int): Filter by warehouse
    """
    try:
        warehouse_id = request.query_params.get('warehouse_id')
        stocks = warehouse_service.get_low_stock_items(warehouse_id)
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_out_of_stock_items(request):
    """
    GET /api/v1/warehouses/stocks/out-of-stock/
    
    Get out of stock items
    
    Query Params:
        - warehouse_id (int): Filter by warehouse
    """
    try:
        warehouse_id = request.query_params.get('warehouse_id')
        stocks = warehouse_service.get_out_of_stock_items(warehouse_id)
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Stock Movement endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_stock_movements(request):
    """
    GET /api/v1/warehouses/movements/
    
    List stock movements with filters
    
    Query Params:
        - warehouse_id (int): Filter by warehouse
        - product_id (int): Filter by product
        - movement_type (string): Filter by type
        - date_from (date): Filter from date
        - date_to (date): Filter to date
    """
    try:
        filters = {
            'warehouse_id': request.query_params.get('warehouse_id'),
            'product_id': request.query_params.get('product_id'),
            'movement_type': request.query_params.get('movement_type'),
            'date_from': request.query_params.get('date_from'),
            'date_to': request.query_params.get('date_to'),
        }
        
        filters = {k: v for k, v in filters.items() if v is not None}
        
        movements = warehouse_service.get_stock_movements(filters)
        serializer = StockMovementListSerializer(movements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager])
def warehouse_statistics(request):
    """
    GET /api/v1/warehouses/stats/
    
    Get warehouse statistics
    
    Query Params:
        - warehouse_id (int): Get stats for specific warehouse
    """
    try:
        warehouse_id = request.query_params.get('warehouse_id')
        stats = warehouse_service.get_warehouse_statistics(warehouse_id)
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'An error occurred: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )