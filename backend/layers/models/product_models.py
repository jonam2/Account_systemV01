"""
Product Models - Corrected Version
Fixed Issues:
- Added app_label to both models
- Added more indexes
- Added constraints
- Added helper methods
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import TimeStampedModel


class Category(TimeStampedModel):
    """
    Product category model with hierarchical structure
    Supports parent-child relationships for nested categories
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique category code'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text='Category name'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        db_index=True,  # ADDED: Index for parent queries
        help_text='Parent category for hierarchical structure'
    )
    description = models.TextField(
        blank=True,
        help_text='Category description'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,  # ADDED: Index for active filtering
        help_text='Is this category active?'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'categories'
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        indexes = [  # ADDED: More indexes
            models.Index(fields=['parent', 'is_active'], name='idx_category_parent_active'),
            models.Index(fields=['is_active', 'name'], name='idx_category_active_name'),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def full_path(self):
        """Get full category path (e.g., 'Electronics > Mobile > Smartphones')"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name
    
    @property
    def level(self):
        """Get category level (0 for root, 1 for child, etc.)"""
        if self.parent:
            return self.parent.level + 1
        return 0
    
    @property
    def is_root(self):
        """Check if this is a root category"""
        return self.parent is None
    
    @property
    def has_children(self):
        """Check if category has child categories"""
        return self.children.exists()
    
    def get_all_children(self):
        """Get all child categories recursively"""
        children = list(self.children.filter(is_active=True))
        for child in list(children):
            children.extend(child.get_all_children())
        return children


class Product(TimeStampedModel):
    """
    Product model
    Represents items that can be bought, sold, or manufactured
    """
    
    class Unit(models.TextChoices):
        PIECE = 'piece', 'Piece'
        KG = 'kg', 'Kilogram'
        GRAM = 'gram', 'Gram'
        LITER = 'liter', 'Liter'
        METER = 'meter', 'Meter'
        CM = 'cm', 'Centimeter'
        BOX = 'box', 'Box'
        PACKAGE = 'package', 'Package'
    
    # Basic Information
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text='Unique product code/SKU'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text='Product name'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        db_index=True,  # Already indexed by FK
        help_text='Product category'
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed product description'
    )
    
    # Product Details
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.PIECE,
        help_text='Unit of measurement'
    )
    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        db_index=True,  # Already indexed by unique
        help_text='Product barcode'
    )
    sku = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,  # ADDED: For SKU searches
        help_text='Stock Keeping Unit'
    )
    
    # Pricing
    sale_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        db_index=True,  # ADDED: For price-based queries
        help_text='Selling price per unit'
    )
    cost_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Cost/Purchase price per unit'
    )
    currency = models.CharField(
        max_length=3,
        default='TRY',
        help_text='Currency code (ISO 4217)'
    )
    
    # Dimensions
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Weight in kg'
    )
    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Length in cm'
    )
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Width in cm'
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Height in cm'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,  # ADDED: For active filtering
        help_text='Is this product active?'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'products'
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['code'], name='idx_product_code'),
            models.Index(fields=['name'], name='idx_product_name'),
            models.Index(fields=['barcode'], name='idx_product_barcode'),
            models.Index(fields=['sku'], name='idx_product_sku'),  # ADDED
            models.Index(fields=['is_active'], name='idx_product_active'),  # ADDED
            models.Index(fields=['category', 'is_active'], name='idx_product_cat_active'),  # ADDED
            models.Index(fields=['sale_price'], name='idx_product_price'),  # ADDED
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(sale_price__gte=0),
                name='product_sale_price_positive'
            ),
            models.CheckConstraint(
                check=models.Q(cost_price__gte=0),
                name='product_cost_price_positive'
            ),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.sale_price > 0:
            profit = self.sale_price - self.cost_price
            return (profit / self.sale_price) * 100
        return Decimal('0.00')
    
    @property
    def profit_amount(self):
        """Calculate profit amount per unit"""
        return self.sale_price - self.cost_price
    
    @property
    def markup_percentage(self):
        """Calculate markup percentage based on cost"""
        if self.cost_price > 0:
            return ((self.sale_price - self.cost_price) / self.cost_price) * 100
        return Decimal('0.00')
    
    @property
    def volume(self):
        """Calculate volume in cubic cm"""
        if self.length and self.width and self.height:
            return self.length * self.width * self.height
        return None
    
    @property
    def dimensional_weight(self):
        """Calculate dimensional weight (volume / 5000)"""
        vol = self.volume
        if vol:
            return vol / Decimal('5000.00')
        return None
    
    def get_total_stock(self):
        """Get total stock across all warehouses"""
        from layers.models.warehouse_models import Stock
        total = Stock.objects.filter(
            product=self,
            is_deleted=False
        ).aggregate(
            total=models.Sum('quantity')
        )['total']
        return total or Decimal('0.00')
    
    def is_profitable(self):
        """Check if product is profitable"""
        return self.sale_price > self.cost_price