from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from layers.services.production_service import ProductionService
from layers.serializers.production_serializers import *
from core.permissions import IsManager, IsAccountant
from core.exceptions import ValidationError, NotFoundError


production_service = ProductionService()


# ==================== BOM Endpoints ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def list_boms(request):
    """List all Bills of Materials"""
    try:
        filters = {
            'product_id': request.GET.get('product_id'),
            'is_active': request.GET.get('is_active'),
            'search': request.GET.get('search'),
        }
        
        boms = production_service.list_boms(filters)
        serializer = BOMListSerializer(boms, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': boms.count()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_bom(request):
    """Create a new BOM"""
    try:
        serializer = BOMCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        components_data = data.pop('components')
        
        bom = production_service.create_bom(
            data=data,
            components_data=components_data,
            user=request.user
        )
        
        result_serializer = BOMDetailSerializer(bom)
        
        return Response({
            'success': True,
            'message': 'BOM created successfully',
            'data': result_serializer.data
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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def get_bom(request, pk):
    """Get BOM details"""
    try:
        bom = production_service.get_bom_details(pk)
        serializer = BOMDetailSerializer(bom)
        
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


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsManager])
def update_bom(request, pk):
    """Update BOM"""
    try:
        serializer = BOMCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        components_data = data.pop('components', None)
        
        bom = production_service.update_bom(
            bom_id=pk,
            data=data,
            components_data=components_data,
            user=request.user
        )
        
        result_serializer = BOMDetailSerializer(bom)
        
        return Response({
            'success': True,
            'message': 'BOM updated successfully',
            'data': result_serializer.data
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
def delete_bom(request, pk):
    """Delete BOM"""
    try:
        production_service.delete_bom(pk, request.user)
        
        return Response({
            'success': True,
            'message': 'BOM deleted successfully'
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
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def check_component_availability(request):
    """Check if components are available for production"""
    try:
        serializer = ComponentAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        availability = production_service.check_component_availability(
            bom_id=serializer.validated_data['bom_id'],
            quantity=serializer.validated_data['quantity'],
            warehouse_id=serializer.validated_data['warehouse_id']
        )
        
        all_available = all(item['is_available'] for item in availability)
        
        return Response({
            'success': True,
            'all_available': all_available,
            'components': availability
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def get_bom_cost_breakdown(request, pk):
    """Get BOM cost breakdown"""
    try:
        breakdown = production_service.get_bom_cost_breakdown(pk)
        
        return Response({
            'success': True,
            'data': breakdown
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


# ==================== Production Order Endpoints ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def list_production_orders(request):
    """List production orders"""
    try:
        filters = {
            'order_type': request.GET.get('order_type'),
            'status': request.GET.get('status'),
            'warehouse_id': request.GET.get('warehouse_id'),
            'product_id': request.GET.get('product_id'),
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
            'search': request.GET.get('search'),
        }
        
        orders = production_service.production_repo.list_production_orders(filters)
        serializer = ProductionOrderListSerializer(orders, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': orders.count()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def get_production_order(request, pk):
    """Get production order details"""
    try:
        order = production_service.production_repo.get_production_order_by_id(pk)
        serializer = ProductionOrderDetailSerializer(order)
        
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


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsManager])
def delete_production_order(request, pk):
    """Delete production order"""
    try:
        production_service.production_repo.delete_production_order(pk)
        
        return Response({
            'success': True,
            'message': 'Production order deleted successfully'
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


# ==================== Assembly Endpoints ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_assembly_order(request):
    """Create assembly/production order"""
    try:
        serializer = AssemblyOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = production_service.create_assembly_order(
            data=serializer.validated_data,
            user=request.user
        )
        
        result_serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Assembly order created successfully',
            'data': result_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e) if isinstance(str(e), str) else e.args[0]
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def confirm_assembly_order(request, pk):
    """Confirm assembly order and reserve stock"""
    try:
        order = production_service.confirm_assembly_order(pk, request.user)
        serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Assembly order confirmed and stock reserved',
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
def start_assembly_order(request, pk):
    """Start assembly process"""
    try:
        order = production_service.start_assembly_order(pk, request.user)
        serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Assembly order started',
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
def complete_assembly_order(request, pk):
    """Complete assembly and update inventory"""
    try:
        serializer = CompleteAssemblySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = production_service.complete_assembly_order(
            order_id=pk,
            actual_quantity=serializer.validated_data['actual_quantity'],
            actual_components=serializer.validated_data['actual_components'],
            user=request.user
        )
        
        result_serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Assembly completed successfully',
            'data': result_serializer.data
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


# ==================== Disassembly Endpoints ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def create_disassembly_order(request):
    """Create disassembly order"""
    try:
        serializer = DisassemblyOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = production_service.create_disassembly_order(
            data=serializer.validated_data,
            user=request.user
        )
        
        result_serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Disassembly order created successfully',
            'data': result_serializer.data
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


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def start_disassembly_order(request, pk):
    """Start disassembly process"""
    try:
        order = production_service.start_assembly_order(pk, request.user)  # Same logic
        serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Disassembly order started',
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
def complete_disassembly_order(request, pk):
    """Complete disassembly and return components"""
    try:
        serializer = CompleteDisassemblySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = production_service.complete_disassembly_order(
            order_id=pk,
            actual_components=serializer.validated_data['actual_components'],
            user=request.user
        )
        
        result_serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Disassembly completed successfully',
            'data': result_serializer.data
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


# ==================== Other Endpoints ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManager])
def cancel_production_order(request, pk):
    """Cancel production order"""
    try:
        order = production_service.cancel_production_order(pk, request.user)
        serializer = ProductionOrderDetailSerializer(order)
        
        return Response({
            'success': True,
            'message': 'Production order cancelled',
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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def get_production_statistics(request):
    """Get production statistics"""
    try:
        filters = {
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
        }
        
        stats = production_service.get_production_statistics(filters)
        
        return Response({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManager | IsAccountant])
def get_production_history(request, product_id):
    """Get production history for a product"""
    try:
        limit = int(request.GET.get('limit', 10))
        history = production_service.get_production_history(product_id, limit)
        serializer = ProductionOrderListSerializer(history, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)