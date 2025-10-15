"""User database models"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimeStampedModel
class Meta:
    db_table = 'users'
class User(AbstractUser, TimeStampedModel):
    """Custom User model"""
    
    class Roles(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        ACCOUNTANT = 'accountant', 'Accountant'
        SALES = 'sales', 'Sales'
        WAREHOUSE_MANAGER = 'warehouse_manager', 'Warehouse Manager'
    
    # Custom fields
    role = models.CharField(
        max_length=20, 
        choices=Roles.choices, 
        default=Roles.SALES
    )
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=50, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    join_date = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username