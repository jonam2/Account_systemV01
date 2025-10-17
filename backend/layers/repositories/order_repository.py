"""Order repository for data access"""
from django.db.models import Q, Sum, Count, Avg, F
from layers.models.order_models import Order, OrderItem, OrderStatusHistory
from core.exceptions import NotFoundError, ValidationError


class OrderRepository:
    """Repository for Order operations"""

    @staticmethod
    def get_all_orders(order_type=None, status=None, contact_id=None, search=None):
        """Get all orders with optional filters"""
        queryset = Order.objects.select_related(
            'contact', 'warehouse', 'created_by', 'confirmed_by', 'invoice'
        ).prefetch_related('items__product')
        
        if order_type:
            queryset = queryset.filter(order_type=order_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(contact__name__icontains=search) |
                Q(contact__code__icontains=search)
            )
        
        return queryset

    @staticmethod
    def get_sales_orders(status=None, search=None):
        """Get all sales orders"""
        return OrderRepository.get_all_orders(
            order_type='sales',
            status=status,
            search=search
        )

    @staticmethod
    def get_purchase_orders(status=None, search=None):
        """Get all purchase orders"""
        return OrderRepository.get_all_orders(
            order_type='purchase',
            status=status,
            search=search
        )

    @staticmethod
    def get_by_id(order_id):
        """Get order by ID"""
        try:
            return Order.objects.select_related(
                'contact', 'warehouse', 'created_by', 'confirmed_by', 'invoice'
            ).prefetch_related(
                'items__product',
                'status_history__changed_by'
            ).get(id=order_id, is_deleted=False)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order with ID {order_id} not found")

    @staticmethod
    def get_by_order_number(order_number):
        """Get order by order number"""
        try:
            return Order.objects.get(order_number=order_number, is_deleted=False)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order with number {order_number} not found")

    @staticmethod
    def create_order(data, items_data, created_by=None):
        """Create a new order with items"""
        if created_by:
            data['created_by'] = created_by
        
        # Create order
        order = Order.objects.create(**data)
        
        # Create order items
        for item_data in items_data:
            item_data['order'] = order
            OrderItem.objects.create(**item_data)
        
        # Calculate totals
        order.calculate_totals()
        
        return order

    @staticmethod
    def update_order(order_id, data):
        """Update an existing order"""
        order = OrderRepository.get_by_id(order_id)
        
        # Don't allow updating converted orders
        if order.is_converted_to_invoice:
            raise ValidationError("Cannot update an order that has been converted to invoice")
        
        # Don't allow updating completed or cancelled orders
        if order.status in ['completed', 'cancelled']:
            raise ValidationError(f"Cannot update order with status: {order.status}")
        
        for key, value in data.items():
            setattr(order, key, value)
        
        order.save()
        return order

    @staticmethod
    def delete_order(order_id):
        """Soft delete an order"""
        order = OrderRepository.get_by_id(order_id)
        
        if order.is_converted_to_invoice:
            raise ValidationError("Cannot delete an order that has been converted to invoice")
        
        if order.status not in ['draft', 'pending']:
            raise ValidationError(f"Cannot delete order with status: {order.status}")
        
        order.soft_delete()
        return True

    @staticmethod
    def update_status(order_id, new_status, notes=None, user=None):
        """Update order status"""
        order = OrderRepository.get_by_id(order_id)
        
        old_status = order.status
        
        if old_status == new_status:
            return order
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            changed_by=user
        )
        
        order.status = new_status
        
        # Set dates based on status
        from datetime import date
        if new_status == 'confirmed':
            order.confirmed_date = date.today()
            order.confirmed_by = user
        elif new_status == 'completed':
            order.completed_date = date.today()
        
        order.save()
        return order

    @staticmethod
    def get_statistics(order_type=None):
        """Get order statistics"""
        queryset = Order.objects.filter(is_deleted=False)
        
        if order_type:
            queryset = queryset.filter(order_type=order_type)
        
        total_orders = queryset.count()
        
        status_counts = {}
        for status, _ in Order.STATUS_CHOICES:
            status_counts[status] = queryset.filter(status=status).count()
        
        total_amount = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
        average_order_value = queryset.aggregate(avg=Avg('total_amount'))['avg'] or 0
        
        converted_count = queryset.filter(is_converted_to_invoice=True).count()
        pending_conversion = queryset.filter(
            is_converted_to_invoice=False,
            status__in=['confirmed', 'processing', 'completed']
        ).count()
        
        return {
            'total_orders': total_orders,
            'status_counts': status_counts,
            'total_amount': float(total_amount),
            'average_order_value': float(average_order_value),
            'converted_count': converted_count,
            'pending_conversion': pending_conversion,
        }


class OrderItemRepository:
    """Repository for OrderItem operations"""

    @staticmethod
    def get_by_order(order_id):
        """Get all items for an order"""
        return OrderItem.objects.filter(order_id=order_id).select_related('product')

    @staticmethod
    def get_by_id(item_id):
        """Get order item by ID"""
        try:
            return OrderItem.objects.select_related('order', 'product').get(id=item_id)
        except OrderItem.DoesNotExist:
            raise NotFoundError(f"Order item with ID {item_id} not found")

    @staticmethod
    def create_item(data):
        """Create an order item"""
        item = OrderItem.objects.create(**data)
        
        # Recalculate order totals
        item.order.calculate_totals()
        
        return item

    @staticmethod
    def update_item(item_id, data):
        """Update an order item"""
        item = OrderItemRepository.get_by_id(item_id)
        
        # Check if order can be modified
        if item.order.is_converted_to_invoice:
            raise ValidationError("Cannot update items of converted order")
        
        for key, value in data.items():
            setattr(item, key, value)
        
        item.save()
        
        # Recalculate order totals
        item.order.calculate_totals()
        
        return item

    @staticmethod
    def delete_item(item_id):
        """Delete an order item"""
        item = OrderItemRepository.get_by_id(item_id)
        
        # Check if order can be modified
        if item.order.is_converted_to_invoice:
            raise ValidationError("Cannot delete items of converted order")
        
        order = item.order
        item.delete()
        
        # Recalculate order totals
        order.calculate_totals()
        
        return True

    @staticmethod
    def update_fulfillment(item_id, quantity_fulfilled):
        """Update item fulfillment quantity"""
        item = OrderItemRepository.get_by_id(item_id)
        
        if quantity_fulfilled > item.quantity:
            raise ValidationError("Fulfilled quantity cannot exceed ordered quantity")
        
        item.quantity_fulfilled = quantity_fulfilled
        item.save()
        
        return item