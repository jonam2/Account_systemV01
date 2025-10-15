"""Warehouse database models"""
from django.db import models
from core.models import TimeStampedModel


class Warehouse(TimeStampedModel):
    """Warehouse/Storage location model"""
    
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    
    # Location details
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default='Turkey')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Contact information
    manager_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text='Default warehouse for new transactions')
    
    # Additional info
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'warehouses'
        ordering = ['-is_default', 'name']
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one default warehouse"""
        if self.is_default:
            Warehouse.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class Stock(TimeStampedModel):
    """Stock levels per product per warehouse"""
    
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    
    # Quantity tracking
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Current stock quantity'
    )
    reserved_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Quantity reserved for orders'
    )
    
    # Reorder settings
    min_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Minimum stock level (reorder point)'
    )
    max_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Maximum stock level'
    )
    
    # Location in warehouse
    location = models.CharField(max_length=100, blank=True, help_text='Shelf/Bin location')
    
    class Meta:
        db_table = 'stocks'
        ordering = ['warehouse', 'product']
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'
        unique_together = [['warehouse', 'product']]
        indexes = [
            models.Index(fields=['warehouse', 'product']),
            models.Index(fields=['quantity']),
        ]
    
    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"
    
    @property
    def available_quantity(self):
        """Calculate available quantity (quantity - reserved)"""
        return self.quantity - self.reserved_quantity
    
    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.quantity <= self.min_quantity if self.min_quantity > 0 else False
    
    @property
    def is_out_of_stock(self):
        """Check if out of stock"""
        return self.quantity <= 0
    
    @property
    def stock_value(self):
        """Calculate total stock value"""
        return self.quantity * self.product.cost_price


class StockMovement(TimeStampedModel):
    """Track all stock movements"""
    
    class MovementType(models.TextChoices):
        IN = 'in', 'Stock In'
        OUT = 'out', 'Stock Out'
        TRANSFER = 'transfer', 'Transfer'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        PRODUCTION = 'production', 'Production'
        RETURN = 'return', 'Return'
    
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='movements'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='movements'
    )
    
    # Movement details
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        help_text='Positive for IN, negative for OUT'
    )
    
    # Before/After tracking
    quantity_before = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0
    )
    quantity_after = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0
    )
    
    # Transfer details (if movement_type = TRANSFER)
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_out'
    )
    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers_in'
    )
    
    # Reference details
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='invoice, order, production, etc.'
    )
    reference_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of related document'
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Document number for reference'
    )
    
    # Additional info
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='stock_movements'
    )
    
    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        indexes = [
            models.Index(fields=['warehouse', 'product']),
            models.Index(fields=['movement_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]
    
    def __str__(self):
        return f"{self.movement_type} - {self.product.name}: {self.quantity}"