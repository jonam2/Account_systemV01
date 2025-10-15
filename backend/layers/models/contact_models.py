"""Contact database models - Customers & Suppliers"""
from django.db import models
from core.models import TimeStampedModel


class Contact(TimeStampedModel):
    """Unified model for Customers and Suppliers"""
    
    class ContactType(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        SUPPLIER = 'supplier', 'Supplier'
        BOTH = 'both', 'Both'
    
    class PaymentTerms(models.TextChoices):
        CASH = 'cash', 'Cash'
        NET_15 = 'net_15', 'Net 15 Days'
        NET_30 = 'net_30', 'Net 30 Days'
        NET_60 = 'net_60', 'Net 60 Days'
        NET_90 = 'net_90', 'Net 90 Days'
    
    # Basic Information
    contact_type = models.CharField(
        max_length=10,
        choices=ContactType.choices,
        default=ContactType.CUSTOMER
    )
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    
    # Contact Details
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Address Information
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default='Turkey')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Business Information
    tax_number = models.CharField(max_length=50, blank=True)
    tax_office = models.CharField(max_length=100, blank=True)
    
    # Financial Settings
    currency = models.CharField(max_length=3, default='TRY')
    payment_terms = models.CharField(
        max_length=10,
        choices=PaymentTerms.choices,
        default=PaymentTerms.CASH
    )
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Maximum credit allowed'
    )
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Current account balance (+ receivable, - payable)'
    )
    
    # Contact Person
    contact_person = models.CharField(max_length=100, blank=True)
    contact_person_phone = models.CharField(max_length=20, blank=True)
    contact_person_email = models.EmailField(blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contacts'
    )
    
    class Meta:
        db_table = 'contacts'
        ordering = ['-created_at']
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        indexes = [
            models.Index(fields=['contact_type', 'is_active']),
            models.Index(fields=['code']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_customer(self):
        """Check if contact is a customer"""
        return self.contact_type in [self.ContactType.CUSTOMER, self.ContactType.BOTH]
    
    @property
    def is_supplier(self):
        """Check if contact is a supplier"""
        return self.contact_type in [self.ContactType.SUPPLIER, self.ContactType.BOTH]
    
    @property
    def available_credit(self):
        """Calculate available credit"""
        if self.credit_limit > 0:
            return self.credit_limit - self.current_balance
        return 0
    
    @property
    def is_over_credit_limit(self):
        """Check if contact exceeded credit limit"""
        return self.current_balance > self.credit_limit if self.credit_limit > 0 else False
    
    def update_balance(self, amount):
        """
        Update current balance
        Positive amount = increase receivable/decrease payable
        Negative amount = decrease receivable/increase payable
        """
        self.current_balance += amount
        self.save(update_fields=['current_balance', 'updated_at'])