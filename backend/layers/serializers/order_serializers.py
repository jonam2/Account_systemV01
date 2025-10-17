"""Order serializers"""
from rest_framework import serializers
from layers.models.order_models import Order, OrderItem, OrderStatusHistory


# ==================== ORDER ITEM SERIALIZERS ====================

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem"""
    
    product_name = serializers.CharField(read_only=True)
    product_sku = serializers.CharField(read_only=True)
    quantity_remaining = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    is_fully_fulfilled = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'discount_percentage', 'discount_amount',
            'tax_percentage', 'tax_amount', 'total_price',
            'quantity_fulfilled', 'quantity_remaining', 'is_fully_fulfilled',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'total_price', 'created_at']


class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order items"""
    
    class Meta:
        model = OrderItem
        fields = [
            'product', 'quantity', 'unit_price',
            'discount_percentage', 'discount_amount',
            'tax_percentage', 'tax_amount', 'notes'
        ]
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative")
        return value


# ==================== ORDER STATUS HISTORY SERIALIZERS ====================

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for OrderStatusHistory"""
    
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'notes',
            'changed_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ==================== ORDER SERIALIZERS ====================

class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for Order list view"""
    
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_code = serializers.CharField(source='contact.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    can_be_converted = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_type', 'order_type_display', 'order_number',
            'reference_number', 'contact', 'contact_name', 'contact_code',
            'warehouse', 'warehouse_name', 'order_date', 'expected_date',
            'status', 'status_display', 'currency', 'total_amount',
            'is_converted_to_invoice', 'can_be_converted', 'items_count',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for Order detail view"""
    
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_code = serializers.CharField(source='contact.code', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.full_name', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    can_be_converted = serializers.BooleanField(read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    is_sales_order = serializers.BooleanField(read_only=True)
    is_purchase_order = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_type', 'order_type_display', 'order_number',
            'reference_number', 'contact', 'contact_name', 'contact_code',
            'warehouse', 'warehouse_name', 'order_date', 'expected_date',
            'confirmed_date', 'completed_date', 'status', 'status_display',
            'currency', 'exchange_rate', 'subtotal', 'discount_percentage',
            'discount_amount', 'tax_percentage', 'tax_amount', 'shipping_cost',
            'total_amount', 'is_converted_to_invoice', 'invoice', 'invoice_number',
            'can_be_converted', 'notes', 'terms_and_conditions', 'items',
            'items_count', 'status_history', 'is_sales_order', 'is_purchase_order',
            'created_by_name', 'confirmed_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating an order"""
    
    items = OrderItemCreateSerializer(many=True)
    
    class Meta:
        model = Order
        fields = [
            'order_type', 'order_number', 'reference_number',
            'contact', 'warehouse', 'order_date', 'expected_date',
            'status', 'currency', 'exchange_rate', 'discount_percentage',
            'discount_amount', 'tax_percentage', 'tax_amount', 'shipping_cost',
            'notes', 'terms_and_conditions', 'items'
        ]
    
    def validate(self, data):
        # Validate items exist
        if not data.get('items'):
            raise serializers.ValidationError("Order must have at least one item")
        
        # Validate order date
        if data.get('expected_date') and data.get('order_date'):
            if data['expected_date'] < data['order_date']:
                raise serializers.ValidationError(
                    "Expected date cannot be before order date"
                )
        
        return data
    
    def validate_exchange_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError("Exchange rate must be greater than 0")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an order"""
    
    class Meta:
        model = Order
        fields = [
            'reference_number', 'warehouse', 'order_date', 'expected_date',
            'status', 'currency', 'exchange_rate', 'discount_percentage',
            'discount_amount', 'tax_percentage', 'tax_amount', 'shipping_cost',
            'notes', 'terms_and_conditions'
        ]
    
    def validate_exchange_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError("Exchange rate must be greater than 0")
        return value


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)


class ConvertToInvoiceSerializer(serializers.Serializer):
    """Serializer for converting order to invoice"""
    
    notes = serializers.CharField(required=False, allow_blank=True)


# ==================== STATISTICS SERIALIZERS ====================

class OrderStatsSerializer(serializers.Serializer):
    """Serializer for order statistics"""
    
    total_orders = serializers.IntegerField()
    status_counts = serializers.DictField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    converted_count = serializers.IntegerField()
    pending_conversion = serializers.IntegerField()


# ==================== ITEM FULFILLMENT SERIALIZER ====================

class OrderItemFulfillmentSerializer(serializers.Serializer):
    """Serializer for updating item fulfillment"""
    
    quantity_fulfilled = serializers.DecimalField(max_digits=15, decimal_places=3, min_value=0)
    
    def validate_quantity_fulfilled(self, value):
        if value < 0:
            raise serializers.ValidationError("Fulfilled quantity cannot be negative")
        return value