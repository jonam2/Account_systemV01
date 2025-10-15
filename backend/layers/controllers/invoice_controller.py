"""
Invoice Controller - Presentation Layer
REST API endpoints for invoice operations
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from layers.services.invoice_service import InvoiceService
from layers.serializers.invoice_serializers import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateSerializer,
    InvoiceUpdateSerializer,
    InvoicePaymentSerializer,
    InvoicePaymentCreateSerializer,
    InvoiceStatsSerializer,
    ContactInvoiceSummarySerializer
)


# Initialize service
invoice_service = InvoiceService()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def invoice_list_create(request, invoice_type):
    """
    GET: List invoices (with filters)
    POST: Create new invoice
    
    invoice_type: 'sales' or 'purchase'
    """
    # Normalize invoice type
    invoice_type_upper = invoice_type.upper()
    if invoice_type_upper not in ['SALES', 'PURCHASE']:
        return Response(
            {'error': 'Invalid invoice type. Use "sales" or "purchase"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == 'GET':
        # Parse query parameters
        filters = {}
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        if request.query_params.get('contact_id'):
            filters['contact_id'] = int(request.query_params.get('contact_id'))
        if request.query_params.get('warehouse_id'):
            filters['warehouse_id'] = int(request.query_params.get('warehouse_id'))
        if request.query_params.get('date_from'):
            filters['date_from'] = request.query_params.get('date_from')
        if request.query_params.get('date_to'):
            filters['date_to'] = request.query_params.get('date_to')
        if request.query_params.get('search'):
            filters['search'] = request.query_params.get('search')
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        # Get invoices
        result = invoice_service.list_invoices(
            invoice_type=invoice_type_upper,
            filters=filters,
            page=page,
            page_size=page_size
        )
        
        serializer = InvoiceListSerializer(result['invoices'], many=True)
        
        return Response({
            'invoices': serializer.data,
            'pagination': {
                'total_count': result['total_count'],
                'page': result['page'],
                'page_size': result['page_size'],
                'total_pages': result['total_pages']
            }
        })
    
    elif request.method == 'POST':
        # Validate input
        serializer = InvoiceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Extract invoice and items data
            data = serializer.validated_data
            items_data = data.pop('items')
            
            # Ensure invoice type matches URL
            data['invoice_type'] = invoice_type_upper
            
            # Create invoice
            invoice = invoice_service.create_invoice(
                invoice_data=data,
                items_data=items_data,
                user_id=request.user.id
            )
            
            # Return created invoice
            response_serializer = InvoiceDetailSerializer(invoice)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def invoice_detail(request, invoice_id):
    """
    GET: Retrieve invoice details
    PUT: Update invoice
    DELETE: Soft delete invoice
    """
    if request.method == 'GET':
        try:
            invoice = invoice_service.get_invoice_with_details(invoice_id)
            if not invoice:
                return Response(
                    {'error': 'Invoice not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = InvoiceDetailSerializer(invoice)
            return Response(serializer.data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'PUT':
        serializer = InvoiceUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = serializer.validated_data
            items_data = data.pop('items', None)
            
            invoice = invoice_service.update_invoice(
                invoice_id=invoice_id,
                invoice_data=data,
                items_data=items_data
            )
            
            response_serializer = InvoiceDetailSerializer(invoice)
            return Response(response_serializer.data)
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'DELETE':
        try:
            # Soft delete using repository
            success = invoice_service.invoice_repo.delete(invoice_id)
            if success:
                return Response(
                    {'message': 'Invoice deleted successfully'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {'error': 'Invoice not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            return Response(
                {'error': f'Failed to delete invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invoice_approve(request, invoice_id):
    """
    POST: Approve an invoice and update inventory
    """
    try:
        invoice = invoice_service.approve_invoice(
            invoice_id=invoice_id,
            user_id=request.user.id
        )
        
        serializer = InvoiceDetailSerializer(invoice)
        return Response(serializer.data)
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to approve invoice: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invoice_cancel(request, invoice_id):
    """
    POST: Cancel an invoice and reverse inventory changes
    """
    try:
        invoice = invoice_service.cancel_invoice(invoice_id)
        
        serializer = InvoiceDetailSerializer(invoice)
        return Response(serializer.data)
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to cancel invoice: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def invoice_payments(request, invoice_id):
    """
    GET: List payments for an invoice
    POST: Add payment to invoice
    """
    if request.method == 'GET':
        try:
            payments = invoice_service.payment_repo.get_by_invoice(invoice_id)
            serializer = InvoicePaymentSerializer(payments, many=True)
            return Response(serializer.data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    elif request.method == 'POST':
        serializer = InvoicePaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payment = invoice_service.add_payment(
                invoice_id=invoice_id,
                payment_data=serializer.validated_data,
                user_id=request.user.id
            )
            
            response_serializer = InvoicePaymentSerializer(payment)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to add payment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def payment_delete(request, payment_id):
    """
    DELETE: Delete a payment
    """
    try:
        success = invoice_service.delete_payment(payment_id)
        if success:
            return Response(
                {'message': 'Payment deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to delete payment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_overdue(request, invoice_type):
    """
    GET: Get all overdue invoices
    
    invoice_type: 'sales', 'purchase', or 'all'
    """
    try:
        # Normalize invoice type
        if invoice_type.lower() == 'all':
            invoice_type_upper = None
        else:
            invoice_type_upper = invoice_type.upper()
            if invoice_type_upper not in ['SALES', 'PURCHASE']:
                return Response(
                    {'error': 'Invalid invoice type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        invoices = invoice_service.get_overdue_invoices(invoice_type_upper)
        serializer = InvoiceListSerializer(invoices, many=True)
        
        return Response({
            'count': len(invoices),
            'invoices': serializer.data
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_stats(request, invoice_type):
    """
    GET: Get invoice statistics
    
    invoice_type: 'sales' or 'purchase'
    """
    try:
        # Normalize invoice type
        invoice_type_upper = invoice_type.upper()
        if invoice_type_upper not in ['SALES', 'PURCHASE']:
            return Response(
                {'error': 'Invalid invoice type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get period from query params (default 30 days)
        period_days = int(request.query_params.get('period_days', 30))
        
        stats = invoice_service.get_dashboard_stats(
            invoice_type=invoice_type_upper,
            period_days=period_days
        )
        
        serializer = InvoiceStatsSerializer(stats)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contact_invoice_summary(request, contact_id, invoice_type):
    """
    GET: Get invoice summary for a contact
    
    invoice_type: 'sales' or 'purchase'
    """
    try:
        # Normalize invoice type
        invoice_type_upper = invoice_type.upper()
        if invoice_type_upper not in ['SALES', 'PURCHASE']:
            return Response(
                {'error': 'Invalid invoice type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        summary = invoice_service.get_contact_invoice_summary(
            contact_id=contact_id,
            invoice_type=invoice_type_upper
        )
        
        serializer = ContactInvoiceSummarySerializer(summary)
        return Response(serializer.data)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )