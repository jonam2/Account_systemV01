"""Warehouse service - Business logic layer"""
from django.db import transaction
from layers.repositories.warehouse_repository import (
    WarehouseRepository,
    StockRepository,
    StockMovementRepository
)
from layers.repositories.product_repository import ProductRepository
from core.exceptions import ValidationError, NotFoundError, DuplicateError


class WarehouseService:
    """Service for warehouse business logic"""
    
    def __init__(self):
        self.warehouse_repo = WarehouseRepository()
        self.stock_repo = StockRepository()
        self.movement_repo = StockMovementRepository()
        self.product_repo = ProductRepository()
    
    # Warehouse CRUD operations
    
    def get_all_warehouses(self, filters=None):
        """Get all warehouses with optional filters"""
        if filters:
            return self.warehouse_repo.filter_warehouses(filters)
        return self.warehouse_repo.get_all()
    
    def get_warehouse_by_id(self, warehouse_id):
        """Get warehouse by ID"""
        warehouse = self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse:
            raise NotFoundError(f"Warehouse with ID {warehouse_id} not found")
        return warehouse
    
    def create_warehouse(self, data):
        """Create new warehouse"""
        # Generate code if not provided
        if not data.get('code'):
            data['code'] = self.warehouse_repo.generate_next_code()
        
        # Check for duplicate code
        existing = self.warehouse_repo.find_by_code(data['code'])
        if existing:
            raise DuplicateError(f"Warehouse with code {data['code']} already exists")
        
        # Validate required fields
        if not data.get('name'):
            raise ValidationError("Warehouse name is required")
        
        return self.warehouse_repo.create(data)
    
    def update_warehouse(self, warehouse_id, data):
        """Update warehouse"""
        warehouse = self.get_warehouse_by_id(warehouse_id)
        
        # Check for duplicate code
        if 'code' in data and data['code'] != warehouse.code:
            existing = self.warehouse_repo.find_by_code(data['code'])
            if existing:
                raise DuplicateError(f"Warehouse with code {data['code']} already exists")
        
        return self.warehouse_repo.update(warehouse_id, data)
    
    def delete_warehouse(self, warehouse_id):
        """Delete warehouse (soft delete)"""
        warehouse = self.get_warehouse_by_id(warehouse_id)
        
        # Check if warehouse has stock
        stocks = self.stock_repo.get_warehouse_stocks(warehouse_id)
        if stocks.filter(quantity__gt=0).exists():
            raise ValidationError("Cannot delete warehouse with existing stock")
        
        self.warehouse_repo.update(warehouse_id, {'is_active': False})
    
    # Stock operations
    
    def get_product_stock(self, warehouse_id, product_id):
        """Get stock for specific product in warehouse"""
        stock = self.stock_repo.get_stock(warehouse_id, product_id)
        if not stock:
            raise NotFoundError(f"No stock found for product {product_id} in warehouse {warehouse_id}")
        return stock
    
    def get_all_product_stocks(self, product_id):
        """Get all stocks for a product across warehouses"""
        return self.stock_repo.get_product_stocks(product_id)
    
    def get_warehouse_stocks(self, warehouse_id):
        """Get all stocks in a warehouse"""
        return self.stock_repo.get_warehouse_stocks(warehouse_id)
    
    @transaction.atomic
    def adjust_stock(self, warehouse_id, product_id, quantity, notes='', user_id=None):
        """
        Adjust stock quantity (manual adjustment)
        
        Args:
            warehouse_id: Warehouse ID
            product_id: Product ID
            quantity: Quantity to add (positive) or remove (negative)
            notes: Adjustment notes
            user_id: User who made the adjustment
        """
        # Validate warehouse and product
        warehouse = self.get_warehouse_by_id(warehouse_id)
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product with ID {product_id} not found")
        
        # Get or create stock
        stock, created = self.stock_repo.update_stock(warehouse_id, product_id, 0)
        quantity_before = stock.quantity
        
        # Update stock
        stock.quantity += quantity
        if stock.quantity < 0:
            raise ValidationError("Stock quantity cannot be negative")
        
        stock.save()
        
        # Create movement record
        self.movement_repo.create_movement({
            'warehouse_id': warehouse_id,
            'product_id': product_id,
            'movement_type': 'adjustment',
            'quantity': quantity,
            'quantity_before': quantity_before,
            'quantity_after': stock.quantity,
            'notes': notes,
            'created_by_id': user_id
        })
        
        return stock
    
    @transaction.atomic
    def transfer_stock(self, from_warehouse_id, to_warehouse_id, product_id, quantity, notes='', user_id=None):
        """
        Transfer stock between warehouses
        
        Args:
            from_warehouse_id: Source warehouse ID
            to_warehouse_id: Destination warehouse ID
            product_id: Product ID
            quantity: Quantity to transfer
            notes: Transfer notes
            user_id: User who initiated transfer
        """
        if quantity <= 0:
            raise ValidationError("Transfer quantity must be positive")
        
        if from_warehouse_id == to_warehouse_id:
            raise ValidationError("Cannot transfer to the same warehouse")
        
        # Validate warehouses and product
        from_warehouse = self.get_warehouse_by_id(from_warehouse_id)
        to_warehouse = self.get_warehouse_by_id(to_warehouse_id)
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product with ID {product_id} not found")
        
        # Check source stock availability
        from_stock = self.stock_repo.get_stock(from_warehouse_id, product_id)
        if not from_stock or from_stock.available_quantity < quantity:
            raise ValidationError("Insufficient stock in source warehouse")
        
        # Update source warehouse stock
        from_qty_before = from_stock.quantity
        from_stock.quantity -= quantity
        from_stock.save()
        
        # Update destination warehouse stock
        to_stock, created = self.stock_repo.update_stock(to_warehouse_id, product_id, 0)
        to_qty_before = to_stock.quantity
        to_stock.quantity += quantity
        to_stock.save()
        
        # Create movement records (OUT from source)
        self.movement_repo.create_movement({
            'warehouse_id': from_warehouse_id,
            'product_id': product_id,
            'movement_type': 'transfer',
            'quantity': -quantity,
            'quantity_before': from_qty_before,
            'quantity_after': from_stock.quantity,
            'from_warehouse_id': from_warehouse_id,
            'to_warehouse_id': to_warehouse_id,
            'notes': notes,
            'created_by_id': user_id
        })
        
        # Create movement record (IN to destination)
        self.movement_repo.create_movement({
            'warehouse_id': to_warehouse_id,
            'product_id': product_id,
            'movement_type': 'transfer',
            'quantity': quantity,
            'quantity_before': to_qty_before,
            'quantity_after': to_stock.quantity,
            'from_warehouse_id': from_warehouse_id,
            'to_warehouse_id': to_warehouse_id,
            'notes': notes,
            'created_by_id': user_id
        })
        
        return {
            'from_stock': from_stock,
            'to_stock': to_stock
        }
    
    def get_low_stock_items(self, warehouse_id=None):
        """Get items with low stock"""
        return self.stock_repo.get_low_stock_items(warehouse_id)
    
    def get_out_of_stock_items(self, warehouse_id=None):
        """Get out of stock items"""
        return self.stock_repo.get_out_of_stock_items(warehouse_id)
    
    def get_stock_movements(self, filters=None):
        """Get stock movements with filters"""
        if filters:
            return self.movement_repo.filter_movements(filters)
        return self.movement_repo.get_all()
    
    def get_warehouse_statistics(self, warehouse_id=None):
        """Get warehouse statistics"""
        if warehouse_id:
            stocks = self.stock_repo.get_warehouse_stocks(warehouse_id)
        else:
            stocks = self.stock_repo.get_all()
        
        total_products = stocks.count()
        total_value = self.stock_repo.get_total_stock_value(warehouse_id)
        low_stock_count = self.stock_repo.get_low_stock_items(warehouse_id).count()
        out_of_stock_count = self.stock_repo.get_out_of_stock_items(warehouse_id).count()
        
        return {
            'total_products': total_products,
            'total_stock_value': float(total_value),
            'low_stock_items': low_stock_count,
            'out_of_stock_items': out_of_stock_count
        }