"""
Production Service - Complete Business Logic Layer
Handles BOM, assembly, and disassembly operations
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging

from layers.repositories.production_repository import ProductionRepository
from layers.repositories.warehouse_repository import StockRepository, StockMovementRepository
from layers.models.production_models import ProductionOrder, ProductionOrderItem
from layers.models.warehouse_models import StockMovement
from core.exceptions import (
    ValidationError,
    NotFoundError,
    InsufficientStockError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


class ProductionService:
    """Service for production operations"""
    
    def __init__(self):
        self.production_repo = ProductionRepository()
        self.stock_repo = StockRepository()
        self.movement_repo = StockMovementRepository()
    
    # ==================== BOM OPERATIONS ====================
    
    @transaction.atomic
    def create_bom(self, data, components_data, user):
        """
        Create Bill of Materials
        
        Args:
            data (dict): BOM data
            components_data (list): List of components
            user: User creating BOM
            
        Returns:
            BillOfMaterials: Created BOM
        """
        try:
            # Validate product
            if not data.get('product_id'):
                raise ValidationError("Product is required")
            
            # Validate components
            if not components_data or len(components_data) == 0:
                raise ValidationError("BOM must have at least one component")
            
            # Deactivate other BOMs for this product if making this active
            if data.get('is_active', True):
                from layers.models import BillOfMaterials
                BillOfMaterials.objects.filter(
                    product_id=data['product_id'],
                    is_active=True
                ).update(is_active=False)
            
            bom = self.production_repo.create_bom(data, components_data)
            
            logger.info(f"BOM created for product {bom.product.name} v{bom.version}")
            return bom
            
        except ValidationError as e:
            logger.warning(f"BOM creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating BOM: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create BOM: {str(e)}")
    
    @transaction.atomic
    def update_bom(self, bom_id, data, components_data, user):
        """Update BOM"""
        try:
            return self.production_repo.update_bom(bom_id, data, components_data)
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"BOM update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating BOM: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update BOM: {str(e)}")
    
    @transaction.atomic
    def delete_bom(self, bom_id, user):
        """Delete BOM"""
        try:
            return self.production_repo.delete_bom(bom_id)
        except NotFoundError as e:
            logger.warning(f"BOM deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting BOM: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete BOM: {str(e)}")
    
    def list_boms(self, filters=None):
        """List BOMs with filters"""
        return self.production_repo.list_boms(filters)
    
    def get_bom_details(self, bom_id):
        """Get BOM with details"""
        return self.production_repo.get_bom_by_id(bom_id)
    
    def check_component_availability(self, bom_id, quantity, warehouse_id):
        """Check if components are available"""
        return self.production_repo.check_component_availability(
            bom_id, quantity, warehouse_id
        )
    
    def get_bom_cost_breakdown(self, bom_id):
        """Get BOM cost breakdown"""
        try:
            bom = self.production_repo.get_bom_by_id(bom_id)
            
            components = []
            for comp in bom.components.filter(is_deleted=False):
                components.append({
                    'component': comp.component.name,
                    'quantity': comp.quantity,
                    'unit_cost': comp.unit_cost,
                    'total_cost': comp.total_cost,
                })
            
            return {
                'bom_id': bom.id,
                'product': bom.product.name,
                'version': bom.version,
                'components': components,
                'material_cost': bom.estimated_material_cost,
                'labor_cost': bom.labor_cost,
                'overhead_cost': bom.overhead_cost,
                'total_cost': bom.total_cost_per_unit,
            }
            
        except NotFoundError as e:
            logger.warning(f"Cost breakdown failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting cost breakdown: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get cost breakdown: {str(e)}")
    
    # ==================== ASSEMBLY OPERATIONS ====================
    
    @transaction.atomic
    def create_assembly_order(self, data, user):
        """
        Create assembly order
        
        Args:
            data (dict): Assembly order data
            user: User creating order
            
        Returns:
            ProductionOrder: Created order
        """
        try:
            # Validate BOM
            bom_id = data.get('bom_id')
            if not bom_id:
                raise ValidationError("BOM is required for assembly")
            
            bom = self.production_repo.get_bom_by_id(bom_id)
            
            # Generate order number
            year = timezone.now().year
            last_order = ProductionOrder.objects.filter(
                order_number__startswith=f'ASM-{year}'
            ).order_by('-order_number').first()
            
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            order_data = {
                'order_number': f'ASM-{year}-{next_num:05d}',
                'order_type': 'assembly',
                'product_id': bom.product_id,
                'bom_id': bom_id,
                'warehouse_id': data['warehouse_id'],
                'planned_quantity': data['planned_quantity'],
                'scheduled_date': data.get('scheduled_date', timezone.now().date()),
                'created_by_id': user.id,
            }
            
            # Create order
            order = self.production_repo.create_production_order(order_data)
            
            # Create order items from BOM components
            items_data = []
            for component in bom.components.filter(is_deleted=False):
                items_data.append({
                    'product_id': component.component_id,
                    'planned_quantity': component.quantity * data['planned_quantity'],
                    'unit_cost': component.unit_cost,
                })
            
            for item_data in items_data:
                self.production_repo.add_production_item(order.id, item_data)
            
            logger.info(f"Assembly order {order.order_number} created")
            return order
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Assembly order creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating assembly: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create assembly order: {str(e)}")
    
    @transaction.atomic
    def confirm_assembly_order(self, order_id, user):
        """Confirm assembly order and reserve stock"""
        try:
            order = self.production_repo.get_production_order_by_id(order_id)
            
            if order.status != 'draft':
                raise ValidationError(f"Cannot confirm order with status {order.status}")
            
            # Check component availability and reserve
            for item in order.items.filter(is_deleted=False):
                stock = self.stock_repo.get_stock(
                    order.warehouse_id,
                    item.product_id
                )
                
                if not stock or stock.available_quantity < item.planned_quantity:
                    available = stock.available_quantity if stock else 0
                    raise InsufficientStockError(
                        f"Insufficient {item.product.name}. "
                        f"Required: {item.planned_quantity}, Available: {available}"
                    )
                
                # Reserve stock
                stock.reserve(item.planned_quantity)
                item.reserved = True
                item.save()
            
            # Update order status
            order.status = 'confirmed'
            order.save()
            
            logger.info(f"Assembly order {order.order_number} confirmed")
            return order
            
        except (NotFoundError, ValidationError, InsufficientStockError) as e:
            logger.warning(f"Confirm assembly failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error confirming assembly: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to confirm assembly: {str(e)}")
    
    @transaction.atomic
    def start_assembly_order(self, order_id, user):
        """Start assembly process"""
        try:
            order = self.production_repo.get_production_order_by_id(order_id)
            
            if order.status != 'confirmed':
                raise ValidationError(f"Cannot start order with status {order.status}")
            
            order.status = 'in_progress'
            order.started_at = timezone.now()
            order.save()
            
            logger.info(f"Assembly order {order.order_number} started")
            return order
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Start assembly failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting assembly: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to start assembly: {str(e)}")
    
    @transaction.atomic
    def complete_assembly_order(self, order_id, actual_quantity, actual_components, user):
        """
        Complete assembly and update inventory
        
        Args:
            order_id (int): Production order ID
            actual_quantity (Decimal): Actual quantity produced
            actual_components (list): Actual components used
            user: User completing the order
            
        Returns:
            ProductionOrder: Completed order
        """
        try:
            order = self.production_repo.get_production_order_by_id(order_id)
            
            if order.status != 'in_progress':
                raise ValidationError(f"Cannot complete order with status {order.status}")
            
            # Update actual quantities
            order.actual_quantity = actual_quantity
            
            # Update components
            total_material_cost = Decimal('0.00')
            for comp_data in actual_components:
                item = order.items.get(product_id=comp_data['product_id'])
                item.actual_quantity = comp_data['actual_quantity']
                item.calculate_total_cost()
                item.save()
                
                total_material_cost += item.total_cost
                
                # Consume stock (decrease)
                self.stock_repo.update_stock(
                    order.warehouse_id,
                    item.product_id,
                    -item.actual_quantity
                )
                
                # Release reservation
                stock = self.stock_repo.get_stock(order.warehouse_id, item.product_id)
                if stock:
                    stock.release(item.planned_quantity)
                
                # Create movement record
                self.movement_repo.create_movement({
                    'warehouse_id': order.warehouse_id,
                    'product_id': item.product_id,
                    'movement_type': StockMovement.MovementType.PRODUCTION,
                    'quantity': -item.actual_quantity,
                    'reference_type': 'production',
                    'reference_id': order.id,
                    'reference_number': order.order_number,
                    'notes': f'Assembly: {order.order_number}',
                    'created_by_id': user.id
                })
            
            # Add produced item to stock
            self.stock_repo.update_stock(
                order.warehouse_id,
                order.product_id,
                actual_quantity
            )
            
            # Create movement record for produced item
            self.movement_repo.create_movement({
                'warehouse_id': order.warehouse_id,
                'product_id': order.product_id,
                'movement_type': StockMovement.MovementType.PRODUCTION,
                'quantity': actual_quantity,
                'reference_type': 'production',
                'reference_id': order.id,
                'reference_number': order.order_number,
                'notes': f'Assembly completed: {order.order_number}',
                'created_by_id': user.id
            })
            
            # Update order
            order.material_cost = total_material_cost
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.completed_by_id = user.id
            order.save()
            
            logger.info(f"Assembly order {order.order_number} completed")
            return order
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Complete assembly failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error completing assembly: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to complete assembly: {str(e)}")
    
    # ==================== DISASSEMBLY OPERATIONS ====================
    
    @transaction.atomic
    def create_disassembly_order(self, data, user):
        """Create disassembly order"""
        try:
            # Validate product and BOM
            bom_id = data.get('bom_id')
            if bom_id:
                bom = self.production_repo.get_bom_by_id(bom_id)
            else:
                bom = None
            
            # Generate order number
            year = timezone.now().year
            last_order = ProductionOrder.objects.filter(
                order_number__startswith=f'DIS-{year}'
            ).order_by('-order_number').first()
            
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            order_data = {
                'order_number': f'DIS-{year}-{next_num:05d}',
                'order_type': 'disassembly',
                'product_id': data['product_id'],
                'bom_id': bom_id,
                'warehouse_id': data['warehouse_id'],
                'planned_quantity': data['planned_quantity'],
                'scheduled_date': data.get('scheduled_date', timezone.now().date()),
                'created_by_id': user.id,
            }
            
            order = self.production_repo.create_production_order(order_data)
            
            logger.info(f"Disassembly order {order.order_number} created")
            return order
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Disassembly order creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating disassembly: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create disassembly order: {str(e)}")
    
    @transaction.atomic
    def complete_disassembly_order(self, order_id, actual_components, user):
        """Complete disassembly and return components to stock"""
        try:
            order = self.production_repo.get_production_order_by_id(order_id)
            
            if order.status not in ['draft', 'confirmed', 'in_progress']:
                raise ValidationError(f"Cannot complete order with status {order.status}")
            
            # Remove assembled product from stock
            self.stock_repo.update_stock(
                order.warehouse_id,
                order.product_id,
                -order.planned_quantity
            )
            
            # Create movement record for disassembled product
            self.movement_repo.create_movement({
                'warehouse_id': order.warehouse_id,
                'product_id': order.product_id,
                'movement_type': StockMovement.MovementType.PRODUCTION,
                'quantity': -order.planned_quantity,
                'reference_type': 'production',
                'reference_id': order.id,
                'reference_number': order.order_number,
                'notes': f'Disassembly: {order.order_number}',
                'created_by_id': user.id
            })
            
            # Add components back to stock
            for comp_data in actual_components:
                # Add to stock
                self.stock_repo.update_stock(
                    order.warehouse_id,
                    comp_data['product_id'],
                    comp_data['actual_quantity']
                )
                
                # Create movement record
                self.movement_repo.create_movement({
                    'warehouse_id': order.warehouse_id,
                    'product_id': comp_data['product_id'],
                    'movement_type': StockMovement.MovementType.PRODUCTION,
                    'quantity': comp_data['actual_quantity'],
                    'reference_type': 'production',
                    'reference_id': order.id,
                    'reference_number': order.order_number,
                    'notes': f'Disassembly: {order.order_number}',
                    'created_by_id': user.id
                })
            
            # Update order
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.completed_by_id = user.id
            order.save()
            
            logger.info(f"Disassembly order {order.order_number} completed")
            return order
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Complete disassembly failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error completing disassembly: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to complete disassembly: {str(e)}")
    
    # ==================== COMMON OPERATIONS ====================
    
    @transaction.atomic
    def cancel_production_order(self, order_id, user):
        """Cancel production order and release reservations"""
        try:
            order = self.production_repo.get_production_order_by_id(order_id)
            
            if order.status == 'completed':
                raise ValidationError("Cannot cancel completed order")
            
            # Release reserved stock
            for item in order.items.filter(reserved=True):
                stock = self.stock_repo.get_stock(order.warehouse_id, item.product_id)
                if stock:
                    stock.release(item.planned_quantity)
                item.reserved = False
                item.save()
            
            order.status = 'cancelled'
            order.save()
            
            logger.info(f"Production order {order.order_number} cancelled")
            return order
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Cancel order failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling order: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to cancel order: {str(e)}")
    
    def get_production_statistics(self, filters=None):
        """Get production statistics"""
        try:
            return self.production_repo.get_production_statistics(filters)
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get statistics: {str(e)}")
    
    def get_production_history(self, product_id, limit=10):
        """Get production history for a product"""
        try:
            return self.production_repo.get_production_history(product_id, limit)
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to get history: {str(e)}")