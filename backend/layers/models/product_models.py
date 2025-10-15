"""Product database models"""
from django.db import models
from core.models import TimeStampedModel


class Category(TimeStampedModel):
    """Product category model with hierarchical structure"""
    
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def full_path(self):
        """Get full category path"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Product(TimeStampedModel):
    """Product model"""
    
    class Unit(models.TextChoices):
        PIECE = 'piece', 'Piece'
        KG = 'kg', 'Kilogram'
        GRAM = 'gram', 'Gram'
        LITER = 'liter', 'Liter'
        METER = 'meter', 'Meter'
        CM = 'cm', 'Centimeter'
        BOX = 'box', 'Box'
        PACKAGE = 'package', 'Package'
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    description = models.TextField(blank=True)
    
    # Product details
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.PIECE
    )
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True)
    
    # Pricing
    sale_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Selling price'
    )
    cost_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Cost/Purchase price'
    )
    currency = models.CharField(max_length=3, default='TRY')
    
    # Dimensions
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text='Weight in kg'
    )
    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Length in cm'
    )
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Width in cm'
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Height in cm'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
            models.Index(fields=['barcode']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.sale_price > 0:
            return ((self.sale_price - self.cost_price) / self.sale_price) * 100
        return 0