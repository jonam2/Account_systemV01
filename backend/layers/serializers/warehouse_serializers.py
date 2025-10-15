"""Warehouse serializers - Data transfer objects"""
from rest_framework import serializers
from layers.models.warehouse_models import Warehouse, Stock, StockMovement


# Warehouse Serializers

class WarehouseSerializer(serializers.ModelSerializer):
    """Main warehouse serializer"""
    
    class Meta:
        model = Warehouse
        fields = [
            'id',
            'code',
            'name',
            'address',
            'city',
            'country',
            'postal_code',
            'manager_name',
            'phone',
            'email',
            'is_active',
            'is_default',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WarehouseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating warehouses"""
    
    class Meta:
        model = Warehouse
        fields = [
            'code',
            'name',
            'address',
            'city',
            'country',
            'postal_code',
            'manager_name',
            'phone',
            'email',
            'is_active',
            'is_default',
            'notes',
        ]
    
    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")
        return value.strip()


class WarehouseUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating warehouses"""
    
    class Meta:
        model = Warehouse
        fields = [
            'code',
            'name',
            'address',
            'city',
            'country',
            'postal_code',
            'manager_name',
            'phone',
            'email',
            'is_active',
            'is_default',
            'notes',
        ]


# Stock Serializers

class StockSerializer(serializers.ModelSerializer):
    """Main stock serializer"""
    
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    available_quantity = serializers.DecimalField(
        max_digits=15,
        decimal_places=3,
        read_only=True
    )
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Stock
        fields = [
            'id',
            'warehouse',
            'warehouse_name',
            'warehouse_code',
            'product',
            'product_name',
            'product_code',
            'product_unit',
            'quantity',
            'reserved_quantity',
            'available_quantity',
            'min_quantity',
            'max_quantity',
            'location',
            'is_low_stock',
            'is_out_of_stock',
            'stock_value',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for stock adjustment"""
    
    warehouse_id = serializers.IntegerField(required=True)
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(
        max_digits=15,
        decimal_places=3,
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_quantity(self, value):
        if value == 0:
            raise serializers.ValidationError("Quantity cannot be zero")
        return value


class StockTransferSerializer(serializers.Serializer):
    """Serializer for stock transfer"""
    
    from_warehouse_id = serializers.IntegerField(required=True)
    to_warehouse_id = serializers.IntegerField(required=True)
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(
        max_digits=15,
        decimal_places=3,
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Transfer quantity must be positive")
        return value
    
    def validate(self, data):
        if data['from_warehouse_id'] == data['to_warehouse_id']:
            raise serializers.ValidationError("Cannot transfer to the same warehouse")
        return data


class StockUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating stock settings"""
    
    class Meta:
        model = Stock
        fields = [
            'min_quantity',
            'max_quantity',
            'location',
        ]


# Stock Movement Serializers

class StockMovementSerializer(serializers.ModelSerializer):
    """Main stock movement serializer"""
    
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    movement_type_display = serializers.CharField(
        source='get_movement_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
        allow_null=True
    )
    from_warehouse_name = serializers.CharField(
        source='from_warehouse.name',
        read_only=True,
        allow_null=True
    )
    to_warehouse_name = serializers.CharField(
        source='to_warehouse.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = StockMovement
        fields = [
            'id',
            'warehouse',
            'warehouse_name',
            'product',
            'product_name',
            'product_code',
            'movement_type',
            'movement_type_display',
            'quantity',
            'quantity_before',
            'quantity_after',
            'from_warehouse',
            'from_warehouse_name',
            'to_warehouse',
            'to_warehouse_name',
            'reference_type',
            'reference_id',
            'reference_number',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class StockMovementListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for movement lists"""
    
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    movement_type_display = serializers.CharField(
        source='get_movement_type_display',
        read_only=True
    )
    
    class Meta:
        model = StockMovement
        fields = [
            'id',
            'warehouse_name',
            'product_name',
            'movement_type',
            'movement_type_display',
            'quantity',
            'quantity_after',
            'reference_number',
            'created_at',
        ]
class WarehouseSummarySerializer(serializers.ModelSerializer):
    """Lightweight warehouse serializer for nested representations"""
    
    class Meta:
        model = Warehouse
        fields = [
            'id',
            'code',
            'name',
            'location',
            'is_active'
        ]