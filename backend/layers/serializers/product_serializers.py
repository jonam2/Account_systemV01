"""Product serializers for data validation and transformation"""
from rest_framework import serializers
from layers.models.product_models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    
    full_path = serializers.CharField(read_only=True)
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'description', 'parent', 'full_path',
            'is_active', 'products_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_products_count(self, obj):
        return obj.products.filter(is_deleted=False).count()


class CategoryCreateSerializer(serializers.Serializer):
    """Serializer for creating categories"""
    
    name = serializers.CharField(max_length=100, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    parent = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model - Read operations"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_full_path = serializers.CharField(source='category.full_path', read_only=True)
    profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    profit_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    unit_type_display = serializers.CharField(source='get_unit_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'name_ar', 'sku', 'barcode',
            'category', 'category_name', 'category_full_path',
            'description', 'description_ar',
            'cost_price', 'selling_price', 'profit_margin', 'profit_amount',
            'unit_type', 'unit_type_display',
            'min_stock', 'max_stock',
            'image', 'is_active', 'track_inventory',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductCreateSerializer(serializers.Serializer):
    """Serializer for creating products"""
    
    name = serializers.CharField(max_length=200, required=True)
    name_ar = serializers.CharField(max_length=200, required=False, allow_blank=True)
    sku = serializers.CharField(max_length=50, required=True)
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    category = serializers.IntegerField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    description_ar = serializers.CharField(required=False, allow_blank=True)
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    unit_type = serializers.ChoiceField(
        choices=['piece', 'kg', 'liter', 'meter', 'box', 'pack'],
        default='piece'
    )
    min_stock = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_stock = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = serializers.BooleanField(default=True)
    track_inventory = serializers.BooleanField(default=True)


class ProductUpdateSerializer(serializers.Serializer):
    """Serializer for updating products"""
    
    name = serializers.CharField(max_length=200, required=False)
    name_ar = serializers.CharField(max_length=200, required=False, allow_blank=True)
    sku = serializers.CharField(max_length=50, required=False)
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    category = serializers.IntegerField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    description_ar = serializers.CharField(required=False, allow_blank=True)
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    unit_type = serializers.ChoiceField(
        choices=['piece', 'kg', 'liter', 'meter', 'box', 'pack'],
        required=False
    )
    min_stock = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_stock = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    is_active = serializers.BooleanField(required=False)
    track_inventory = serializers.BooleanField(required=False)


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing products"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category_name',
            'selling_price', 'is_active'
        ]

class ProductSummarySerializer(serializers.ModelSerializer):
    """Lightweight product serializer for nested representations"""
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    
    class Meta:
        model = Product
        fields = [
            'id',
            'sku',
            'name',
            'category_name',
            'unit',
            'selling_price',
            'cost_price'
        ]