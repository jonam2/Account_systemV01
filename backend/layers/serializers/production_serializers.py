from rest_framework import serializers
from layers.models.production_models import (
    BillOfMaterials, BOMComponent, ProductionOrder, 
    ProductionOrderItem, ProductionPhase
)
from layers.serializers.product_serializers import ProductListSerializer
from layers.serializers.user_serializers import UserSerializer


class BOMComponentSerializer(serializers.ModelSerializer):
    """Serializer for BOM components"""
    component_name = serializers.CharField(source='component.name', read_only=True)
    component_sku = serializers.CharField(source='component.sku', read_only=True)
    component_details = ProductListSerializer(source='component', read_only=True)
    total_cost = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = BOMComponent
        fields = [
            'id', 'component', 'component_name', 'component_sku',
            'component_details', 'quantity', 'is_variable', 
            'estimated_quantity', 'unit_cost', 'total_cost',
            'notes', 'sequence', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BOMComponentCreateSerializer(serializers.Serializer):
    """Serializer for creating BOM components"""
    component_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    is_variable = serializers.BooleanField(default=False)
    estimated_quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, required=False, allow_null=True
    )
    unit_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, default=0
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    sequence = serializers.IntegerField(default=0)


class BOMListSerializer(serializers.ModelSerializer):
    """Serializer for listing BOMs"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    component_count = serializers.IntegerField(read_only=True)
    total_cost_per_unit = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = BillOfMaterials
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'name', 'name_ar', 'version', 'is_active',
            'expected_quantity', 'min_yield', 'max_yield',
            'estimated_material_cost', 'labor_cost', 
            'overhead_cost', 'total_cost_per_unit',
            'component_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BOMDetailSerializer(serializers.ModelSerializer):
    """Detailed BOM serializer with components"""
    product_details = ProductListSerializer(source='product', read_only=True)
    components = BOMComponentSerializer(many=True, read_only=True)
    component_count = serializers.IntegerField(read_only=True)
    total_cost_per_unit = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = BillOfMaterials
        fields = [
            'id', 'product', 'product_details', 'name', 'name_ar',
            'version', 'is_active', 'notes', 'expected_quantity',
            'min_yield', 'max_yield', 'estimated_material_cost',
            'labor_cost', 'overhead_cost', 'total_cost_per_unit',
            'components', 'component_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BOMCreateSerializer(serializers.Serializer):
    """Serializer for creating BOM"""
    product_id = serializers.IntegerField()
    name = serializers.CharField(max_length=200)
    name_ar = serializers.CharField(max_length=200, required=False, allow_blank=True)
    version = serializers.CharField(max_length=50, default='1.0')
    is_active = serializers.BooleanField(default=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    expected_quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, default=1
    )
    min_yield = serializers.DecimalField(
        max_digits=12, decimal_places=3, required=False, allow_null=True
    )
    max_yield = serializers.DecimalField(
        max_digits=12, decimal_places=3, required=False, allow_null=True
    )
    labor_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    overhead_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    components = BOMComponentCreateSerializer(many=True)


class ProductionOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for production order items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_details = ProductListSerializer(source='product', read_only=True)
    variance_quantity = serializers.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        read_only=True
    )
    
    class Meta:
        model = ProductionOrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'product_details', 'planned_quantity', 'actual_quantity',
            'variance_quantity', 'unit_cost', 'total_cost',
            'reserved', 'reservation_id', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductionPhaseSerializer(serializers.ModelSerializer):
    """Serializer for production phases"""
    
    class Meta:
        model = ProductionPhase
        fields = [
            'id', 'phase_number', 'name', 'description',
            'started_at', 'completed_at', 'status',
            'components_snapshot', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductionOrderListSerializer(serializers.ModelSerializer):
    """Serializer for listing production orders"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance_quantity = serializers.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        read_only=True
    )
    yield_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = ProductionOrder
        fields = [
            'id', 'order_number', 'order_type', 'order_type_display',
            'status', 'status_display', 'product', 'product_name',
            'warehouse', 'warehouse_name', 'planned_quantity',
            'actual_quantity', 'variance_quantity', 'yield_percentage',
            'scheduled_date', 'started_at', 'completed_at',
            'material_cost', 'labor_cost', 'overhead_cost',
            'total_cost', 'created_by_name', 'phase', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductionOrderDetailSerializer(serializers.ModelSerializer):
    """Detailed production order serializer"""
    product_details = ProductListSerializer(source='product', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    bom_details = BOMDetailSerializer(source='bom', read_only=True)
    items = ProductionOrderItemSerializer(many=True, read_only=True)
    phases = ProductionPhaseSerializer(many=True, read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    completed_by_details = UserSerializer(source='completed_by', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance_quantity = serializers.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        read_only=True
    )
    yield_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = ProductionOrder
        fields = [
            'id', 'order_number', 'order_type', 'order_type_display',
            'status', 'status_display', 'product', 'product_details',
            'warehouse', 'warehouse_name', 'bom', 'bom_details',
            'planned_quantity', 'actual_quantity', 'variance_quantity',
            'yield_percentage', 'scheduled_date', 'started_at',
            'completed_at', 'material_cost', 'labor_cost',
            'overhead_cost', 'total_cost', 'created_by',
            'created_by_details', 'completed_by', 'completed_by_details',
            'notes', 'parent_order', 'phase', 'items', 'phases',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssemblyOrderCreateSerializer(serializers.Serializer):
    """Serializer for creating assembly orders"""
    product_id = serializers.IntegerField()
    warehouse_id = serializers.IntegerField()
    planned_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    scheduled_date = serializers.DateField(required=False)
    labor_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, default=0
    )
    overhead_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, default=0
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    force = serializers.BooleanField(
        default=False,
        help_text="Force create even if components are insufficient"
    )


class DisassemblyOrderCreateSerializer(serializers.Serializer):
    """Serializer for creating disassembly orders"""
    product_id = serializers.IntegerField()
    warehouse_id = serializers.IntegerField()
    planned_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    scheduled_date = serializers.DateField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    parent_order_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Parent order ID for phased disassembly"
    )
    phase = serializers.IntegerField(
        default=1,
        help_text="Disassembly phase number"
    )


class CompleteAssemblySerializer(serializers.Serializer):
    """Serializer for completing assembly"""
    actual_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    actual_components = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {item_id, actual_quantity}"
    )


class CompleteDisassemblySerializer(serializers.Serializer):
    """Serializer for completing disassembly"""
    actual_components = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {item_id, actual_quantity} for recovered components"
    )


class ComponentAvailabilitySerializer(serializers.Serializer):
    """Serializer for component availability check"""
    bom_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    warehouse_id = serializers.IntegerField()