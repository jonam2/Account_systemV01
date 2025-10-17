"""
Models Package - Corrected Version
Fixed Issues:
- Removed wildcard imports to avoid circular imports
- Explicit imports for better control
- Clear __all__ definition
- Proper ordering to avoid dependency issues
"""

# Import models explicitly to avoid circular imports
# Order matters - import models without dependencies first

# User models (no dependencies)
from layers.models.user_models import User

# Product models (no dependencies)
from layers.models.product_models import Product, Category

# Contact models (depends on User)
from layers.models.contact_models import Contact

# Warehouse models (depends on Product, User)
from layers.models.warehouse_models import Warehouse, Stock, StockMovement

# Invoice models (depends on User, Product, Contact, Warehouse)
from layers.models.invoice_models import Invoice, InvoiceItem, InvoicePayment

# Order models (depends on User, Product, Contact, Warehouse, Invoice)
from layers.models.order_models import Order, OrderItem, OrderStatusHistory

# Production models (depends on Product, Warehouse, User)
from layers.models.production_models import (
    BillOfMaterials,
    BOMComponent,
    ProductionOrder,
    ProductionOrderItem,
    ProductionPhase
)

# Define what gets exported when someone does "from layers.models import *"
__all__ = [
    # User models
    'User',
    
    # Product models
    'Product',
    'Category',
    
    # Contact models
    'Contact',
    
    # Warehouse models
    'Warehouse',
    'Stock',
    'StockMovement',
    
    # Invoice models
    'Invoice',
    'InvoiceItem',
    'InvoicePayment',
    
    # Order models
    'Order',
    'OrderItem',
    'OrderStatusHistory',
    
    # Production models
    'BillOfMaterials',
    'BOMComponent',
    'ProductionOrder',
    'ProductionOrderItem',
    'ProductionPhase',
]