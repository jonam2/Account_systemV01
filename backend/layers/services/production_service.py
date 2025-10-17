from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from layers.repositories.production_repository import ProductionRepository
from layers.repositories.warehouse_repository import WarehouseRepository
from layers.models.warehouse_models import Stock, StockMovement
from layers.models.production_models import BillOfMaterials, ProductionOrder, ProductionOrderItem
from core.exceptions import ValidationError, NotFoundError
import uuid


class ProductionService:
    """Business logic for production operations"""
    
    def __init__(self):
        self.production_repo = ProductionRepository()
        self.warehouse_repo = WarehouseRepository()
    
    # ==================== BOM Operations ====================
    
    def create_bom(self, data, components_data, user):
        """Create a new Bill of Materials"""
        # Validate product exists and is assembleable
        from layers.models.product_models import Product
        
        try:
            product = Product.objects.get(id=data['product_id'])
        except Product.DoesNotExist:
            raise NotFoundError("Product not found")
        
        if not product.is_assembleable:
            raise ValidationError(
                "Product must be marked as assembleable to create BOM"
            )
        
        # Check for duplicate active BOM
        existing_bom = BillOfMaterials.objects.filter(
            product=product,
            version=data.get('version', '1.0'),
            is_deleted=False
        ).first()
        
        if existing_bom:
            raise ValidationError(
                f"BOM version {data.get('version')} already exists for this product"
            )
        
        # Validate components
        self._validate_bom_components(components_data, product.id)
        
        # Calculate costs
        self._calculate_component_costs(components_data)
        
        # Create BOM
        bom = self.production_repo.create_bom(data, components_data)
        
        return bom
    
    def update_bom(self, bom_id, data, components_data, user):
        """Update BOM"""
        bom = self.production_repo.get_bom_by_id(bom_id)
        
        # If updating components, validate them
        if components_data is not None:
            self._validate_bom_components(components_data, bom.product.id)
            self._calculate_component_costs(components_data)
        
        return self.production_repo.update_bom(bom_id, data, components_data)
    
    def delete_bom(self, bom_id, user):
        """Delete BOM"""
        # Check if BOM is used in any production orders
        active_orders = ProductionOrder.objects.filter(
            bom_id=bom_id,
            status__in=['draft', 'confirmed', 'in_progress'],
            is_deleted=False
        ).exists()
        
        if active_orders:
            raise ValidationError(
                "Cannot delete BOM with active production orders"
            )
        
        return self.production_repo.delete_bom(bom_id)
    
    def get_bom_details(self, bom_id):
        """Get BOM with full details"""
        return self.production_repo.get_bom_by_id(bom_id)
    
    def list_boms(self, filters=None):
        """List BOMs"""
        return self.production_repo.list_boms(filters)
    
    def check_component_availability(self, bom_id, quantity, warehouse_id):
        """Check if components are available"""
        return self.production_repo.check_component_availability(
            bom_id, quantity, warehouse_id
        )
    
    # ==================== Assembly Operations ====================
    
    @transaction.atomic
    def create_assembly_order(self, data, user):
        """Create assembly/production order"""
        from layers.models.production_models import ProductionOrder, ProductionOrderItem
        from layers.models.product_models import Product
        
        # Validate product
        try:
            product = Product.objects.get(id=data['product_id'])
        except Product.DoesNotExist:
            raise NotFoundError("Product not found")
        
        if not product.is_assembleable:
            raise ValidationError("Product is not assembleable")
        
        # Get active BOM
        try:
            bom = self.production_repo.get_active_bom_for_product(data['product_id'])
        except NotFoundError:
            raise ValidationError("No active BOM found for this product")
        
        # Generate order number
        order_number = self._generate_production_number('ASM')
        
        # Check component availability
        availability = self.check_component_availability(
            bom.id,
            data['planned_quantity'],
            data['warehouse_id']
        )
        
        insufficient = [a for a in availability if not a['is_available']]
        if insufficient and not data.get('force', False):
            raise ValidationError({
                'message': 'Insufficient components',
                'details': insufficient
            })
        
        # Create production order
        order_data = {
            'order_number': order_number,
            'order_type': 'assembly',
            'status': 'draft',
            'product_id': data['product_id'],
            'bom_id': bom.id,
            'planned_quantity': data['planned_quantity'],
            'warehouse_id': data['warehouse_id'],
            'scheduled_date': data.get('scheduled_date', timezone.now().date()),
            'labor_cost': data.get('labor_cost', bom.labor_cost),
            'overhead_cost': data.get('overhead_cost', bom.overhead_cost),
            'created_by': user,
            'notes': data.get('notes', ''),
        }
        
        order = self.production_repo.create_production_order(order_data)
        
        # Create order items from BOM components
        total_material_cost = Decimal('0')
        for component in bom.components.filter(is_deleted=False):
            planned_qty = component.quantity * data['planned_quantity']
            
            # Get current unit cost from stock
            stock = Stock.objects.filter(
                product=component.component,
                warehouse_id=data['warehouse_id']
            ).first()
            
            unit_cost = stock.unit_cost if stock else component.unit_cost
            
            item_data = {
                'product': component.component,
                'planned_quantity': planned_qty,
                'unit_cost': unit_cost,
                'total_cost': planned_qty * unit_cost,
            }
            
            ProductionOrderItem.objects.create(
                production_order=order,
                **item_data
            )
            
            total_material_cost += item_data['total_cost']
        
        # Update order material cost
        order.material_cost = total_material_cost
        order.save()
        
        return order
    
    @transaction.atomic
    def confirm_assembly_order(self, order_id, user):
        """Confirm assembly order and reserve stock"""
        order = self.production_repo.get_production_order_by_id(order_id)
        
        if order.status != 'draft':
            raise ValidationError("Only draft orders can be confirmed")
        
        if order.order_type != 'assembly':
            raise ValidationError("Not an assembly order")
        
        # Reserve stock for components
        for item in order.items.filter(is_deleted=False):
            stock = Stock.objects.filter(
                product=item.product,
                warehouse=order.warehouse
            ).first()
            
            if not stock or stock.available_quantity < item.planned_quantity:
                raise ValidationError(
                    f"Insufficient stock for {item.product.name}"
                )
            
            # Reserve quantity
            stock.reserved_quantity += item.planned_quantity
            stock.save()
            
            item.reserved = True
            item.reservation_id = f"PROD-{order.order_number}-{item.id}"
            item.save()
        
        # Update order status
        order.status = 'confirmed'
        order.save()
        
        return order
    
    @transaction.atomic
    def start_assembly_order(self, order_id, user):
        """Start assembly process"""
        order = self.production_repo.get_production_order_by_id(order_id)
        
        if order.status != 'confirmed':
            raise ValidationError("Order must be confirmed first")
        
        order.status = 'in_progress'
        order.started_at = timezone.now()
        order.save()
        
        return order
    
    @transaction.atomic
    def complete_assembly_order(self, order_id, actual_quantity, actual_components, user):
        """Complete assembly and update inventory"""
        order = self.production_repo.get_production_order_by_id(order_id)
        
        if order.status != 'in_progress':
            raise ValidationError("Order must be in progress")
        
        if order.order_type != 'assembly':
            raise ValidationError("Not an assembly order")
        
        # Update actual quantity (for variable yield)
        order.actual_quantity = Decimal(str(actual_quantity))
        order.completed_at = timezone.now()
        order.completed_by = user
        
        # Process component consumption
        for item_data in actual_components:
            item = order.items.get(id=item_data['item_id'])
            actual_qty = Decimal(str(item_data['actual_quantity']))
            
            # Update item actual quantity
            item.actual_quantity = actual_qty
            item.save()
            
            # Remove from stock
            stock = Stock.objects.get(
                product=item.product,
                warehouse=order.warehouse
            )
            
            # Release reservation
            stock.reserved_quantity -= item.planned_quantity
            # Deduct actual consumption
            stock.quantity -= actual_qty
            stock.save()
            
            # Create stock movement (consumption)
            StockMovement.objects.create(
                stock=stock,
                movement_type='production_consume',
                quantity=-actual_qty,
                reference_type='production_order',
                reference_id=str(order.id),
                notes=f"Assembly Order {order.order_number}",
                created_by=user
            )
        
        # Add finished product to stock
        finished_stock, created = Stock.objects.get_or_create(
            product=order.product,
            warehouse=order.warehouse,
            defaults={
                'quantity': 0,
                'reserved_quantity': 0,
                'unit_cost': order.total_cost / order.actual_quantity
            }
        )
        
        finished_stock.quantity += order.actual_quantity
        finished_stock.unit_cost = order.total_cost / order.actual_quantity
        finished_stock.save()
        
        # Create stock movement (production)
        StockMovement.objects.create(
            stock=finished_stock,
            movement_type='production_output',
            quantity=order.actual_quantity,
            reference_type='production_order',
            reference_id=str(order.id),
            notes=f"Assembly Order {order.order_number}",
            created_by=user
        )
        
        # Update order status
        order.status = 'completed'
        order.save()
        
        return order
    
    # ==================== Disassembly Operations ====================
    
    @transaction.atomic
    def create_disassembly_order(self, data, user):
        """Create disassembly order for phased disassembly"""
        from layers.models.production_models import ProductionOrder, ProductionOrderItem
        from layers.models.product_models import Product
        
        # Validate product
        try:
            product = Product.objects.get(id=data['product_id'])
        except Product.DoesNotExist:
            raise NotFoundError("Product not found")
        
        if not product.is_assembleable:
            raise ValidationError("Product is not assembleable/disassembleable")
        
        # Get BOM for disassembly
        try:
            bom = self.production_repo.get_active_bom_for_product(data['product_id'])
        except NotFoundError:
            raise ValidationError("No BOM found for disassembly")
        
        # Check if product is in stock
        stock = Stock.objects.filter(
            product=product,
            warehouse_id=data['warehouse_id']
        ).first()
        
        if not stock or stock.available_quantity < data['planned_quantity']:
            raise ValidationError("Insufficient stock for disassembly")
        
        # Generate order number
        order_number = self._generate_production_number('DIS')
        
        # Determine phase (for phased disassembly)
        phase = data.get('phase', 1)
        parent_order_id = data.get('parent_order_id')
        
        # Create disassembly order
        order_data = {
            'order_number': order_number,
            'order_type': 'disassembly',
            'status': 'draft',
            'product_id': data['product_id'],
            'bom_id': bom.id,
            'planned_quantity': data['planned_quantity'],
            'warehouse_id': data['warehouse_id'],
            'scheduled_date': data.get('scheduled_date', timezone.now().date()),
            'created_by': user,
            'notes': data.get('notes', ''),
            'parent_order_id': parent_order_id,
            'phase': phase,
        }
        
        order = self.production_repo.create_production_order(order_data)
        
        # Create order items from BOM (components to be recovered)
        for component in bom.components.filter(is_deleted=False).order_by('-sequence'):
            expected_qty = component.quantity * data['planned_quantity']
            
            item_data = {
                'product': component.component,
                'planned_quantity': expected_qty,
                'unit_cost': component.unit_cost,
                'total_cost': 0,  # No cost for disassembly
            }
            
            ProductionOrderItem.objects.create(
                production_order=order,
                **item_data
            )
        
        return order
    
    @transaction.atomic
    def complete_disassembly_order(self, order_id, actual_components, user):
        """Complete disassembly and return components to inventory"""
        order = self.production_repo.get_production_order_by_id(order_id)
        
        if order.status != 'in_progress':
            raise ValidationError("Order must be in progress")
        
        if order.order_type != 'disassembly':
            raise ValidationError("Not a disassembly order")
        
        # Remove assembled product from stock
        product_stock = Stock.objects.get(
            product=order.product,
            warehouse=order.warehouse
        )
        
        product_stock.quantity -= order.planned_quantity
        product_stock.save()
        
        # Create stock movement (consumption)
        StockMovement.objects.create(
            stock=product_stock,
            movement_type='production_consume',
            quantity=-order.planned_quantity,
            reference_type='production_order',
            reference_id=str(order.id),
            notes=f"Disassembly Order {order.order_number}",
            created_by=user
        )
        
        # Add recovered components to stock
        for item_data in actual_components:
            item = order.items.get(id=item_data['item_id'])
            actual_qty = Decimal(str(item_data['actual_quantity']))
            
            # Update item actual quantity
            item.actual_quantity = actual_qty
            item.save()
            
            # Add to stock
            component_stock, created = Stock.objects.get_or_create(
                product=item.product,
                warehouse=order.warehouse,
                defaults={
                    'quantity': 0,
                    'reserved_quantity': 0,
                    'unit_cost': item.unit_cost
                }
            )
            
            component_stock.quantity += actual_qty
            component_stock.save()
            
            # Create stock movement (recovery)
            StockMovement.objects.create(
                stock=component_stock,
                movement_type='production_output',
                quantity=actual_qty,
                reference_type='production_order',
                reference_id=str(order.id),
                notes=f"Disassembly Order {order.order_number} - Phase {order.phase}",
                created_by=user
            )
        
        # Update order
        order.status = 'completed'
        order.completed_at = timezone.now()
        order.completed_by = user
        order.actual_quantity = order.planned_quantity
        order.save()
        
        return order
    
    @transaction.atomic
    def cancel_production_order(self, order_id, user):
        """Cancel production order and release reservations"""
        order = self.production_repo.get_production_order_by_id(order_id)
        
        if order.status in ['completed', 'cancelled']:
            raise ValidationError(f"Cannot cancel {order.status} order")
        
        # Release stock reservations
        for item in order.items.filter(reserved=True):
            stock = Stock.objects.filter(
                product=item.product,
                warehouse=order.warehouse
            ).first()
            
            if stock:
                stock.reserved_quantity -= item.planned_quantity
                stock.save()
            
            item.reserved = False
            item.save()
        
        order.status = 'cancelled'
        order.save()
        
        return order
    
    # ==================== Statistics & Reports ====================
    
    def get_production_statistics(self, filters=None):
        """Get production statistics"""
        stats = self.production_repo.get_production_statistics(filters)
        
        # Calculate efficiency
        if stats['total_orders'] > 0:
            stats['completion_rate'] = (
                stats['completed_orders'] / stats['total_orders']
            ) * 100
        else:
            stats['completion_rate'] = 0
        
        return stats
    
    def get_production_history(self, product_id, limit=10):
        """Get production history for a product"""
        return self.production_repo.get_production_history(product_id, limit)
    
    def get_bom_cost_breakdown(self, bom_id):
        """Get detailed cost breakdown for BOM"""
        bom = self.production_repo.get_bom_by_id(bom_id)
        
        components_cost = []
        for component in bom.components.filter(is_deleted=False):
            components_cost.append({
                'component': component.component.name,
                'quantity': component.quantity,
                'unit_cost': component.unit_cost,
                'total_cost': component.total_cost,
                'is_variable': component.is_variable,
            })
        
        return {
            'product': bom.product.name,
            'components': components_cost,
            'material_cost': bom.estimated_material_cost,
            'labor_cost': bom.labor_cost,
            'overhead_cost': bom.overhead_cost,
            'total_cost_per_unit': bom.total_cost_per_unit,
            'expected_quantity': bom.expected_quantity,
            'yield_range': {
                'min': bom.min_yield,
                'max': bom.max_yield,
            }
        }
    
    # ==================== Helper Methods ====================
    
    def _validate_bom_components(self, components_data, product_id):
        """Validate BOM components"""
        from layers.models.product_models import Product
        
        if not components_data:
            raise ValidationError("BOM must have at least one component")
        
        # Check for circular dependencies
        component_ids = [c['component_id'] for c in components_data]
        
        if product_id in component_ids:
            raise ValidationError("Product cannot be its own component")
        
        # Validate all components exist
        for comp_data in components_data:
            try:
                component = Product.objects.get(id=comp_data['component_id'])
            except Product.DoesNotExist:
                raise NotFoundError(
                    f"Component product {comp_data['component_id']} not found"
                )
    
    def _calculate_component_costs(self, components_data):
        """Calculate unit costs for components"""
        from layers.models.product_models import Product
        
        for comp_data in components_data:
            if 'unit_cost' not in comp_data or comp_data['unit_cost'] == 0:
                # Get cost from product
                product = Product.objects.get(id=comp_data['component_id'])
                comp_data['unit_cost'] = product.cost_price or 0
    
    def _generate_production_number(self, prefix='PRD'):
        """Generate unique production order number"""
        from layers.models.production_models import ProductionOrder
        
        date_str = datetime.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:8].upper()
        
        order_number = f"{prefix}-{date_str}-{random_str}"
        
        # Ensure uniqueness
        while ProductionOrder.objects.filter(order_number=order_number).exists():
            random_str = str(uuid.uuid4())[:8].upper()
            order_number = f"{prefix}-{date_str}-{random_str}"
        
        return order_number