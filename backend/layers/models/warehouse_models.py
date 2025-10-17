"""
Warehouse Models - Corrected Version
Fixed Issues:
- Added app_label to all models
- Fixed ForeignKey references to use strings
- Added more indexes
- Added constraints
- Added validation methods
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from core.models import TimeStampedModel


class Warehouse(TimeStampedModel):
    """
    Warehouse/Storage location model
    Represents physical locations where inventory is stored
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique warehouse code'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text='Warehouse name'
    )
    
    # Location details
    address = models.TextField(
        blank=True,
        help_text='Street address'
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,  # ADDED: For city filtering
        help_text='City'
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default='Turkey',
        help_text='Country'
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text='Postal code'
    )
    
    # Contact information
    manager_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Warehouse manager name'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone'
    )
    email = models.EmailField(
        blank=True,
        help_text='Contact email'
    )
    
    # Settings
    is_active = models.BooleanField(
        default=True,
        db_index=True,  # ADDED: For active filtering
        help_text='Is this warehouse active?'
    )
    is_default = models.BooleanField(
        default=False,
        db_index=True,  # ADDED: For quick default lookup
        help_text='Default warehouse for new transactions'
    )
    
    # Additional info
    notes = models.TextField(
        blank=True,
        help_text='Additional notes'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'warehouses'
        ordering = ['-is_default', 'name']
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'
        indexes = [  # ADDED: More indexes
            models.Index(fields=['is_active', 'is_default'], name='idx_wh_active_default'),
            models.Index(fields=['city', 'is_active'], name='idx_wh_city_active'),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one default warehouse"""
        if self.is_default:
            # Set all other warehouses to non-default
            Warehouse.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)
    
    def get_total_stock_value(self):
        """Calculate total value of all stock in this warehouse"""
        total = Decimal('0.00')
        for stock in self.stocks.select_related('product'):
            total += stock.stock_value
        return total
    
    def get_stock_count(self):
        """Get count of different products in warehouse"""
        return self.stocks.filter(quantity__gt=0).count()
    
    def get_low_stock_count(self):
        """Get count of low stock items"""
        return self.stocks.filter(
            quantity__lte=models.F('min_quantity'),
            min_quantity__gt=0
        ).count()


class Stock(TimeStampedModel):
    """
    Stock levels per product per warehouse
    Tracks inventory quantities and locations
    """
    
    warehouse = models.ForeignKey(
        'layers.Warehouse',  # CHANGED: Use string reference
        on_delete=models.CASCADE,
        related_name='stocks',
        help_text='Warehouse location'
    )
    product = models.ForeignKey(
        'layers.Product',  # CHANGED: Use string reference
        on_delete=models.CASCADE,
        related_name='stocks',
        help_text='Product'
    )
    
    # Quantity tracking
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal('0.00'),
        db_index=True,  # ADDED: For quantity queries
        help_text='Current stock quantity'
    )
    reserved_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Quantity reserved for orders'
    )
    
    # Reorder settings
    min_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Minimum stock level (reorder point)'
    )
    max_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Maximum stock level'
    )
    
    # Location in warehouse
    location = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,  # ADDED: For location searches
        help_text='Shelf/Bin location within warehouse'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'stocks'
        ordering = ['warehouse', 'product']
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'
        unique_together = [['warehouse', 'product']]
        indexes = [
            models.Index(fields=['warehouse', 'product'], name='idx_stock_wh_prod'),
            models.Index(fields=['quantity'], name='idx_stock_qty'),
            models.Index(fields=['product', 'quantity'], name='idx_stock_prod_qty'),  # ADDED
            models.Index(fields=['location'], name='idx_stock_location'),  # ADDED
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(reserved_quantity__gte=0),
                name='stock_reserved_positive'
            ),
            models.CheckConstraint(
                check=models.Q(reserved_quantity__lte=models.F('quantity')),
                name='stock_reserved_not_exceed_quantity'
            ),
            models.CheckConstraint(
                check=models.Q(min_quantity__gte=0),
                name='stock_min_positive'
            ),
            models.CheckConstraint(
                check=models.Q(max_quantity__gte=0),
                name='stock_max_positive'
            ),
        ]
    
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"
    
    def clean(self):
        """Validate stock data"""
        if self.reserved_quantity > self.quantity:
            raise ValidationError({
                'reserved_quantity': 'Reserved quantity cannot exceed available quantity'
            })
        if self.max_quantity > 0 and self.min_quantity > self.max_quantity:
            raise ValidationError({
                'min_quantity': 'Minimum quantity cannot exceed maximum quantity'
            })
    
    def save(self, *args, **kwargs):
        """Validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def available_quantity(self):
        """Calculate available quantity (quantity - reserved)"""
        return max(Decimal('0.00'), self.quantity - self.reserved_quantity)
    
    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.min_quantity > 0 and self.quantity <= self.min_quantity
    
    @property
    def is_out_of_stock(self):
        """Check if out of stock"""
        return self.quantity <= 0
    
    @property
    def is_over_max(self):
        """Check if stock exceeds maximum level"""
        return self.max_quantity > 0 and self.quantity > self.max_quantity
    
    @property
    def stock_value(self):
        """Calculate total stock value based on cost price"""
        return self.quantity * self.product.cost_price
    
    @property
    def stock_status(self):
        """Get human-readable stock status"""
        if self.is_out_of_stock:
            return 'Out of Stock'
        elif self.is_low_stock:
            return 'Low Stock'
        elif self.is_over_max:
            return 'Overstocked'
        return 'Normal'
    
    def reserve(self, quantity):
        """Reserve stock for orders"""
        if quantity > self.available_quantity:
            raise ValidationError(f'Cannot reserve {quantity}. Only {self.available_quantity} available.')
        self.reserved_quantity += quantity
        self.save(update_fields=['reserved_quantity', 'updated_at'])
    
    def release(self, quantity):
        """Release reserved stock"""
        self.reserved_quantity = max(Decimal('0.00'), self.reserved_quantity - quantity)
        self.save(update_fields=['reserved_quantity', 'updated_at'])


class StockMovement(TimeStampedModel):
    """
    Track all stock movements
    Provides audit trail for inventory changes
    """
    
    class MovementType(models.TextChoices):
        IN = 'in', 'Stock In'
        OUT = 'out', 'Stock Out'
        TRANSFER = 'transfer', 'Transfer'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        PRODUCTION = 'production', 'Production'
        RETURN = 'return', 'Return'
    
    warehouse = models.ForeignKey(
        'layers.Warehouse',  # CHANGED: Use string reference
        on_delete=models.CASCADE,
        related_name='movements',
        help_text='Warehouse'
    )
    product = models.ForeignKey(
        'layers.Product',  # CHANGED: Use string reference
        on_delete=models.CASCADE,
        related_name='movements',
        help_text='Product'
    )
    
    # Movement details
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        db_index=True,  # ADDED: For filtering by type
        help_text='Type of movement'
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text='Quantity moved (positive for IN, negative for OUT)'
    )
    
    # Before/After tracking for audit
    quantity_before = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal('0.00'),
        help_text='Quantity before movement'
    )
    quantity_after = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=Decimal('0.00'),
        help_text='Quantity after movement'
    )
    
    # Transfer details (if movement_type = TRANSFER)
    from_warehouse = models.ForeignKey(
        'layers.Warehouse',  # CHANGED: Use string reference
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_out',
        help_text='Source warehouse for transfers'
    )
    to_warehouse = models.ForeignKey(
        'layers.Warehouse',  # CHANGED: Use string reference
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_in',
        help_text='Destination warehouse for transfers'
    )
    
    # Reference to source document
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,  # ADDED: For reference lookups
        help_text='Type of source document (invoice, order, production, etc.)'
    )
    reference_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,  # ADDED: For reference lookups
        help_text='ID of source document'
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,  # ADDED: For reference lookups
        help_text='Document number for reference'
    )
    
    # Additional info
    notes = models.TextField(
        blank=True,
        help_text='Movement notes'
    )
    created_by = models.ForeignKey(
        'layers.User',  # CHANGED: Use string reference
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements_created',
        help_text='User who created this movement'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'stock_movements'
        ordering = ['-created_at']
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        indexes = [
            models.Index(fields=['warehouse', 'product'], name='idx_movement_wh_prod'),
            models.Index(fields=['movement_type'], name='idx_movement_type'),
            models.Index(fields=['created_at'], name='idx_movement_date'),
            models.Index(fields=['reference_type', 'reference_id'], name='idx_movement_ref'),
            models.Index(fields=['product', '-created_at'], name='idx_movement_prod_date'),  # ADDED
        ]
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name}: {self.quantity}"
    
    @property
    def quantity_change(self):
        """Get absolute quantity change"""
        return abs(self.quantity)
    
    @property
    def is_increase(self):
        """Check if this movement increased stock"""
        return self.quantity > 0
    
    @property
    def is_decrease(self):
        """Check if this movement decreased stock"""
        return self.quantity < 0
    
    def get_reference_display(self):
        """Get formatted reference display"""
        if self.reference_type and self.reference_number:
            return f"{self.reference_type} #{self.reference_number}"
        return "N/A"