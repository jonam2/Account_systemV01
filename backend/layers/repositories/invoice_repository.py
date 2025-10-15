"""
Invoice Repository - Data Access Layer
Handles all database operations for invoices
"""
from typing import List, Optional, Dict, Any
from django.db.models import Q, Sum, Count, F, QuerySet
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from layers.repositories.base_repository import BaseRepository
from layers.models.invoice_models import Invoice, InvoiceItem, InvoicePayment


class InvoiceRepository(BaseRepository):
    """Repository for Invoice operations"""
    
    def __init__(self):
        super().__init__(Invoice)
    
    def get_with_details(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice with all related data"""
        return self.model.objects.select_related(
            'contact',
            'warehouse',
            'created_by',
            'approved_by'
        ).prefetch_related(
            'items__product',
            'payments'
        ).filter(id=invoice_id).first()
    
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number"""
        return self.model.objects.filter(
            invoice_number=invoice_number
        ).first()
    
    def filter_by_type(
        self,
        invoice_type: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> QuerySet:
        """
        Filter invoices by type with additional filters
        
        Args:
            invoice_type: 'SALES' or 'PURCHASE'
            filters: Optional dict with status, contact_id, date_from, date_to, etc.
        """
        queryset = self.model.objects.filter(invoice_type=invoice_type)
        
        if filters:
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            
            if 'contact_id' in filters:
                queryset = queryset.filter(contact_id=filters['contact_id'])
            
            if 'warehouse_id' in filters:
                queryset = queryset.filter(warehouse_id=filters['warehouse_id'])
            
            if 'date_from' in filters:
                queryset = queryset.filter(invoice_date__gte=filters['date_from'])
            
            if 'date_to' in filters:
                queryset = queryset.filter(invoice_date__lte=filters['date_to'])
            
            if 'search' in filters:
                search_term = filters['search']
                queryset = queryset.filter(
                    Q(invoice_number__icontains=search_term) |
                    Q(reference_number__icontains=search_term) |
                    Q(contact__name__icontains=search_term)
                )
        
        return queryset.select_related('contact', 'warehouse', 'created_by')
    
    def get_overdue_invoices(self, invoice_type: Optional[str] = None) -> QuerySet:
        """Get all overdue invoices"""
        today = timezone.now().date()
        queryset = self.model.objects.filter(
            due_date__lt=today,
            status__in=['PENDING', 'APPROVED', 'PARTIALLY_PAID']
        )
        
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        return queryset.select_related('contact')
    
    def get_pending_invoices(self, invoice_type: Optional[str] = None) -> QuerySet:
        """Get all pending/unpaid invoices"""
        queryset = self.model.objects.filter(
            status__in=['PENDING', 'APPROVED', 'PARTIALLY_PAID']
        )
        
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        return queryset.select_related('contact')
    
    def get_invoices_by_contact(
        self,
        contact_id: int,
        invoice_type: Optional[str] = None
    ) -> QuerySet:
        """Get all invoices for a specific contact"""
        queryset = self.model.objects.filter(contact_id=contact_id)
        
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        return queryset.order_by('-invoice_date')
    
    def get_invoices_by_date_range(
        self,
        start_date: date,
        end_date: date,
        invoice_type: Optional[str] = None
    ) -> QuerySet:
        """Get invoices within a date range"""
        queryset = self.model.objects.filter(
            invoice_date__range=[start_date, end_date]
        )
        
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        return queryset.select_related('contact')
    
    def generate_invoice_number(self, invoice_type: str, date: Optional[date] = None) -> str:
        """
        Generate unique invoice number
        Format: INV-SALES-2024-0001 or INV-PURCHASE-2024-0001
        """
        if date is None:
            date = timezone.now().date()
        
        prefix = f"INV-{invoice_type}-{date.year}"
        
        # Get last invoice number for this type and year
        last_invoice = self.model.objects.filter(
            invoice_type=invoice_type,
            invoice_number__startswith=prefix
        ).order_by('-invoice_number').first()
        
        if last_invoice:
            # Extract number and increment
            last_number = int(last_invoice.invoice_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}-{new_number:04d}"
    
    def calculate_total_revenue(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Calculate total revenue from sales invoices"""
        queryset = self.model.objects.filter(
            invoice_type='SALES',
            status__in=['APPROVED', 'PAID', 'PARTIALLY_PAID']
        )
        
        if start_date:
            queryset = queryset.filter(invoice_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(invoice_date__lte=end_date)
        
        result = queryset.aggregate(total=Sum('total_amount'))
        return result['total'] or Decimal('0.00')
    
    def calculate_total_expenses(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Calculate total expenses from purchase invoices"""
        queryset = self.model.objects.filter(
            invoice_type='PURCHASE',
            status__in=['APPROVED', 'PAID', 'PARTIALLY_PAID']
        )
        
        if start_date:
            queryset = queryset.filter(invoice_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(invoice_date__lte=end_date)
        
        result = queryset.aggregate(total=Sum('total_amount'))
        return result['total'] or Decimal('0.00')
    
    def get_outstanding_balance(self, invoice_type: Optional[str] = None) -> Decimal:
        """Get total outstanding balance"""
        queryset = self.model.objects.filter(
            status__in=['PENDING', 'APPROVED', 'PARTIALLY_PAID']
        )
        
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        result = queryset.aggregate(total=Sum('balance_due'))
        return result['total'] or Decimal('0.00')
    
    def get_statistics(self, invoice_type: str, period_days: int = 30) -> Dict[str, Any]:
        """Get invoice statistics for a period"""
        start_date = timezone.now().date() - timedelta(days=period_days)
        
        queryset = self.model.objects.filter(
            invoice_type=invoice_type,
            invoice_date__gte=start_date
        )
        
        stats = queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('total_amount'),
            paid_amount=Sum('paid_amount'),
            pending_count=Count('id', filter=Q(status__in=['PENDING', 'APPROVED'])),
            paid_count=Count('id', filter=Q(status='PAID')),
            overdue_count=Count('id', filter=Q(
                status__in=['PENDING', 'APPROVED', 'PARTIALLY_PAID'],
                due_date__lt=timezone.now().date()
            ))
        )
        
        return {
            'total_invoices': stats['total_count'] or 0,
            'total_amount': stats['total_amount'] or Decimal('0.00'),
            'total_paid': stats['paid_amount'] or Decimal('0.00'),
            'pending_invoices': stats['pending_count'] or 0,
            'paid_invoices': stats['paid_count'] or 0,
            'overdue_invoices': stats['overdue_count'] or 0,
        }


class InvoiceItemRepository(BaseRepository):
    """Repository for InvoiceItem operations"""
    
    def __init__(self):
        super().__init__(InvoiceItem)
    
    def get_by_invoice(self, invoice_id: int) -> QuerySet:
        """Get all items for an invoice"""
        return self.model.objects.filter(
            invoice_id=invoice_id
        ).select_related('product').order_by('sort_order')
    
    def bulk_create_items(self, items_data: List[Dict[str, Any]]) -> List[InvoiceItem]:
        """Bulk create invoice items"""
        items = [self.model(**item_data) for item_data in items_data]
        return self.model.objects.bulk_create(items)
    
    def delete_by_invoice(self, invoice_id: int) -> int:
        """Delete all items for an invoice"""
        return self.model.objects.filter(invoice_id=invoice_id).delete()[0]
    
    def get_product_sales_stats(
        self,
        product_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get sales statistics for a product"""
        queryset = self.model.objects.filter(
            product_id=product_id,
            invoice__invoice_type='SALES',
            invoice__status__in=['APPROVED', 'PAID', 'PARTIALLY_PAID']
        )
        
        if start_date:
            queryset = queryset.filter(invoice__invoice_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(invoice__invoice_date__lte=end_date)
        
        stats = queryset.aggregate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('line_total'),
            invoice_count=Count('invoice', distinct=True)
        )
        
        return {
            'total_quantity_sold': stats['total_quantity'] or Decimal('0.00'),
            'total_revenue': stats['total_revenue'] or Decimal('0.00'),
            'invoice_count': stats['invoice_count'] or 0,
        }


class InvoicePaymentRepository(BaseRepository):
    """Repository for InvoicePayment operations"""
    
    def __init__(self):
        super().__init__(InvoicePayment)
    
    def get_by_invoice(self, invoice_id: int) -> QuerySet:
        """Get all payments for an invoice"""
        return self.model.objects.filter(
            invoice_id=invoice_id
        ).select_related('recorded_by').order_by('-payment_date')
    
    def get_total_paid(self, invoice_id: int) -> Decimal:
        """Get total amount paid for an invoice"""
        result = self.model.objects.filter(
            invoice_id=invoice_id
        ).aggregate(total=Sum('amount'))
        
        return result['total'] or Decimal('0.00')
    
    def get_payments_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> QuerySet:
        """Get payments within a date range"""
        return self.model.objects.filter(
            payment_date__range=[start_date, end_date]
        ).select_related('invoice', 'recorded_by')
    
    def get_payments_by_method(self, payment_method: str) -> QuerySet:
        """Get payments by payment method"""
        return self.model.objects.filter(
            payment_method=payment_method
        ).select_related('invoice')
    
    def calculate_total_payments(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        payment_method: Optional[str] = None
    ) -> Decimal:
        """Calculate total payments"""
        queryset = self.model.objects.all()
        
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        result = queryset.aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')