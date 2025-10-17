"""
User Models - Corrected Version
Fixed Issues:
- Removed duplicate Meta class
- Added app_label
- Added proper indexes
- Added db_index to frequently queried fields
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model extending Django's AbstractUser
    Includes role-based access control and additional employee information
    """
    
    class Roles(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        ACCOUNTANT = 'accountant', 'Accountant'
        SALES = 'sales', 'Sales'
        WAREHOUSE_MANAGER = 'warehouse_manager', 'Warehouse Manager'
    
    # Role and permissions
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.SALES,
        db_index=True,  # ADDED: Index for filtering by role
        help_text='User role for access control'
    )
    
    # Contact information
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone number'
    )
    
    # Employment details
    department = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,  # ADDED: Index for filtering by department
        help_text='Department or division'
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Monthly salary'
    )
    join_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,  # ADDED: Index for date queries
        help_text='Date of joining the company'
    )
    
    # Additional information
    address = models.TextField(
        blank=True,
        help_text='Full address'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text='Profile picture'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required for models outside standard app structure
        db_table = 'users'
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [  # ADDED: Composite indexes for common queries
            models.Index(fields=['role', 'is_active'], name='idx_user_role_active'),
            models.Index(fields=['department', 'is_active'], name='idx_user_dept_active'),
            models.Index(fields=['join_date'], name='idx_user_join_date'),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """
        Get user's full name
        Returns username if first_name and last_name are empty
        """
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username
    
    @property
    def is_manager(self):
        """Check if user is a manager"""
        return self.role == self.Roles.MANAGER
    
    @property
    def is_accountant(self):
        """Check if user is an accountant"""
        return self.role == self.Roles.ACCOUNTANT
    
    @property
    def is_warehouse_manager(self):
        """Check if user is a warehouse manager"""
        return self.role == self.Roles.WAREHOUSE_MANAGER
    
    def has_role(self, *roles):
        """
        Check if user has any of the specified roles
        Usage: user.has_role('manager', 'accountant')
        """
        return self.role in roles