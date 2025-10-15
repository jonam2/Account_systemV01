"""Warehouse repository - Data access layer"""
from django.db.models import Q, Sum, Count, F
from layers.repositories.base_repository import BaseRepository
from layers.models.warehouse_models import Warehouse, Stock, StockMovement


class WarehouseRepository(BaseRepository):
    """Repository for Warehouse data operations"""
    
    def __init__(self):
        super().__init__(Warehouse)
    
    def find_by_code(self, code):
        """Find warehouse by code"""
        return self.model.objects.filter(code=code).first()
    
    def get_default_warehouse(self):
        """Get default warehouse"""
        return self.model.objects.filter(is_default=True, is_active=True).first()
    
    def get_active_warehouses(self):
        """Get all active warehouses"""
        return self.model.objects.filter(is_active=True)
    
    def filter_warehouses(self, filters):
        """Filter warehouses"""
        queryset = self.model.objects.all()
        
        if 'is_active' in filters:
            is_active = str(filters['is_active']).lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if 'city' in filters:
            queryset = queryset.filter(city__icontains=filters['city'])
        
        if 'search' in filters:
            search = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(city__icontains=search)
            )
        
        return queryset
    
    def generate_next_code(self):
        """Generate next warehouse code (WH-0001)"""
        last_warehouse = self.model.objects.filter(
            code__startswith='WH-'
        ).order_by('-code').first()
        
        if last_warehouse:
            try:
                last_number = int(last_warehouse.code.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1
        
        return f"WH-{next_number:04d}"


class StockRepository(BaseRepository):
    """Repository for Stock data operations"""
    
    def __init__(self):
        super().__init__(Stock)
    
    def get_stock(self, warehouse_id, product_id):
        """Get stock for specific warehouse and product"""
        return self.model.objects.filter(
            warehouse_id=warehouse_id,
            product_id=product_id
        ).first()
    
    def get_product_stocks(self, product_id):
        """Get all stocks for a product across warehouses"""
        return self.model.objects.filter(
            product_id=product_id
        ).select_related('warehouse', 'product')
    
    def get_warehouse_stocks(self, warehouse_id):
        """Get all stocks in a warehouse"""
        return self.model.objects.filter(
            warehouse_id=warehouse_id
        ).select_related('warehouse', 'product')
    
    def get_low_stock_items(self, warehouse_id=None):
        """Get items with low stock"""
        queryset = self.model.objects.filter(
            quantity__lte=F('min_quantity'),
            min_quantity__gt=0
        )
        
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        return queryset.select_related('warehouse', 'product')
    
    def get_out_of_stock_items(self, warehouse_id=None):
        """Get out of stock items"""
        queryset = self.model.objects.filter(quantity__lte=0)
        
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        return queryset.select_related('warehouse', 'product')
    
    def get_total_stock_value(self, warehouse_id=None):
        """Calculate total stock value"""
        queryset = self.model.objects.select_related('product')
        
        if warehouse_id:
            queryset = queryset.filter(warehouse_id=warehouse_id)
        
        total = 0
        for stock in queryset:
            total += stock.stock_value
        
        return total
    
    def update_stock(self, warehouse_id, product_id, quantity_change):
        """
        Update stock quantity
        Returns: (stock, created)
        """
        stock, created = self.model.objects.get_or_create(
            warehouse_id=warehouse_id,
            product_id=product_id,
            defaults={'quantity': 0}
        )
        
        stock.quantity += quantity_change
        stock.save()
        
        return stock, created
    
    def reserve_stock(self, warehouse_id, product_id, quantity):
        """Reserve stock for orders"""
        stock = self.get_stock(warehouse_id, product_id)
        if stock and stock.available_quantity >= quantity:
            stock.reserved_quantity += quantity
            stock.save()
            return True
        return False
    
    def release_reserved_stock(self, warehouse_id, product_id, quantity):
        """Release reserved stock"""
        stock = self.get_stock(warehouse_id, product_id)
        if stock:
            stock.reserved_quantity = max(0, stock.reserved_quantity - quantity)
            stock.save()
            return True
        return False


class StockMovementRepository(BaseRepository):
    """Repository for StockMovement data operations"""
    
    def __init__(self):
        super().__init__(StockMovement)
    
    def create_movement(self, data):
        """Create stock movement record"""
        return self.create(data)
    
    def get_product_movements(self, product_id, limit=None):
        """Get movements for a product"""
        queryset = self.model.objects.filter(
            product_id=product_id
        ).select_related('warehouse', 'product', 'created_by')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    def get_warehouse_movements(self, warehouse_id, limit=None):
        """Get movements for a warehouse"""
        queryset = self.model.objects.filter(
            warehouse_id=warehouse_id
        ).select_related('warehouse', 'product', 'created_by')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    def get_movements_by_reference(self, reference_type, reference_id):
        """Get movements by reference"""
        return self.model.objects.filter(
            reference_type=reference_type,
            reference_id=reference_id
        ).select_related('warehouse', 'product', 'created_by')
    
    def filter_movements(self, filters):
        """Filter stock movements"""
        queryset = self.model.objects.all()
        
        if 'warehouse_id' in filters:
            queryset = queryset.filter(warehouse_id=filters['warehouse_id'])
        
        if 'product_id' in filters:
            queryset = queryset.filter(product_id=filters['product_id'])
        
        if 'movement_type' in filters:
            queryset = queryset.filter(movement_type=filters['movement_type'])
        
        if 'date_from' in filters:
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        
        if 'date_to' in filters:
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        return queryset.select_related('warehouse', 'product', 'created_by')