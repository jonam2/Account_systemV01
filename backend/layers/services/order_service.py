"""Order service for business logic"""
from datetime import date
from decimal import Decimal
from layers.repositories.order_repository import OrderRepository, OrderItemRepository
from layers.repositories.contact_repository import ContactRepository
from layers.services.contact_service import ContactService
from core.exceptions import ValidationError


class OrderService:
    """Service layer for Order business logic"""

    @staticmethod
    def generate_order_number(order_type):
        """Generate unique order number"""
        from layers.models.order_models import Order
        
        today = date.today()
        prefix_map = {
            'sales': f"SO{today.strftime('%Y%m%d')}",
            'purchase': f"PO{today.strftime('%Y%m%d')}",
        }
        
        prefix = prefix_map.get(order_type, f"ORD{today.strftime('%Y%m%d')}")
        
        last_order = Order.objects.filter(
            order_number__startswith=prefix
        ).order_by('-order_number').first()
        
        if last_order:
            try:
                last_number = int(last_order.order_number.replace(prefix, ''))
                next_number = last_number + 1
            except ValueError:
                next_number = 1
        else:
            next_number = 1
        
        return f"{prefix}{next_number:04d}"

    @staticmethod
    def get_all_orders(order_type=None, status=None, contact_id=None, search=None):
        """Get all orders with filters"""
        return OrderRepository.get_all_orders(order_type, status, contact_id, search)

    @staticmethod
    def get_sales_orders(status=None, search=None):
        """Get all sales orders"""
        return OrderRepository.get_sales_orders(status, search)

    @staticmethod
    def get_purchase_orders(status=None, search=None):
        """Get all purchase orders"""
        return OrderRepository.get_purchase_orders(status, search)

    @staticmethod
    def get_order_by_id(order_id):
        """Get order by ID"""
        return OrderRepository.get_by_id(order_id)

    @staticmethod
    def create_order(data, items_data, user=None):
        """Create a new order with validation"""
        # Generate order number if not provided
        if 'order_number' not in data or not data['order_number']:
            data['order_number'] = OrderService.generate_order_number(data['order_type'])
        
        # Validate contact exists and type matches
        contact = ContactRepository.get_by_id(data['contact_id'])
        
        if data['order_type'] == 'sales':
            if contact.contact_type not in ['customer', 'both']:
                raise ValidationError("Contact must be a customer for sales orders")
        elif data['order_type'] == 'purchase':
            if contact.contact_type not in ['supplier', 'both']:
                raise ValidationError("Contact must be a supplier for purchase orders")
        
        # Validate items
        if not items_data or len(items_data) == 0:
            raise ValidationError("Order must have at least one item")
        
        # Check credit limit for sales orders
        if data['order_type'] == 'sales' and data.get('status') not in ['draft', 'cancelled']:
            # This will be enforced when converting to invoice
            pass
        
        # Create order
        order = OrderRepository.create_order(data, items_data, created_by=user)
        
        return order

    @staticmethod
    def update_order(order_id, data):
        """Update order with validation"""
        return OrderRepository.update_order(order_id, data)

    @staticmethod
    def delete_order(order_id):
        """Delete order"""
        return OrderRepository.delete_order(order_id)

    @staticmethod
    def update_status(order_id, new_status, notes=None, user=None):
        """Update order status with validation"""
        order = OrderRepository.get_by_id(order_id)
        
        # Validate status transition
        valid_transitions = {
            'draft': ['pending', 'cancelled'],
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['processing', 'cancelled'],
            'processing': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': [],
        }
        
        current_status = order.status
        
        if new_status not in valid_transitions.get(current_status, []):
            raise ValidationError(
                f"Cannot change status from {current_status} to {new_status}"
            )
        
        return OrderRepository.update_status(order_id, new_status, notes, user)

    @staticmethod
    def confirm_order(order_id, user=None):
        """Confirm an order"""
        return OrderService.update_status(order_id, 'confirmed', 'Order confirmed', user)

    @staticmethod
    def cancel_order(order_id, reason=None, user=None):
        """Cancel an order"""
        return OrderService.update_status(order_id, 'cancelled', reason, user)

    @staticmethod
    def complete_order(order_id, user=None):
        """Mark order as completed"""
        return OrderService.update_status(order_id, 'completed', 'Order completed', user)

    @staticmethod
    def convert_to_invoice(order_id, user=None):
        """Convert order to invoice"""
        from layers.services.invoice_service import InvoiceService
        
        order = OrderRepository.get_by_id(order_id)
        
        # Validate order can be converted
        if not order.can_be_converted:
            raise ValidationError(
                "Order cannot be converted. Check order status and conversion state."
            )
        
        # Check credit limit for sales orders
        if order.is_sales_order:
            try:
                ContactService.check_credit_limit(
                    order.contact_id,
                    order.total_amount
                )
            except ValidationError as e:
                raise ValidationError(f"Cannot convert order: {str(e)}")
        
        # Prepare invoice data
        invoice_data = {
            'invoice_type': 'sales' if order.is_sales_order else 'purchase',
            'contact_id': order.contact_id,
            'warehouse_id': order.warehouse_id,
            'invoice_date': date.today(),
            'due_date': date.today(),  # Can be calculated based on payment terms
            'currency': order.currency,
            'exchange_rate': order.exchange_rate,
            'discount_percentage': order.discount_percentage,
            'discount_amount': order.discount_amount,
            'tax_percentage': order.tax_percentage,
            'tax_amount': order.tax_amount,
            'shipping_cost': order.shipping_cost,
            'notes': f"Converted from Order: {order.order_number}\n{order.notes or ''}",
            'terms_and_conditions': order.terms_and_conditions,
            'reference_number': order.order_number,
        }
        
        # Prepare invoice items
        items_data = []
        for order_item in order.items.all():
            items_data.append({
                'product_id': order_item.product_id,
                'quantity': order_item.quantity,
                'unit_price': order_item.unit_price,
                'discount_percentage': order_item.discount_percentage,
                'discount_amount': order_item.discount_amount,
                'tax_percentage': order_item.tax_percentage,
                'tax_amount': order_item.tax_amount,
                'notes': order_item.notes,
            })
        
        # Create invoice
        invoice = InvoiceService.create_invoice(invoice_data, items_data, user=user)
        
        # Link invoice to order
        order.invoice = invoice
        order.is_converted_to_invoice = True
        order.save()
        
        # Update order status to completed if not already
        if order.status != 'completed':
            OrderService.update_status(order_id, 'completed', 'Converted to invoice', user)
        
        return invoice

    @staticmethod
    def get_statistics(order_type=None):
        """Get order statistics"""
        return OrderRepository.get_statistics(order_type)


class OrderItemService:
    """Service layer for OrderItem business logic"""

    @staticmethod
    def get_order_items(order_id):
        """Get all items for an order"""
        return OrderItemRepository.get_by_order(order_id)

    @staticmethod
    def add_item(order_id, item_data):
        """Add item to order"""
        order = OrderRepository.get_by_id(order_id)
        
        if order.is_converted_to_invoice:
            raise ValidationError("Cannot add items to converted order")
        
        if order.status in ['completed', 'cancelled']:
            raise ValidationError(f"Cannot add items to {order.status} order")
        
        item_data['order_id'] = order_id
        return OrderItemRepository.create_item(item_data)

    @staticmethod
    def update_item(item_id, item_data):
        """Update order item"""
        return OrderItemRepository.update_item(item_id, item_data)

    @staticmethod
    def remove_item(item_id):
        """Remove item from order"""
        return OrderItemRepository.delete_item(item_id)

    @staticmethod
    def update_fulfillment(item_id, quantity_fulfilled):
        """Update item fulfillment"""
        return OrderItemRepository.update_fulfillment(item_id, quantity_fulfilled)