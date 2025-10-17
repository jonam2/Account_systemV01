"""
Contact Models - Corrected Version
Fixed Issues:
- Added app_label
- Added more indexes for performance
- Added database constraints
- Added helper methods
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import TimeStampedModel


class Contact(TimeStampedModel):
    """
    Unified model for Customers and Suppliers
    Supports both customer and supplier relationships
    """
    
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
        default=ContactType.CUSTOMER,
        db_index=True  # Already indexed
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique contact code'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text='Contact name'
    )
    
    # Contact Details
    email = models.EmailField(
        blank=True,
        db_index=True,  # ADDED: For email searches
        help_text='Email address'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Primary phone number'
    )
    mobile = models.CharField(
        max_length=20,
        blank=True,
        help_text='Mobile phone number'
    )
    website = models.URLField(
        blank=True,
        help_text='Company website'
    )
    
    # Address Information
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
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text='State/Province'
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
        help_text='Postal/ZIP code'
    )
    
    # Business Information
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,  # ADDED: For tax number searches
        help_text='Tax identification number'
    )
    tax_office = models.CharField(
        max_length=100,
        blank=True,
        help_text='Tax office name'
    )
    
    # Financial Settings
    currency = models.CharField(
        max_length=3,
        default='TRY',
        help_text='Default currency code (ISO 4217)'
    )
    payment_terms = models.CharField(
        max_length=10,
        choices=PaymentTerms.choices,
        default=PaymentTerms.CASH,
        help_text='Default payment terms'
    )
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Maximum credit allowed'
    )
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        db_index=True,  # ADDED: For balance queries
        help_text='Current account balance (+receivable, -payable)'
    )
    
    # Contact Person
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text='Primary contact person name'
    )
    contact_person_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact person phone'
    )
    contact_person_email = models.EmailField(
        blank=True,
        help_text='Contact person email'
    )
    
    # Additional Information
    notes = models.TextField(
        blank=True,
        help_text='Additional notes'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,  # ADDED: For active/inactive filtering
        help_text='Is this contact active?'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'layers.User',  # CHANGED: Use string reference with app label
        on_delete=models.SET_NULL,
        null=True,
        related_name='contacts_created',  # CHANGED: More consistent naming
        help_text='User who created this contact'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'contacts'
        ordering = ['-created_at']
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        indexes = [
            models.Index(fields=['contact_type', 'is_active'], name='idx_contact_type_active'),
            models.Index(fields=['code'], name='idx_contact_code'),
            models.Index(fields=['name'], name='idx_contact_name'),
            models.Index(fields=['email'], name='idx_contact_email'),  # ADDED
            models.Index(fields=['tax_number'], name='idx_contact_tax'),  # ADDED
            models.Index(fields=['current_balance'], name='idx_contact_balance'),  # ADDED
            models.Index(fields=['city', 'is_active'], name='idx_contact_city_active'),  # ADDED
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(credit_limit__gte=0),
                name='contact_credit_limit_positive'
            ),
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
        if self.credit_limit > 0 and self.is_customer:
            return max(Decimal('0.00'), self.credit_limit - self.current_balance)
        return Decimal('0.00')
    
    @property
    def is_over_credit_limit(self):
        """Check if contact exceeded credit limit"""
        if self.credit_limit > 0 and self.is_customer:
            return self.current_balance > self.credit_limit
        return False
    
    @property
    def credit_utilization_percentage(self):
        """Calculate credit utilization percentage"""
        if self.credit_limit > 0 and self.is_customer:
            return min(100, (self.current_balance / self.credit_limit) * 100)
        return 0
    
    def update_balance(self, amount):
        """
        Update current balance
        Positive amount = increase receivable/decrease payable
        Negative amount = decrease receivable/increase payable
        
        Args:
            amount (Decimal): Amount to add/subtract
        """
        self.current_balance += amount
        self.save(update_fields=['current_balance', 'updated_at'])
    
    def get_full_address(self):
        """Get formatted full address"""
        parts = [
            self.address,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join([p for p in parts if p])