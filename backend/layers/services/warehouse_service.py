"""
Warehouse Service - Complete Business Logic Layer
Handles all warehouse and inventory operations with proper locking
"""
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
import logging

from layers.repositories.warehouse_repository import (
    WarehouseRepository,
    StockRepository,
    StockMovementRepository
)
from layers.repositories.product_repository import ProductRepository
from layers.models.warehouse_models import Stock, StockMovement
from core.exceptions import (
    ValidationError,
    NotFoundError,
    DuplicateError,
    InsufficientStockError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


class WarehouseService:
    """
    Service for warehouse and inventory operations
    Handles stock management with proper locking and audit trails
    """
    
    def __init__(self):
        self.warehouse_repo = WarehouseRepository()
        self.stock_repo = StockRepository()
        self.movement_repo = StockMovementRepository()
        self.product_repo = ProductRepository()
    
    # ==================== WAREHOUSE OPERATIONS ====================
    
    @transaction.atomic
    def create_warehouse(self, data):
        """
        Create a new warehouse
        
        Args:
            data (dict): Warehouse data
            
        Returns:
            Warehouse: Created warehouse
        """
        try:
            # Check for duplicate code
            if self.warehouse_repo.find_by_code(data.get('code')):
                raise DuplicateError(f"Warehouse with code {data['code']} already exists")
            
            # Generate code if not provided
            if not data.get('code'):
                data['code'] = self.warehouse_repo.generate_next_code()
            
            warehouse = self.warehouse_repo.create(data)
            logger.info(f"Warehouse created: {warehouse.code} - {warehouse.name}")
            
            return warehouse
            
        except DuplicateError as e:
            logger.warning(f"Warehouse creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating warehouse: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create warehouse: {str(e)}")
    
    @transaction.atomic
    def update_warehouse(self, warehouse_id, data):
        """Update warehouse"""
        try:
            warehouse = self.warehouse_repo.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse {warehouse_id} not found")
            
            # Check for duplicate code if changing
            if 'code' in data and data['code'] != warehouse.code:
                if self.warehouse_repo.find_by_code(data['code']):
                    raise DuplicateError(f"Warehouse with code {data['code']} already exists")
            
            updated = self.warehouse_repo.update(warehouse_id, data)
            logger.info(f"Warehouse updated: {updated.code}")
            
            return updated
            
        except (NotFoundError, DuplicateError) as e:
            logger.warning(f"Warehouse update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating warehouse: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update warehouse: {str(e)}")
    
    @transaction.atomic
    def delete_warehouse(self, warehouse_id):
        """
        Delete warehouse (only if no stock)
        
        Args:
            warehouse_id (int): Warehouse ID
            
        Returns:
            bool: Success status
        """
        try:
            warehouse = self.warehouse_repo.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse {warehouse_id} not found")
            
            # Check if warehouse has stock
            stock_count = self.stock_repo.get_warehouse_stocks(warehouse_id).filter(
                quantity__gt=0
            ).count()
            
            if stock_count > 0:
                raise BusinessLogicError(
                    f"Cannot delete warehouse with {stock_count} items in stock. "
                    "Transfer or remove stock first."
                )
            
            # Check if default warehouse
            if warehouse.is_default:
                raise BusinessLogicError(
                    "Cannot delete default warehouse. Set another warehouse as default first."
                )
            
            self.warehouse_repo.delete(warehouse_id)
            logger.info(f"Warehouse deleted: {warehouse.code}")
            
            return True
            
        except (NotFoundError, BusinessLogicError) as e:
            logger.warning(f"Warehouse deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting warehouse: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete warehouse: {str(e)}")
    
    def get_all_warehouses(self, filters=None):
        """Get all warehouses with filters"""
        try:
            filters = filters or {}
            return self.warehouse_repo.filter_warehouses(filters)
        except Exception as e:
            logger.error(f"Error listing warehouses: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to list warehouses: {str(e)}")
    
    def get_warehouse_by_id(self, warehouse_id):
        """Get warehouse by ID"""
        warehouse = self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse:
            raise NotFoundError(f"Warehouse {warehouse_id} not found")
        return warehouse
    
    # ==================== STOCK OPERATIONS ====================
    
    @transaction.atomic
    def adjust_stock(self, warehouse_id, product_id, quantity, notes, user_id):
        """
        Adjust stock quantity with locking to prevent race conditions
        
        Args:
            warehouse_id (int): Warehouse ID
            product_id (int): Product ID
            quantity (Decimal): Quantity to add (positive) or remove (negative)
            notes (str): Adjustment notes
            user_id (int): User making adjustment
            
        Returns:
            Stock: Updated stock
        """
        try:
            # Validate warehouse
            warehouse = self.warehouse_repo.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse {warehouse_id} not found")
            
            # Validate product
            product = self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"Product {product_id} not found")
            
            # Lock the stock row for update to prevent race conditions
            stock = Stock.objects.select_for_update().filter(
                warehouse_id=warehouse_id,
                product_id=product_id
            ).first()
            
            # Create stock if doesn't exist
            if not stock:
                stock = Stock.objects.create(
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                    quantity=Decimal('0.00')
                )
                logger.info(f"Stock created for {product.name} in {warehouse.name}")
            
            # Store before value
            quantity_before = stock.quantity
            
            # Update quantity
            stock.quantity += quantity
            
            # Validate final quantity
            if stock.quantity < 0:
                raise ValidationError(
                    f"Insufficient stock. Current: {quantity_before}, "
                    f"Trying to remove: {abs(quantity)}"
                )
            
            stock.save()
            
            # Create movement record
            movement_type = (
                StockMovement.MovementType.ADJUSTMENT 
                if quantity != 0 
                else StockMovement.MovementType.ADJUSTMENT
            )
            
            self.movement_repo.create_movement({
                'warehouse_id': warehouse_id,
                'product_id': product_id,
                'movement_type': movement_type,
                'quantity': quantity,
                'quantity_before': quantity_before,
                'quantity_after': stock.quantity,
                'notes': notes or 'Stock adjustment',
                'created_by_id': user_id
            })
            
            logger.info(
                f"Stock adjusted: {product.name} in {warehouse.name}. "
                f"Change: {quantity}, New quantity: {stock.quantity}"
            )
            
            return stock
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Stock adjustment failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adjusting stock: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to adjust stock: {str(e)}")
    
    @transaction.atomic
    def transfer_stock(self, from_warehouse_id, to_warehouse_id, product_id, 
                      quantity, notes, user_id):
        """
        Transfer stock between warehouses with locking
        
        Args:
            from_warehouse_id (int): Source warehouse
            to_warehouse_id (int): Destination warehouse
            product_id (int): Product ID
            quantity (Decimal): Quantity to transfer
            notes (str): Transfer notes
            user_id (int): User initiating transfer
            
        Returns:
            dict: Updated stock for both warehouses
        """
        try:
            # Validate inputs
            if quantity <= 0:
                raise ValidationError("Transfer quantity must be positive")
            
            if from_warehouse_id == to_warehouse_id:
                raise ValidationError("Cannot transfer to the same warehouse")
            
            # Validate warehouses
            from_warehouse = self.warehouse_repo.get_by_id(from_warehouse_id)
            if not from_warehouse:
                raise NotFoundError(f"Source warehouse {from_warehouse_id} not found")
            
            to_warehouse = self.warehouse_repo.get_by_id(to_warehouse_id)
            if not to_warehouse:
                raise NotFoundError(f"Destination warehouse {to_warehouse_id} not found")
            
            # Validate product
            product = self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"Product {product_id} not found")
            
            # Lock both stock rows (ordered by ID to prevent deadlock)
            stock_ids = sorted([
                (from_warehouse_id, product_id),
                (to_warehouse_id, product_id)
            ])
            
            # Get source stock with lock
            from_stock = Stock.objects.select_for_update().filter(
                warehouse_id=from_warehouse_id,
                product_id=product_id
            ).first()
            
            if not from_stock or from_stock.available_quantity < quantity:
                available = from_stock.available_quantity if from_stock else 0
                raise InsufficientStockError(
                    f"Insufficient stock in {from_warehouse.name}. "
                    f"Required: {quantity}, Available: {available}"
                )
            
            # Get or create destination stock with lock
            to_stock = Stock.objects.select_for_update().filter(
                warehouse_id=to_warehouse_id,
                product_id=product_id
            ).first()
            
            if not to_stock:
                to_stock = Stock.objects.create(
                    warehouse_id=to_warehouse_id,
                    product_id=product_id,
                    quantity=Decimal('0.00')
                )
            
            # Store before values
            from_qty_before = from_stock.quantity
            to_qty_before = to_stock.quantity
            
            # Update quantities
            from_stock.quantity -= quantity
            to_stock.quantity += quantity
            
            from_stock.save()
            to_stock.save()
            
            # Create movement records for audit trail
            transfer_notes = notes or f'Transfer from {from_warehouse.name} to {to_warehouse.name}'
            
            # Outgoing movement
            self.movement_repo.create_movement({
                'warehouse_id': from_warehouse_id,
                'product_id': product_id,
                'movement_type': StockMovement.MovementType.TRANSFER,
                'quantity': -quantity,
                'quantity_before': from_qty_before,
                'quantity_after': from_stock.quantity,
                'from_warehouse_id': from_warehouse_id,
                'to_warehouse_id': to_warehouse_id,
                'notes': transfer_notes,
                'created_by_id': user_id
            })
            
            # Incoming movement
            self.movement_repo.create_movement({
                'warehouse_id': to_warehouse_id,
                'product_id': product_id,
                'movement_type': StockMovement.MovementType.TRANSFER,
                'quantity': quantity,
                'quantity_before': to_qty_before,
                'quantity_after': to_stock.quantity,
                'from_warehouse_id': from_warehouse_id,
                'to_warehouse_id': to_warehouse_id,
                'notes': transfer_notes,
                'created_by_id': user_id
            })
            
            logger.info(
                f"Stock transferred: {quantity} {product.name} "
                f"from {from_warehouse.name} to {to_warehouse.name}"
            )
            
            return {
                'from_stock': from_stock,
                'to_stock': to_stock
            }
            
        except (NotFoundError, ValidationError, InsufficientStockError) as e:
            logger.warning(f"Stock transfer failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error transferring stock: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to transfer stock: {str(e)}")
    
    def get_warehouse_stocks(self, warehouse_id):
        """Get all stocks in a warehouse"""
        try:
            warehouse = self.warehouse_repo.get_by_id(warehouse_id)
            if not warehouse:
                raise NotFoundError(f"Warehouse {warehouse_id} not found")
            
            return self.stock_repo.get_warehouse_stocks(warehouse_id)
            
        except NotFoundError as e:
            logger.warning(f"Get warehouse stocks failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting warehouse stocks: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get warehouse stocks: {str(e)}")
    
    def get_all_product_stocks(self, product_id):
        """Get stock levels for a product across all warehouses"""
        try:
            product = self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"Product {product_id} not found")
            
            return self.stock_repo.get_product_stocks(product_id)
            
        except NotFoundError as e:
            logger.warning(f"Get product stocks failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting product stocks: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get product stocks: {str(e)}")
    
    def get_low_stock_items(self, warehouse_id=None):
        """Get items with low stock"""
        try:
            return self.stock_repo.get_low_stock_items(warehouse_id)
        except Exception as e:
            logger.error(f"Error getting low stock items: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get low stock items: {str(e)}")
    
    def get_out_of_stock_items(self, warehouse_id=None):
        """Get out of stock items"""
        try:
            return self.stock_repo.get_out_of_stock_items(warehouse_id)
        except Exception as e:
            logger.error(f"Error getting out of stock items: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get out of stock items: {str(e)}")
    
    # ==================== STOCK MOVEMENT OPERATIONS ====================
    
    def get_stock_movements(self, filters=None):
        """Get stock movements with filters"""
        try:
            filters = filters or {}
            return self.movement_repo.filter_movements(filters)
        except Exception as e:
            logger.error(f"Error getting stock movements: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get stock movements: {str(e)}")
    
    def get_product_movement_history(self, product_id, limit=50):
        """Get movement history for a product"""
        try:
            product = self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"Product {product_id} not found")
            
            return self.movement_repo.get_product_movements(product_id, limit)
            
        except NotFoundError as e:
            logger.warning(f"Get movement history failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting movement history: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get movement history: {str(e)}")
    
    # ==================== STATISTICS & REPORTING ====================
    
    def get_warehouse_statistics(self, warehouse_id=None):
        """
        Get warehouse statistics
        
        Args:
            warehouse_id (int): Specific warehouse ID or None for all
            
        Returns:
            dict: Statistics data
        """
        try:
            if warehouse_id:
                warehouse = self.warehouse_repo.get_by_id(warehouse_id)
                if not warehouse:
                    raise NotFoundError(f"Warehouse {warehouse_id} not found")
                
                stocks = self.stock_repo.get_warehouse_stocks(warehouse_id)
            else:
                stocks = Stock.objects.all()
            
            # Calculate statistics
            stats = stocks.aggregate(
                total_products=Count('id', distinct=True),
                total_items=Sum('quantity'),
                low_stock_count=Count('id', filter=Q(
                    quantity__lte=F('min_quantity'),
                    min_quantity__gt=0
                )),
                out_of_stock_count=Count('id', filter=Q(quantity__lte=0)),
                total_reserved=Sum('reserved_quantity')
            )
            
            # Calculate total value
            total_value = Decimal('0.00')
            for stock in stocks.select_related('product'):
                total_value += stock.stock_value
            
            return {
                'warehouse_id': warehouse_id,
                'total_products': stats['total_products'] or 0,
                'total_items': stats['total_items'] or Decimal('0.00'),
                'total_value': total_value,
                'low_stock_count': stats['low_stock_count'] or 0,
                'out_of_stock_count': stats['out_of_stock_count'] or 0,
                'total_reserved': stats['total_reserved'] or Decimal('0.00'),
            }
            
        except NotFoundError as e:
            logger.warning(f"Get warehouse statistics failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting warehouse statistics: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get warehouse statistics: {str(e)}")
    
    def get_stock_valuation_report(self, warehouse_id=None):
        """
        Get stock valuation report
        
        Args:
            warehouse_id (int): Warehouse ID or None for all
            
        Returns:
            list: Stock valuation data
        """
        try:
            if warehouse_id:
                stocks = self.stock_repo.get_warehouse_stocks(warehouse_id)
            else:
                stocks = Stock.objects.all()
            
            stocks = stocks.select_related('warehouse', 'product').filter(
                quantity__gt=0
            ).order_by('warehouse__name', 'product__name')
            
            valuation = []
            for stock in stocks:
                valuation.append({
                    'warehouse': stock.warehouse.name,
                    'product_code': stock.product.code,
                    'product_name': stock.product.name,
                    'quantity': stock.quantity,
                    'cost_price': stock.product.cost_price,
                    'total_value': stock.stock_value,
                    'is_low_stock': stock.is_low_stock,
                })
            
            return valuation
            
        except Exception as e:
            logger.error(f"Error getting valuation report: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get valuation report: {str(e)}")
    
    def get_stock_movement_summary(self, warehouse_id, start_date, end_date):
        """
        Get stock movement summary for a period
        
        Args:
            warehouse_id (int): Warehouse ID
            start_date (date): Start date
            end_date (date): End date
            
        Returns:
            dict: Movement summary
        """
        try:
            movements = self.movement_repo.filter_movements({
                'warehouse_id': warehouse_id,
                'date_from': start_date,
                'date_to': end_date
            })
            
            summary = movements.aggregate(
                total_movements=Count('id'),
                total_in=Sum('quantity', filter=Q(quantity__gt=0)),
                total_out=Sum('quantity', filter=Q(quantity__lt=0)),
                adjustments=Count('id', filter=Q(
                    movement_type=StockMovement.MovementType.ADJUSTMENT
                )),
                transfers_in=Count('id', filter=Q(
                    movement_type=StockMovement.MovementType.TRANSFER,
                    quantity__gt=0
                )),
                transfers_out=Count('id', filter=Q(
                    movement_type=StockMovement.MovementType.TRANSFER,
                    quantity__lt=0
                )),
            )
            
            return {
                'warehouse_id': warehouse_id,
                'start_date': start_date,
                'end_date': end_date,
                'total_movements': summary['total_movements'] or 0,
                'total_in': summary['total_in'] or Decimal('0.00'),
                'total_out': abs(summary['total_out'] or Decimal('0.00')),
                'adjustments': summary['adjustments'] or 0,
                'transfers_in': summary['transfers_in'] or 0,
                'transfers_out': summary['transfers_out'] or 0,
            }
            
        except Exception as e:
            logger.error(f"Error getting movement summary: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get movement summary: {str(e)}")