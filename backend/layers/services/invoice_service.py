"""
Invoice Service - Business Logic Layer
Handles all invoice-related business operations
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from layers.repositories.invoice_repository import (
    InvoiceRepository,
    InvoiceItemRepository,
    InvoicePaymentRepository
)
from layers.repositories.product_repository import ProductRepository
from layers.repositories.warehouse_repository import StockRepository
from layers.models.invoice_models import Invoice, InvoiceItem, InvoicePayment


class InvoiceService:
    """Service for invoice business logic"""
    
    def __init__(self):
        self.invoice_repo = InvoiceRepository()
        self.item_repo = InvoiceItemRepository()
        self.payment_repo = InvoicePaymentRepository()
        self.product_repo = ProductRepository()
        self.stock_repo = StockRepository()
    
    @transaction.atomic
    def create_invoice(
        self,
        invoice_data: Dict[str, Any],
        items_data: List[Dict[str, Any]],
        user_id: int
    ) -> Invoice:
        """
        Create a new invoice with items
        
        Args:
            invoice_data: Invoice information
            items_data: List of invoice items
            user_id: User creating the invoice
        
        Returns:
            Created Invoice instance
        """
        # Validate invoice type
        if invoice_data['invoice_type'] not in ['SALES', 'PURCHASE']:
            raise ValidationError("Invalid invoice type")
        
        # Validate contact type matches invoice type
        contact = invoice_data.get('contact')
        if invoice_data['invoice_type'] == 'SALES' and contact.contact_type != 'CUSTOMER':
            raise ValidationError("Sales invoices require a customer")
        if invoice_data['invoice_type'] == 'PURCHASE' and contact.contact_type != 'SUPPLIER':
            raise ValidationError("Purchase invoices require a supplier")
        
        # Generate invoice number
        invoice_data['invoice_number'] = self.invoice_repo.generate_invoice_number(
            invoice_data['invoice_type'],
            invoice_data.get('invoice_date', timezone.now().date())
        )
        
        # Set created_by
        invoice_data['created_by_id'] = user_id
        
        # Calculate due date if not provided
        if 'due_date' not in invoice_data:
            invoice_data['due_date'] = self._calculate_due_date(
                invoice_data.get('invoice_date', timezone.now().date()),
                invoice_data.get('payment_terms', 'NET_30')
            )
        
        # Create invoice
        invoice = self.invoice_repo.create(invoice_data)
        
        # Create invoice items
        for idx, item_data in enumerate(items_data):
            item_data['invoice_id'] = invoice.id
            item_data['sort_order'] = idx
            
            # Validate product exists
            product = self.product_repo.get_by_id(item_data['product_id'])
            if not product:
                raise ValidationError(f"Product {item_data['product_id']} not found")
            
            # Auto-fill unit price if not provided
            if 'unit_price' not in item_data or item_data['unit_price'] is None:
                if invoice_data['invoice_type'] == 'SALES':
                    item_data['unit_price'] = product.selling_price
                else:
                    item_data['unit_price'] = product.cost_price
            
            self.item_repo.create(item_data)
        
        # Calculate totals
        invoice.calculate_totals()
        self.invoice_repo.update(invoice.id, {
            'subtotal': invoice.subtotal,
            'discount_amount': invoice.discount_amount,
            'tax_amount': invoice.tax_amount,
            'total_amount': invoice.total_amount,
            'balance_due': invoice.balance_due
        })
        
        return self.invoice_repo.get_with_details(invoice.id)
    
    @transaction.atomic
    def update_invoice(
        self,
        invoice_id: int,
        invoice_data: Dict[str, Any],
        items_data: Optional[List[Dict[str, Any]]] = None
    ) -> Invoice:
        """
        Update an existing invoice
        
        Args:
            invoice_id: Invoice ID
            invoice_data: Updated invoice data
            items_data: Optional updated items list
        """
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise ValidationError("Invoice not found")
        
        # Prevent editing approved/paid invoices
        if invoice.status in ['PAID', 'APPROVED'] and invoice.inventory_updated:
            raise ValidationError("Cannot edit approved or paid invoices with inventory updates")
        
        # Update invoice
        self.invoice_repo.update(invoice_id, invoice_data)
        
        # Update items if provided
        if items_data is not None:
            # Delete existing items
            self.item_repo.delete_by_invoice(invoice_id)
            
            # Create new items
            for idx, item_data in enumerate(items_data):
                item_data['invoice_id'] = invoice_id
                item_data['sort_order'] = idx
                
                # Validate product
                product = self.product_repo.get_by_id(item_data['product_id'])
                if not product:
                    raise ValidationError(f"Product {item_data['product_id']} not found")
                
                self.item_repo.create(item_data)
        
        # Recalculate totals
        invoice = self.invoice_repo.get_by_id(invoice_id)
        invoice.calculate_totals()
        self.invoice_repo.update(invoice_id, {
            'subtotal': invoice.subtotal,
            'discount_amount': invoice.discount_amount,
            'tax_amount': invoice.tax_amount,
            'total_amount': invoice.total_amount,
            'balance_due': invoice.balance_due
        })
        
        return self.invoice_repo.get_with_details(invoice_id)
    
    @transaction.atomic
    def approve_invoice(self, invoice_id: int, user_id: int) -> Invoice:
        """
        Approve an invoice and update inventory
        
        Args:
            invoice_id: Invoice ID
            user_id: User approving the invoice
        """
        invoice = self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise ValidationError("Invoice not found")
        
        if invoice.status != 'DRAFT' and invoice.status != 'PENDING':
            raise ValidationError("Only draft or pending invoices can be approved")
        
        # Update inventory based on invoice type
        if not invoice.inventory_updated:
            items = self.item_repo.get_by_invoice(invoice_id)
            
            for item in items:
                if invoice.invoice_type == 'SALES':
                    # Decrease stock for sales
                    self._decrease_stock(
                        product_id=item.product_id,
                        warehouse_id=invoice.warehouse_id,
                        quantity=item.quantity,
                        reference=f"Sales Invoice {invoice.invoice_number}"
                    )
                else:  # PURCHASE
                    # Increase stock for purchases
                    self._increase_stock(
                        product_id=item.product_id,
                        warehouse_id=invoice.warehouse_id,
                        quantity=item.quantity,
                        reference=f"Purchase Invoice {invoice.invoice_number}"
                    )
        
        # Update invoice
        self.invoice_repo.update(invoice_id, {
            'status': 'APPROVED',
            'approved_by_id': user_id,
            'approved_date': timezone.now(),
            'inventory_updated': True
        })
        
        return self.invoice_repo.get_with_details(invoice_id)
    
    @transaction.atomic
    def cancel_invoice(self, invoice_id: int) -> Invoice:
        """
        Cancel an invoice and reverse inventory changes
        
        Args:
            invoice_id: Invoice ID
        """
        invoice = self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise ValidationError("Invoice not found")
        
        if invoice.status == 'PAID':
            raise ValidationError("Cannot cancel paid invoices. Please refund first.")
        
        # Reverse inventory if it was updated
        if invoice.inventory_updated:
            items = self.item_repo.get_by_invoice(invoice_id)
            
            for item in items:
                if invoice.invoice_type == 'SALES':
                    # Restore stock for cancelled sales
                    self._increase_stock(
                        product_id=item.product_id,
                        warehouse_id=invoice.warehouse_id,
                        quantity=item.quantity,
                        reference=f"Cancelled Sales Invoice {invoice.invoice_number}"
                    )
                else:  # PURCHASE
                    # Remove stock for cancelled purchases
                    self._decrease_stock(
                        product_id=item.product_id,
                        warehouse_id=invoice.warehouse_id,
                        quantity=item.quantity,
                        reference=f"Cancelled Purchase Invoice {invoice.invoice_number}"
                    )
        
        # Update invoice
        self.invoice_repo.update(invoice_id, {
            'status': 'CANCELLED',
            'inventory_updated': False
        })
        
        return self.invoice_repo.get_with_details(invoice_id)
    
    @transaction.atomic
    def add_payment(
        self,
        invoice_id: int,
        payment_data: Dict[str, Any],
        user_id: int
    ) -> InvoicePayment:
        """
        Add a payment to an invoice
        
        Args:
            invoice_id: Invoice ID
            payment_data: Payment information
            user_id: User recording the payment
        """
        invoice = self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise ValidationError("Invoice not found")
        
        if invoice.status == 'CANCELLED':
            raise ValidationError("Cannot add payment to cancelled invoice")
        
        # Validate payment amount
        amount = payment_data['amount']
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        if amount > invoice.balance_due:
            raise ValidationError(
                f"Payment amount ({amount}) exceeds balance due ({invoice.balance_due})"
            )
        
        # Create payment
        payment_data['invoice_id'] = invoice_id
        payment_data['recorded_by_id'] = user_id
        payment = self.payment_repo.create(payment_data)
        
        # Update invoice paid amount and status
        new_paid_amount = invoice.paid_amount + amount
        new_balance = invoice.total_amount - new_paid_amount
        
        update_data = {
            'paid_amount': new_paid_amount,
            'balance_due': new_balance
        }
        
        if new_paid_amount >= invoice.total_amount:
            update_data['status'] = 'PAID'
            update_data['payment_date'] = payment_data['payment_date']
        else:
            update_data['status'] = 'PARTIALLY_PAID'
        
        self.invoice_repo.update(invoice_id, update_data)
        
        return payment
    
    def delete_payment(self, payment_id: int) -> bool:
        """
        Delete a payment and update invoice
        
        Args:
            payment_id: Payment ID
        """
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise ValidationError("Payment not found")
        
        invoice = self.invoice_repo.get_by_id(payment.invoice_id)
        
        # Update invoice amounts
        new_paid_amount = invoice.paid_amount - payment.amount
        new_balance = invoice.total_amount - new_paid_amount
        
        update_data = {
            'paid_amount': new_paid_amount,
            'balance_due': new_balance
        }
        
        if new_paid_amount <= 0:
            update_data['status'] = 'APPROVED'
            update_data['payment_date'] = None
        else:
            update_data['status'] = 'PARTIALLY_PAID'
        
        self.invoice_repo.update(invoice.id, update_data)
        
        # Delete payment
        return self.payment_repo.delete(payment_id)
    
    def get_invoice_with_details(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice with all related data"""
        return self.invoice_repo.get_with_details(invoice_id)
    
    def list_invoices(
        self,
        invoice_type: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        List invoices with pagination and filters
        
        Args:
            invoice_type: 'SALES' or 'PURCHASE'
            filters: Optional filters dict
            page: Page number
            page_size: Items per page
        """
        queryset = self.invoice_repo.filter_by_type(invoice_type, filters)
        
        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        invoices = list(queryset[start:end])
        
        return {
            'invoices': invoices,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
    
    def get_overdue_invoices(self, invoice_type: Optional[str] = None):
        """Get all overdue invoices"""
        return list(self.invoice_repo.get_overdue_invoices(invoice_type))
    
    def get_dashboard_stats(self, invoice_type: str, period_days: int = 30) -> Dict[str, Any]:
        """
        Get invoice statistics for dashboard
        
        Args:
            invoice_type: 'SALES' or 'PURCHASE'
            period_days: Number of days to analyze
        """
        stats = self.invoice_repo.get_statistics(invoice_type, period_days)
        
        # Add outstanding balance
        stats['outstanding_balance'] = self.invoice_repo.get_outstanding_balance(invoice_type)
        
        # Add overdue amount
        overdue_invoices = self.invoice_repo.get_overdue_invoices(invoice_type)
        overdue_amount = sum(inv.balance_due for inv in overdue_invoices)
        stats['overdue_amount'] = overdue_amount
        
        return stats
    
    def get_contact_invoice_summary(
        self,
        contact_id: int,
        invoice_type: str
    ) -> Dict[str, Any]:
        """
        Get invoice summary for a contact
        
        Args:
            contact_id: Contact ID
            invoice_type: 'SALES' or 'PURCHASE'
        """
        invoices = self.invoice_repo.get_invoices_by_contact(contact_id, invoice_type)
        
        total_invoiced = sum(inv.total_amount for inv in invoices)
        total_paid = sum(inv.paid_amount for inv in invoices)
        total_outstanding = sum(
            inv.balance_due for inv in invoices
            if inv.status in ['PENDING', 'APPROVED', 'PARTIALLY_PAID']
        )
        
        return {
            'total_invoices': invoices.count(),
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
            'invoices': list(invoices[:10])  # Recent 10
        }
    
    def _calculate_due_date(self, invoice_date: date, payment_terms: str) -> date:
        """Calculate due date based on payment terms"""
        days_map = {
            'IMMEDIATE': 0,
            'NET_15': 15,
            'NET_30': 30,
            'NET_45': 45,
            'NET_60': 60,
            'NET_90': 90,
        }
        
        days = days_map.get(payment_terms, 30)
        return invoice_date + timedelta(days=days)
    
    def _increase_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        reference: str
    ):
        """Increase stock for a product in a warehouse"""
        stock = self.stock_repo.get_stock(product_id, warehouse_id)
        
        if stock:
            self.stock_repo.update(stock.id, {
                'quantity': stock.quantity + quantity,
                'last_restocked': timezone.now().date()
            })
        else:
            # Create new stock entry
            self.stock_repo.create({
                'product_id': product_id,
                'warehouse_id': warehouse_id,
                'quantity': quantity,
                'last_restocked': timezone.now().date()
            })
    
    def _decrease_stock(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: Decimal,
        reference: str
    ):
        """Decrease stock for a product in a warehouse"""
        stock = self.stock_repo.get_stock(product_id, warehouse_id)
        
        if not stock:
            raise ValidationError(
                f"No stock found for product {product_id} in warehouse {warehouse_id}"
            )
        
        if stock.quantity < quantity:
            raise ValidationError(
                f"Insufficient stock. Available: {stock.quantity}, Required: {quantity}"
            )
        
        self.stock_repo.update(stock.id, {
            'quantity': stock.quantity - quantity
        })