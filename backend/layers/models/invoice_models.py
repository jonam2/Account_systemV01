"""
Invoice Models - Domain Layer
Handles Sales and Purchase Invoices with line items
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import TimeStampedModel, SoftDeleteModel


class Invoice(TimeStampedModel, SoftDeleteModel):
    """
    Main Invoice model for both Sales and Purchase invoices
    """
    INVOICE_TYPE_CHOICES = [
        ('SALES', 'Sales Invoice'),
        ('PURCHASE', 'Purchase Invoice'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('CANCELLED', 'Cancelled'),
        ('OVERDUE', 'Overdue'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('IMMEDIATE', 'Immediate'),
        ('NET_15', 'Net 15 Days'),
        ('NET_30', 'Net 30 Days'),
        ('NET_45', 'Net 45 Days'),
        ('NET_60', 'Net 60 Days'),
        ('NET_90', 'Net 90 Days'),
    ]

    # Basic Information
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique invoice number (auto-generated)"
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=INVOICE_TYPE_CHOICES,
        db_index=True
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="External reference number (PO number, etc.)"
    )
    
    # Relationships
    contact = models.ForeignKey(
        'Contact',  # Customer for SALES, Supplier for PURCHASE
        on_delete=models.PROTECT,
        related_name='invoices'
    )
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text="Warehouse for inventory movements"
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='created_invoices'
    )
    approved_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        related_name='approved_invoices',
        null=True,
        blank=True
    )
    
    # Dates
    invoice_date = models.DateField(db_index=True)
    due_date = models.DateField(db_index=True)
    payment_date = models.DateField(null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    
    # Payment Terms
    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default='NET_30'
    )
    
    # Financial Fields
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    shipping_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    balance_due = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status & Notes
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    notes = models.TextField(blank=True, null=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    
    # Flags
    is_recurring = models.BooleanField(default=False)
    inventory_updated = models.BooleanField(
        default=False,
        help_text="Whether inventory has been updated for this invoice"
    )

    class Meta:
        app_label = 'layers'
        db_table = 'invoices'
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice_type', 'status']),
            models.Index(fields=['contact', 'invoice_date']),
            models.Index(fields=['due_date']),
        ]
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __str__(self):
        return f"{self.get_invoice_type_display()} - {self.invoice_number}"

    def calculate_totals(self):
        """Calculate all financial totals"""
        # Subtotal from line items
        self.subtotal = sum(
            item.line_total for item in self.items.all()
        )
        
        # Discount
        if self.discount_percentage > 0:
            self.discount_amount = (self.subtotal * self.discount_percentage) / 100
        
        # Amount after discount
        amount_after_discount = self.subtotal - self.discount_amount
        
        # Tax
        if self.tax_percentage > 0:
            self.tax_amount = (amount_after_discount * self.tax_percentage) / 100
        
        # Total
        self.total_amount = amount_after_discount + self.tax_amount + self.shipping_cost
        
        # Balance due
        self.balance_due = self.total_amount - self.paid_amount
        
        return self.total_amount

    def update_status(self):
        """Update invoice status based on payment"""
        if self.paid_amount >= self.total_amount:
            self.status = 'PAID'
        elif self.paid_amount > 0:
            self.status = 'PARTIALLY_PAID'
        elif self.status == 'DRAFT':
            self.status = 'DRAFT'
        else:
            self.status = 'PENDING'
        
        return self.status

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        from django.utils import timezone
        if self.status not in ['PAID', 'CANCELLED']:
            return timezone.now().date() > self.due_date
        return False

    @property
    def days_until_due(self):
        """Calculate days until due date"""
        from django.utils import timezone
        if self.status not in ['PAID', 'CANCELLED']:
            delta = self.due_date - timezone.now().date()
            return delta.days
        return 0


class InvoiceItem(TimeStampedModel, SoftDeleteModel):
    """
    Individual line items in an invoice
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.PROTECT,
        related_name='invoice_items'
    )
    
    # Item Details
    description = models.TextField(
        blank=True,
        help_text="Item description (auto-filled from product)"
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Discounts
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Tax
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Totals
    line_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Additional Info
    notes = models.TextField(blank=True, null=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'invoice_items'
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['invoice', 'product']),
        ]
        verbose_name = 'Invoice Item'
        verbose_name_plural = 'Invoice Items'

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.name} x {self.quantity}"

    def calculate_line_total(self):
        """Calculate line total with discount and tax"""
        # Base amount
        base_amount = self.quantity * self.unit_price
        
        # Apply discount
        if self.discount_percentage > 0:
            self.discount_amount = (base_amount * self.discount_percentage) / 100
        
        amount_after_discount = base_amount - self.discount_amount
        
        # Apply tax
        if self.tax_percentage > 0:
            self.tax_amount = (amount_after_discount * self.tax_percentage) / 100
        
        # Final total
        self.line_total = amount_after_discount + self.tax_amount
        
        return self.line_total

    def save(self, *args, **kwargs):
        """Override save to auto-fill description and calculate totals"""
        if not self.description:
            self.description = self.product.description or self.product.name
        
        self.calculate_line_total()
        super().save(*args, **kwargs)


class InvoicePayment(TimeStampedModel):
    """
    Payment records for invoices
    """
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('CHECK', 'Check'),
        ('MOBILE_PAYMENT', 'Mobile Payment'),
        ('OTHER', 'Other'),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment Details
    payment_date = models.DateField(db_index=True)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Check number, transaction ID, etc."
    )
    
    # Tracking
    recorded_by = models.ForeignKey(
        'User',
        on_delete=models.PROTECT,
        related_name='recorded_payments'
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'invoice_payments'
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice', 'payment_date']),
        ]
        verbose_name = 'Invoice Payment'
        verbose_name_plural = 'Invoice Payments'

    def __str__(self):
        return f"Payment {self.amount} for {self.invoice.invoice_number}"