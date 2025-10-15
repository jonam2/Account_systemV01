"""Import all models to make them discoverable by Django"""
from layers.models.user_models import User
from layers.models.product_models import Product, Category
from layers.models.contact_models import Contact
from layers.models.warehouse_models import Warehouse, Stock, StockMovement
from .invoice_models import Invoice, InvoiceItem, InvoicePayment

__all__ = [
    'User',
    'Product', 'Category',
    'Contact',
    'Warehouse', 'Stock', 'StockMovement',
    'Invoice', 'InvoiceItem', 'InvoicePayment',
]

"""
Models Package - Centralized model imports
All models are registered here for Django to discover them
"""

# Import all models to register them with Django
# Order matters - import models without dependencies first

# User models
from .user_models import User

# Product models
from .product_models import Product, Category

# Contact models
from .contact_models import Contact

# Warehouse models
from .warehouse_models import Warehouse, Stock

# Invoice models
from .invoice_models import Invoice, InvoiceItem, InvoicePayment


# Export all models
__all__ = [
    # User models
    'User',
    'Role',
    
    # Product models
    'Product',
    'Category',
    
    # Contact models
    'Contact',
    
    # Warehouse models
    'Warehouse',
    'Stock',
    
    # Invoice models
    'Invoice',
    'InvoiceItem',
    'InvoicePayment',
]