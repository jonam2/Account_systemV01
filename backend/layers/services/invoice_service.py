"""
Invoice Service - Complete Business Logic Layer
Handles all invoice-related operations with proper transaction management
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import logging

from layers.repositories.invoice_repository import (
    InvoiceRepository,
    InvoiceItemRepository,
    InvoicePaymentRepository
)
from layers.repositories.warehouse_repository import StockRepository, StockMovementRepository
from layers.repositories.contact_repository import ContactRepository
from layers.models.warehouse_models import StockMovement
from core.exceptions import (
    ValidationError,
    NotFoundError,
    InsufficientStockError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Service for invoice operations
    Handles invoice creation, approval, payments, and inventory updates
    """
    
    def __init__(self):
        self.invoice_repo = InvoiceRepository()
        self.item_repo = InvoiceItemRepository()
        self.payment_repo = InvoicePaymentRepository()
        self.stock_repo = StockRepository()
        self.movement_repo = StockMovementRepository()
        self.contact_repo = ContactRepository()
    
    @transaction.atomic
    def create_invoice(self, invoice_data, items_data, user_id):
        """
        Create a new invoice with items
        
        Args:
            invoice_data (dict): Invoice data
            items_data (list): List of invoice items
            user_id (int): User creating the invoice
            
        Returns:
            Invoice: Created invoice
            
        Raises:
            ValidationError: If data is invalid
        """
        try:
            # Validate invoice type
            invoice_type = invoice_data.get('invoice_type', '').upper()
            if invoice_type not in ['SALES', 'PURCHASE']:
                raise ValidationError(f"Invalid invoice type: {invoice_type}")
            
            # Validate items
            if not items_data or len(items_data) == 0:
                raise ValidationError("Invoice must have at least one item")
            
            # Validate contact
            contact_id = invoice_data.get('contact_id') or invoice_data.get('contact')
            if not contact_id:
                raise ValidationError("Contact is required")
            
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact {contact_id} not found")
            
            # Validate contact type matches invoice type
            if invoice_type == 'SALES' and not contact.is_customer:
                raise ValidationError(f"{contact.name} is not a customer")
            elif invoice_type == 'PURCHASE' and not contact.is_supplier:
                raise ValidationError(f"{contact.name} is not a supplier")
            
            # Generate invoice number
            invoice_data['invoice_number'] = self.invoice_repo.generate_invoice_number(
                invoice_type,
                invoice_data.get('invoice_date') or timezone.now().date()
            )
            
            # Set created_by
            invoice_data['created_by_id'] = user_id
            invoice_data['contact_id'] = contact_id
            
            # Create invoice
            invoice = self.invoice_repo.create(invoice_data)
            logger.info(f"Invoice {invoice.invoice_number} created by user {user_id}")
            
            # Create invoice items
            for item_data in items_data:
                item_data['invoice_id'] = invoice.id
                
                # Validate product exists
                product_id = item_data.get('product_id') or item_data.get('product')
                if not product_id:
                    raise ValidationError("Product is required for invoice item")
                
                # Auto-fill description if not provided
                if not item_data.get('description'):
                    from layers.models import Product
                    product = Product.objects.filter(id=product_id).first()
                    if product:
                        item_data['description'] = product.description or product.name
                
                item = self.item_repo.create(item_data)
                logger.debug(f"Invoice item created: {item}")
            
            # Calculate totals
            invoice.calculate_totals()
            invoice.update_status()
            invoice.save()
            
            logger.info(
                f"Invoice {invoice.invoice_number} created successfully. "
                f"Total: {invoice.total_amount}"
            )
            
            return invoice
            
        except (ValidationError, NotFoundError) as e:
            logger.warning(f"Invoice creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating invoice: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create invoice: {str(e)}")
    
    @transaction.atomic
    def update_invoice(self, invoice_id, invoice_data, items_data=None):
        """
        Update an existing invoice
        
        Args:
            invoice_id (int): Invoice ID
            invoice_data (dict): Updated invoice data
            items_data (list): Updated items (optional)
            
        Returns:
            Invoice: Updated invoice
        """
        try:
            invoice = self.invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise NotFoundError(f"Invoice {invoice_id} not found")
            
            # Cannot update approved or paid invoices
            if invoice.status in ['APPROVED', 'PAID', 'CANCELLED']:
                raise BusinessLogicError(
                    f"Cannot update invoice with status {invoice.status}"
                )
            
            # Update invoice fields
            for key, value in invoice_data.items():
                if key not in ['id', 'invoice_number', 'created_by', 'created_at']:
                    setattr(invoice, key, value)
            
            # Update items if provided
            if items_data is not None:
                # Delete existing items
                self.item_repo.delete_by_invoice(invoice_id)
                
                # Create new items
                for item_data in items_data:
                    item_data['invoice_id'] = invoice_id
                    self.item_repo.create(item_data)
            
            # Recalculate totals
            invoice.calculate_totals()
            invoice.update_status()
            invoice.save()
            
            logger.info(f"Invoice {invoice.invoice_number} updated successfully")
            return invoice
            
        except (ValidationError, NotFoundError, BusinessLogicError) as e:
            logger.warning(f"Invoice update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating invoice: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update invoice: {str(e)}")
    
    @transaction.atomic
    def approve_invoice(self, invoice_id, user_id):
        """
        Approve invoice and update inventory
        
        Args:
            invoice_id (int): Invoice ID
            user_id (int): User approving the invoice
            
        Returns:
            Invoice: Approved invoice
        """
        try:
            invoice = self.invoice_repo.get_with_details(invoice_id)
            if not invoice:
                raise NotFoundError(f"Invoice {invoice_id} not found")
            
            # Validate status
            if invoice.status not in ['DRAFT', 'PENDING']:
                raise BusinessLogicError(
                    f"Cannot approve invoice with status {invoice.status}"
                )
            
            # Check if already updated inventory
            if invoice.inventory_updated:
                raise BusinessLogicError("Invoice inventory already updated")
            
            # For sales invoices, check stock availability
            if invoice.invoice_type == 'SALES':
                for item in invoice.items.all():
                    stock = self.stock_repo.get_stock(
                        invoice.warehouse_id,
                        item.product_id
                    )
                    
                    if not stock or stock.available_quantity < item.quantity:
                        available = stock.available_quantity if stock else 0
                        raise InsufficientStockError(
                            f"Insufficient stock for {item.product.name}. "
                            f"Required: {item.quantity}, Available: {available}"
                        )
            
            # Update inventory
            self._update_inventory(invoice, user_id)
            
            # Update invoice status
            invoice.status = 'APPROVED'
            invoice.approved_by_id = user_id
            invoice.approved_date = timezone.now()
            invoice.inventory_updated = True
            invoice.save()
            
            # Update contact balance
            if invoice.invoice_type == 'SALES':
                # Increase customer receivable
                invoice.contact.update_balance(invoice.total_amount)
            else:
                # Increase supplier payable (negative balance)
                invoice.contact.update_balance(-invoice.total_amount)
            
            logger.info(
                f"Invoice {invoice.invoice_number} approved by user {user_id}. "
                f"Inventory updated."
            )
            
            return invoice
            
        except (NotFoundError, BusinessLogicError, InsufficientStockError) as e:
            logger.warning(f"Invoice approval failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error approving invoice: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to approve invoice: {str(e)}")
    
    @transaction.atomic
    def cancel_invoice(self, invoice_id):
        """
        Cancel invoice and reverse inventory changes
        
        Args:
            invoice_id (int): Invoice ID
            
        Returns:
            Invoice: Cancelled invoice
        """
        try:
            invoice = self.invoice_repo.get_with_details(invoice_id)
            if not invoice:
                raise NotFoundError(f"Invoice {invoice_id} not found")
            
            # Cannot cancel paid invoices
            if invoice.status == 'PAID':
                raise BusinessLogicError("Cannot cancel a paid invoice")
            
            # Reverse inventory if it was updated
            if invoice.inventory_updated:
                self._reverse_inventory(invoice)
            
            # Reverse contact balance
            if invoice.invoice_type == 'SALES':
                invoice.contact.update_balance(-invoice.total_amount)
            else:
                invoice.contact.update_balance(invoice.total_amount)
            
            # Update status
            invoice.status = 'CANCELLED'
            invoice.save()
            
            logger.info(f"Invoice {invoice.invoice_number} cancelled")
            return invoice
            
        except (NotFoundError, BusinessLogicError) as e:
            logger.warning(f"Invoice cancellation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling invoice: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to cancel invoice: {str(e)}")
    
    @transaction.atomic
    def add_payment(self, invoice_id, payment_data, user_id):
        """
        Add payment to invoice
        
        Args:
            invoice_id (int): Invoice ID
            payment_data (dict): Payment data
            user_id (int): User recording the payment
            
        Returns:
            InvoicePayment: Created payment
        """
        try:
            invoice = self.invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise NotFoundError(f"Invoice {invoice_id} not found")
            
            # Validate invoice status
            if invoice.status == 'CANCELLED':
                raise BusinessLogicError("Cannot add payment to cancelled invoice")
            
            # Validate payment amount
            amount = payment_data.get('amount', 0)
            if amount <= 0:
                raise ValidationError("Payment amount must be positive")
            
            remaining = invoice.balance_due
            if amount > remaining:
                raise ValidationError(
                    f"Payment amount ({amount}) exceeds remaining balance ({remaining})"
                )
            
            # Create payment
            payment_data['invoice_id'] = invoice_id
            payment_data['recorded_by_id'] = user_id
            payment = self.payment_repo.create(payment_data)
            
            # Update invoice paid amount and status
            invoice.paid_amount += amount
            invoice.balance_due = invoice.total_amount - invoice.paid_amount
            invoice.update_status()
            
            if invoice.status == 'PAID':
                invoice.payment_date = payment.payment_date
            
            invoice.save()
            
            # Update contact balance
            if invoice.invoice_type == 'SALES':
                # Decrease customer receivable
                invoice.contact.update_balance(-amount)
            else:
                # Decrease supplier payable
                invoice.contact.update_balance(amount)
            
            logger.info(
                f"Payment of {amount} added to invoice {invoice.invoice_number}. "
                f"New status: {invoice.status}"
            )
            
            return payment
            
        except (NotFoundError, ValidationError, BusinessLogicError) as e:
            logger.warning(f"Payment addition failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding payment: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to add payment: {str(e)}")
    
    @transaction.atomic
    def delete_payment(self, payment_id):
        """
        Delete a payment and update invoice
        
        Args:
            payment_id (int): Payment ID
            
        Returns:
            bool: Success status
        """
        try:
            payment = self.payment_repo.get_by_id(payment_id)
            if not payment:
                raise NotFoundError(f"Payment {payment_id} not found")
            
            invoice = payment.invoice
            
            # Cannot delete if invoice is already paid
            if invoice.status == 'PAID' and invoice.paid_amount == invoice.total_amount:
                raise BusinessLogicError(
                    "Cannot delete payment from fully paid invoice"
                )
            
            amount = payment.amount
            
            # Delete payment
            payment.delete()
            
            # Update invoice
            invoice.paid_amount = max(Decimal('0.00'), invoice.paid_amount - amount)
            invoice.balance_due = invoice.total_amount - invoice.paid_amount
            invoice.update_status()
            invoice.save()
            
            # Update contact balance
            if invoice.invoice_type == 'SALES':
                invoice.contact.update_balance(amount)
            else:
                invoice.contact.update_balance(-amount)
            
            logger.info(f"Payment {payment_id} deleted from invoice {invoice.invoice_number}")
            return True
            
        except (NotFoundError, BusinessLogicError) as e:
            logger.warning(f"Payment deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting payment: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete payment: {str(e)}")
    
    def list_invoices(self, invoice_type, filters=None, page=1, page_size=20):
        """
        List invoices with filters and pagination
        
        Args:
            invoice_type (str): SALES or PURCHASE
            filters (dict): Filter parameters
            page (int): Page number
            page_size (int): Items per page
            
        Returns:
            dict: Paginated invoice list
        """
        try:
            queryset = self.invoice_repo.filter_by_type(invoice_type, filters)
            
            # Count total
            total_count = queryset.count()
            
            # Calculate pagination
            offset = (page - 1) * page_size
            invoices = queryset[offset:offset + page_size]
            
            return {
                'invoices': invoices,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Error listing invoices: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to list invoices: {str(e)}")
    
    def get_invoice_with_details(self, invoice_id):
        """Get invoice with all related data"""
        invoice = self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")
        return invoice
    
    def get_overdue_invoices(self, invoice_type=None):
        """Get overdue invoices"""
        return self.invoice_repo.get_overdue_invoices(invoice_type)
    
    def get_dashboard_stats(self, invoice_type, period_days=30):
        """Get invoice statistics for dashboard"""
        return self.invoice_repo.get_statistics(invoice_type, period_days)
    
    def get_contact_invoice_summary(self, contact_id, invoice_type):
        """Get invoice summary for a contact"""
        try:
            invoices = self.invoice_repo.get_invoices_by_contact(contact_id, invoice_type)
            
            from django.db.models import Sum, Count
            summary = invoices.aggregate(
                total_invoices=Count('id'),
                total_amount=Sum('total_amount'),
                total_paid=Sum('paid_amount'),
                pending_amount=Sum('balance_due')
            )
            
            return {
                'contact_id': contact_id,
                'invoice_type': invoice_type,
                'total_invoices': summary['total_invoices'] or 0,
                'total_amount': summary['total_amount'] or Decimal('0.00'),
                'total_paid': summary['total_paid'] or Decimal('0.00'),
                'pending_amount': summary['pending_amount'] or Decimal('0.00'),
            }
            
        except Exception as e:
            logger.error(f"Error getting contact summary: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get contact summary: {str(e)}")
    
    # Private helper methods
    
    def _update_inventory(self, invoice, user_id):
        """Update inventory based on invoice type"""
        for item in invoice.items.all():
            if invoice.invoice_type == 'SALES':
                # Decrease stock (outgoing)
                quantity_change = -item.quantity
                movement_type = StockMovement.MovementType.OUT
            else:
                # Increase stock (incoming)
                quantity_change = item.quantity
                movement_type = StockMovement.MovementType.IN
            
            # Get or create stock
            stock, created = self.stock_repo.update_stock(
                invoice.warehouse_id,
                item.product_id,
                quantity_change
            )
            
            # Create stock movement record
            self.movement_repo.create_movement({
                'warehouse_id': invoice.warehouse_id,
                'product_id': item.product_id,
                'movement_type': movement_type,
                'quantity': quantity_change,
                'quantity_before': stock.quantity - quantity_change,
                'quantity_after': stock.quantity,
                'reference_type': 'invoice',
                'reference_id': invoice.id,
                'reference_number': invoice.invoice_number,
                'notes': f'{invoice.get_invoice_type_display()} - {invoice.invoice_number}',
                'created_by_id': user_id
            })
    
    def _reverse_inventory(self, invoice):
        """Reverse inventory changes"""
        for item in invoice.items.all():
            if invoice.invoice_type == 'SALES':
                # Add back stock
                quantity_change = item.quantity
            else:
                # Remove stock
                quantity_change = -item.quantity
            
            # Update stock
            self.stock_repo.update_stock(
                invoice.warehouse_id,
                item.product_id,
                quantity_change
            )
            
            # Create reversal movement record
            self.movement_repo.create_movement({
                'warehouse_id': invoice.warehouse_id,
                'product_id': item.product_id,
                'movement_type': StockMovement.MovementType.ADJUSTMENT,
                'quantity': quantity_change,
                'reference_type': 'invoice_reversal',
                'reference_id': invoice.id,
                'reference_number': invoice.invoice_number,
                'notes': f'Reversal: {invoice.invoice_number} cancelled',
                'created_by_id': invoice.created_by_id
            })