"""
Order Service - Complete Business Logic Layer
Handles sales and purchase orders with invoice conversion
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from layers.repositories.order_repository import OrderRepository, OrderItemRepository
from layers.repositories.contact_repository import ContactRepository
from layers.repositories.product_repository import ProductRepository
from layers.repositories.warehouse_repository import WarehouseRepository
from layers.models.order_models import Order, OrderItem, OrderStatusHistory
from core.exceptions import (
    ValidationError,
    NotFoundError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order operations"""
    
    def __init__(self):
        self.order_repo = OrderRepository()
        self.contact_repo = ContactRepository()
        self.product_repo = ProductRepository()
        self.warehouse_repo = WarehouseRepository()
    
    @transaction.atomic
    def create_order(self, order_data, items_data, user):
        """
        Create a new order
        
        Args:
            order_data (dict): Order data
            items_data (list): List of order items
            user: User creating the order
            
        Returns:
            Order: Created order
        """
        try:
            # Validate order type
            order_type = order_data.get('order_type', '').lower()
            if order_type not in ['sales', 'purchase']:
                raise ValidationError(f"Invalid order type: {order_type}")
            
            # Validate items
            if not items_data or len(items_data) == 0:
                raise ValidationError("Order must have at least one item")
            
            # Validate contact
            contact_id = order_data.get('contact_id') or order_data.get('contact')
            if not contact_id:
                raise ValidationError("Contact is required")
            
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact {contact_id} not found")
            
            # Validate contact type
            if order_type == 'sales' and not contact.is_customer:
                raise ValidationError(f"{contact.name} is not a customer")
            elif order_type == 'purchase' and not contact.is_supplier:
                raise ValidationError(f"{contact.name} is not a supplier")
            
            # Generate order number
            prefix = 'SO' if order_type == 'sales' else 'PO'
            year = timezone.now().year
            last_order = Order.objects.filter(
                order_number__startswith=f'{prefix}-{year}'
            ).order_by('-order_number').first()
            
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            order_data['order_number'] = f'{prefix}-{year}-{next_num:05d}'
            order_data['contact_id'] = contact_id
            
            # Create order
            order = self.order_repo.create_order(order_data, items_data, user)
            
            logger.info(f"Order {order.order_number} created by {user.username}")
            return order
            
        except (ValidationError, NotFoundError) as e:
            logger.warning(f"Order creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create order: {str(e)}")
    
    @transaction.atomic
    def update_order(self, order_id, data):
        """Update an order"""
        try:
            return self.order_repo.update_order(order_id, data)
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Order update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update order: {str(e)}")
    
    @transaction.atomic
    def delete_order(self, order_id):
        """Delete an order"""
        try:
            return self.order_repo.delete_order(order_id)
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Order deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete order: {str(e)}")
    
    @transaction.atomic
    def update_status(self, order_id, new_status, notes=None, user=None):
        """Update order status"""
        try:
            return self.order_repo.update_status(order_id, new_status, notes, user)
        except NotFoundError as e:
            logger.warning(f"Status update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating status: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update status: {str(e)}")
    
    @transaction.atomic
    def confirm_order(self, order_id, user):
        """Confirm an order"""
        try:
            order = self.order_repo.get_by_id(order_id)
            
            if order.status != 'draft':
                raise ValidationError(f"Cannot confirm order with status {order.status}")
            
            return self.order_repo.update_status(
                order_id, 'confirmed', 
                'Order confirmed', user
            )
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Order confirmation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error confirming order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to confirm order: {str(e)}")
    
    @transaction.atomic
    def cancel_order(self, order_id, reason, user):
        """Cancel an order"""
        try:
            order = self.order_repo.get_by_id(order_id)
            
            if order.is_converted_to_invoice:
                raise ValidationError("Cannot cancel order that has been converted to invoice")
            
            return self.order_repo.update_status(
                order_id, 'cancelled', 
                reason, user
            )
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Order cancellation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to cancel order: {str(e)}")
    
    @transaction.atomic
    def convert_to_invoice(self, order_id, user):
        """
        Convert order to invoice
        
        Args:
            order_id (int): Order ID
            user: User converting the order
            
        Returns:
            Invoice: Created invoice
        """
        try:
            from layers.models import Invoice, InvoiceItem
            
            order = self.order_repo.get_by_id(order_id)
            
            # Validate conversion
            if not order.can_be_converted:
                raise ValidationError(
                    "Order cannot be converted. Check status and conversion flag."
                )
            
            # Create invoice
            invoice_type = 'SALES' if order.is_sales_order else 'PURCHASE'
            
            invoice_data = {
                'invoice_type': invoice_type,
                'contact_id': order.contact_id,
                'warehouse_id': order.warehouse_id,
                'invoice_date': timezone.now().date(),
                'due_date': timezone.now().date() + timezone.timedelta(days=30),
                'payment_terms': 'NET_30',
                'reference_number': order.order_number,
                'created_by_id': user.id,
            }
            
            # Generate invoice number
            from layers.repositories.invoice_repository import InvoiceRepository
            invoice_repo = InvoiceRepository()
            invoice_data['invoice_number'] = invoice_repo.generate_invoice_number(
                invoice_type, invoice_data['invoice_date']
            )
            
            invoice = Invoice.objects.create(**invoice_data)
            
            # Create invoice items from order items
            for order_item in order.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=order_item.product,
                    description=order_item.product_name,
                    quantity=order_item.quantity,
                    unit_price=order_item.unit_price,
                    discount_percentage=order_item.discount_percentage,
                    tax_percentage=order_item.tax_percentage,
                )
            
            # Calculate invoice totals
            invoice.calculate_totals()
            invoice.save()
            
            # Update order
            order.is_converted_to_invoice = True
            order.invoice = invoice
            order.save()
            
            logger.info(
                f"Order {order.order_number} converted to invoice {invoice.invoice_number}"
            )
            
            return invoice
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Order conversion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to convert order: {str(e)}")
    
    # Query methods
    
    @staticmethod
    def get_all_orders(order_type=None, status=None, contact_id=None, search=None):
        """Get all orders with filters"""
        return OrderRepository.get_all_orders(order_type, status, contact_id, search)
    
    @staticmethod
    def get_sales_orders(status=None, search=None):
        """Get sales orders"""
        return OrderRepository.get_sales_orders(status, search)
    
    @staticmethod
    def get_purchase_orders(status=None, search=None):
        """Get purchase orders"""
        return OrderRepository.get_purchase_orders(status, search)
    
    @staticmethod
    def get_order_by_id(order_id):
        """Get order by ID"""
        return OrderRepository.get_by_id(order_id)
    
    @staticmethod
    def get_statistics(order_type=None):
        """Get order statistics"""
        return OrderRepository.get_statistics(order_type)


class OrderItemService:
    """Service for order item operations"""
    
    @staticmethod
    @transaction.atomic
    def add_item(order_id, item_data):
        """Add item to order"""
        try:
            item_data['order_id'] = order_id
            return OrderItemRepository.create_item(item_data)
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Add item failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding item: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to add item: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def update_item(item_id, item_data):
        """Update order item"""
        try:
            return OrderItemRepository.update_item(item_id, item_data)
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Update item failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating item: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update item: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def remove_item(item_id):
        """Remove order item"""
        try:
            return OrderItemRepository.delete_item(item_id)
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Remove item failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error removing item: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to remove item: {str(e)}")