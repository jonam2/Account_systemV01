"""Order database models"""
from django.db import models
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel, SoftDeleteModel


class Order(TimeStampedModel, SoftDeleteModel):
    """Base Order model for both Sales and Purchase Orders"""
    
    ORDER_TYPE_CHOICES = [
        ('sales', 'Sales Order'),
        ('purchase', 'Purchase Order'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('SAR', 'Saudi Riyal'),
        ('AED', 'UAE Dirham'),
        ('TRY', 'Turkish Lira'),
    ]
    
    # Order identification
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    order_number = models.CharField(max_length=50, unique=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Contact information
    contact = models.ForeignKey(
        'Contact',
        on_delete=models.PROTECT,
        related_name='orders'
    )
    
    # Warehouse
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.PROTECT,
        related_name='orders',
        null=True,
        blank=True
    )
    
    # Dates
    order_date = models.DateField()
    expected_date = models.DateField(null=True, blank=True)
    confirmed_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial details
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    exchange_rate = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        default=1,
        validators=[MinValueValidator(0)]
    )
    
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    shipping_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Conversion tracking
    is_converted_to_invoice = models.BooleanField(default=False)
    invoice = models.ForeignKey(
        'Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_order'
    )
    
    # Additional information
    notes = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    
    # User tracking
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders_created'
    )
    confirmed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders_confirmed'
    )

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_type']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['contact']),
            models.Index(fields=['order_date']),
            models.Index(fields=['is_converted_to_invoice']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.contact.name}"

    def calculate_totals(self):
        """Calculate order totals from items"""
        items = self.items.all()
        
        # Calculate subtotal
        self.subtotal = sum(item.total_price for item in items)
        
        # Calculate discount
        if self.discount_percentage > 0:
            self.discount_amount = (self.subtotal * self.discount_percentage) / 100
        
        # Calculate amount after discount
        amount_after_discount = self.subtotal - self.discount_amount
        
        # Calculate tax
        if self.tax_percentage > 0:
            self.tax_amount = (amount_after_discount * self.tax_percentage) / 100
        
        # Calculate total
        self.total_amount = amount_after_discount + self.tax_amount + self.shipping_cost
        
        self.save()
        return self.total_amount

    @property
    def is_sales_order(self):
        return self.order_type == 'sales'

    @property
    def is_purchase_order(self):
        return self.order_type == 'purchase'

    @property
    def can_be_converted(self):
        """Check if order can be converted to invoice"""
        return (
            not self.is_converted_to_invoice and
            self.status in ['confirmed', 'processing', 'completed']
        )

    @property
    def items_count(self):
        return self.items.count()


class OrderItem(TimeStampedModel):
    """Items in an order"""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    
    # Product details at time of order
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=100, blank=True, null=True)
    
    # Quantity and pricing
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(0.001)]
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Fulfillment tracking
    quantity_fulfilled = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'order_items'
        ordering = ['id']
        indexes = [
            models.Index(fields=['order', 'product']),
        ]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def calculate_totals(self):
        """Calculate item totals"""
        # Calculate line total before discount
        line_total = self.quantity * self.unit_price
        
        # Calculate discount
        if self.discount_percentage > 0:
            self.discount_amount = (line_total * self.discount_percentage) / 100
        
        # Calculate amount after discount
        amount_after_discount = line_total - self.discount_amount
        
        # Calculate tax
        if self.tax_percentage > 0:
            self.tax_amount = (amount_after_discount * self.tax_percentage) / 100
        
        # Calculate total
        self.total_price = amount_after_discount + self.tax_amount
        
        return self.total_price

    @property
    def quantity_remaining(self):
        """Get remaining quantity to fulfill"""
        return max(0, self.quantity - self.quantity_fulfilled)

    @property
    def is_fully_fulfilled(self):
        """Check if item is fully fulfilled"""
        return self.quantity_fulfilled >= self.quantity

    def save(self, *args, **kwargs):
        # Store product details
        if self.product:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
        
        # Calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)


class OrderStatusHistory(TimeStampedModel):
    """Track order status changes"""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_status_changes'
    )

    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
        verbose_name_plural = 'Order status histories'

    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} → {self.new_status}"