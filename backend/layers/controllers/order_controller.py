"""Order API controllers"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from layers.services.order_service import OrderService, OrderItemService
from layers.serializers.order_serializers import (
    OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, OrderUpdateSerializer,
    OrderStatusUpdateSerializer, ConvertToInvoiceSerializer,
    OrderStatsSerializer, OrderItemSerializer,
    OrderItemCreateSerializer, OrderItemFulfillmentSerializer
)
from layers.serializers.invoice_serializers import InvoiceDetailSerializer
from core.permissions import IsManager, IsAccountant
from core.exceptions import ValidationError, NotFoundError


# ==================== ORDER ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_orders(request):
    """Get all orders"""
    try:
        order_type = request.query_params.get('type', None)
        status_filter = request.query_params.get('status', None)
        contact_id = request.query_params.get('contact_id', None)
        search = request.query_params.get('search', None)
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        orders = OrderService.get_all_orders(order_type, status_filter, contact_id, search)
        
        paginator = Paginator(orders, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = OrderListSerializer(page_obj, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sales_orders(request):
    """Get all sales orders"""
    try:
        status_filter = request.query_params.get('status', None)
        search = request.query_params.get('search', None)
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        orders = OrderService.get_sales_orders(status_filter, search)
        
        paginator = Paginator(orders, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = OrderListSerializer(page_obj, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_purchase_orders(request):
    """Get all purchase orders"""
    try:
        status_filter = request.query_params.get('status', None)
        search = request.query_params.get('search', None)
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        orders = OrderService.get_purchase_orders(status_filter, search)
        
        paginator = Paginator(orders, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = OrderListSerializer(page_obj, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'page_size': page_size,
            }
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_by_id(request, order_id):
    """Get order by ID"""
    try:
        order = OrderService.get_order_by_id(order_id)
        serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_order(request):
    """Create a new order"""
    try:
        serializer = OrderCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract items data
        items_data = serializer.validated_data.pop('items')
        
        order = OrderService.create_order(
            serializer.validated_data,
            items_data,
            user=request.user
        )
        
        response_serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Order created successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsManager])
def update_order(request, order_id):
    """Update an order"""
    try:
        serializer = OrderUpdateSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order = OrderService.update_order(order_id, serializer.validated_data)
        response_serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Order updated successfully',
            'data': response_serializer.data
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsManager])
def delete_order(request, order_id):
    """Delete an order"""
    try:
        OrderService.delete_order(order_id)
        
        return Response({
            'success': True,
            'message': 'Order deleted successfully'
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsManager])
def update_order_status(request, order_id):
    """Update order status"""
    try:
        serializer = OrderStatusUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order = OrderService.update_status(
            order_id,
            serializer.validated_data['status'],
            serializer.validated_data.get('notes'),
            user=request.user
        )
        
        response_serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Order status updated successfully',
            'data': response_serializer.data
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def confirm_order(request, order_id):
    """Confirm an order"""
    try:
        order = OrderService.confirm_order(order_id, user=request.user)
        serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Order confirmed successfully',
            'data': serializer.data
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def cancel_order(request, order_id):
    """Cancel an order"""
    try:
        reason = request.data.get('reason', 'Order cancelled')
        order = OrderService.cancel_order(order_id, reason, user=request.user)
        serializer = OrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
            'data': serializer.data
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def convert_to_invoice(request, order_id):
    """Convert order to invoice"""
    try:
        invoice = OrderService.convert_to_invoice(order_id, user=request.user)
        serializer = InvoiceDetailSerializer(invoice)
        
        return Response({
            'success': True,
            'message': 'Order converted to invoice successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_statistics(request):
    """Get order statistics"""
    try:
        order_type = request.query_params.get('type', None)
        stats = OrderService.get_statistics(order_type)
        serializer = OrderStatsSerializer(stats)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== ORDER ITEM ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def add_order_item(request, order_id):
    """Add item to order"""
    try:
        serializer = OrderItemCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item = OrderItemService.add_item(order_id, serializer.validated_data)
        response_serializer = OrderItemSerializer(item)
        
        return Response({
            'success': True,
            'message': 'Item added successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsManager])
def update_order_item(request, item_id):
    """Update order item"""
    try:
        serializer = OrderItemCreateSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        item = OrderItemService.update_item(item_id, serializer.validated_data)
        response_serializer = OrderItemSerializer(item)
        
        return Response({
            'success': True,
            'message': 'Item updated successfully',
            'data': response_serializer.data
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsManager])
def delete_order_item(request, item_id):
    """Delete order item"""
    try:
        OrderItemService.remove_item(item_id)
        
        return Response({
            'success': True,
            'message': 'Item deleted successfully'
        })
    except NotFoundError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)