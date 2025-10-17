from django.db import transaction
from django.db.models import Q, Sum, Count, F, Prefetch
from layers.models.production_models import (
    BillOfMaterials, BOMComponent, ProductionOrder, 
    ProductionOrderItem, ProductionPhase
)
from layers.models.warehouse_models import Stock
from layers.models.product_models import Product
from core.exceptions import NotFoundError, ValidationError


class ProductionRepository:
    """Repository for production-related data operations"""
    
    # ==================== BOM Operations ====================
    
    @staticmethod
    def get_bom_by_id(bom_id):
        """Get BOM by ID with components"""
        try:
            return BillOfMaterials.objects.select_related(
                'product'
            ).prefetch_related(
                Prefetch(
                    'components',
                    queryset=BOMComponent.objects.select_related(
                        'component'
                    ).filter(is_deleted=False)
                )
            ).get(id=bom_id, is_deleted=False)
        except BillOfMaterials.DoesNotExist:
            raise NotFoundError(f"BOM with id {bom_id} not found")
    
    @staticmethod
    def get_active_bom_for_product(product_id):
        """Get active BOM for a product"""
        try:
            return BillOfMaterials.objects.select_related(
                'product'
            ).prefetch_related(
                Prefetch(
                    'components',
                    queryset=BOMComponent.objects.select_related(
                        'component'
                    ).filter(is_deleted=False)
                )
            ).get(
                product_id=product_id,
                is_active=True,
                is_deleted=False
            )
        except BillOfMaterials.DoesNotExist:
            raise NotFoundError(f"No active BOM found for product {product_id}")
    
    @staticmethod
    def list_boms(filters=None):
        """List all BOMs with optional filters"""
        queryset = BillOfMaterials.objects.select_related(
            'product'
        ).prefetch_related(
            'components__component'
        ).filter(is_deleted=False)
        
        if filters:
            if filters.get('product_id'):
                queryset = queryset.filter(product_id=filters['product_id'])
            if filters.get('is_active') is not None:
                queryset = queryset.filter(is_active=filters['is_active'])
            if filters.get('search'):
                search = filters['search']
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(product__name__icontains=search)
                )
        
        return queryset
    
    @staticmethod
    @transaction.atomic
    def create_bom(data, components_data):
        """Create a new BOM with components"""
        # Create BOM
        bom = BillOfMaterials.objects.create(**data)
        
        # Create components
        for comp_data in components_data:
            BOMComponent.objects.create(bom=bom, **comp_data)
        
        # Calculate estimated cost
        bom.estimated_material_cost = sum(
            comp.total_cost for comp in bom.components.all()
        )
        bom.save()
        
        return bom
    
    @staticmethod
    @transaction.atomic
    def update_bom(bom_id, data, components_data=None):
        """Update BOM and optionally its components"""
        bom = ProductionRepository.get_bom_by_id(bom_id)
        
        # Update BOM fields
        for key, value in data.items():
            setattr(bom, key, value)
        
        # Update components if provided
        if components_data is not None:
            # Soft delete existing components
            bom.components.update(is_deleted=True)
            
            # Create new components
            for comp_data in components_data:
                BOMComponent.objects.create(bom=bom, **comp_data)
            
            # Recalculate cost
            bom.estimated_material_cost = sum(
                comp.total_cost for comp in bom.components.filter(is_deleted=False)
            )
        
        bom.save()
        return bom
    
    @staticmethod
    def delete_bom(bom_id):
        """Soft delete BOM and its components"""
        bom = ProductionRepository.get_bom_by_id(bom_id)
        bom.is_deleted = True
        bom.components.update(is_deleted=True)
        bom.save()
        return bom
    
    @staticmethod
    def check_component_availability(bom_id, quantity, warehouse_id):
        """Check if components are available for production"""
        from layers.models.warehouse_models import Stock
        
        bom = ProductionRepository.get_bom_by_id(bom_id)
        availability = []
        
        for component in bom.components.filter(is_deleted=False):
            required_qty = component.quantity * quantity
            
            # Get available stock
            stock = Stock.objects.filter(
                product=component.component,
                warehouse_id=warehouse_id,
                is_deleted=False
            ).first()
            
            available_qty = stock.available_quantity if stock else 0
            
            availability.append({
                'component': component.component,
                'required_quantity': required_qty,
                'available_quantity': available_qty,
                'is_available': available_qty >= required_qty,
                'shortage': max(0, required_qty - available_qty)
            })
        
        return availability
    
    # ==================== Production Order Operations ====================
    
    @staticmethod
    def get_production_order_by_id(order_id):
        """Get production order by ID"""
        try:
            return ProductionOrder.objects.select_related(
                'product', 'warehouse', 'bom', 'created_by', 'completed_by'
            ).prefetch_related(
                Prefetch(
                    'items',
                    queryset=ProductionOrderItem.objects.select_related(
                        'product'
                    ).filter(is_deleted=False)
                ),
                'phases'
            ).get(id=order_id, is_deleted=False)
        except ProductionOrder.DoesNotExist:
            raise NotFoundError(f"Production order with id {order_id} not found")
    
    @staticmethod
    def get_production_order_by_number(order_number):
        """Get production order by order number"""
        try:
            return ProductionOrder.objects.select_related(
                'product', 'warehouse', 'bom'
            ).prefetch_related('items', 'phases').get(
                order_number=order_number,
                is_deleted=False
            )
        except ProductionOrder.DoesNotExist:
            raise NotFoundError(f"Production order {order_number} not found")
    
    @staticmethod
    def list_production_orders(filters=None):
        """List production orders with filters"""
        queryset = ProductionOrder.objects.select_related(
            'product', 'warehouse', 'bom', 'created_by'
        ).prefetch_related('items').filter(is_deleted=False)
        
        if filters:
            if filters.get('order_type'):
                queryset = queryset.filter(order_type=filters['order_type'])
            if filters.get('status'):
                queryset = queryset.filter(status=filters['status'])
            if filters.get('warehouse_id'):
                queryset = queryset.filter(warehouse_id=filters['warehouse_id'])
            if filters.get('product_id'):
                queryset = queryset.filter(product_id=filters['product_id'])
            if filters.get('date_from'):
                queryset = queryset.filter(scheduled_date__gte=filters['date_from'])
            if filters.get('date_to'):
                queryset = queryset.filter(scheduled_date__lte=filters['date_to'])
            if filters.get('search'):
                search = filters['search']
                queryset = queryset.filter(
                    Q(order_number__icontains=search) |
                    Q(product__name__icontains=search)
                )
        
        return queryset
    
    @staticmethod
    @transaction.atomic
    def create_production_order(data, items_data=None):
        """Create a new production order"""
        order = ProductionOrder.objects.create(**data)
        
        # Create items if provided
        if items_data:
            for item_data in items_data:
                ProductionOrderItem.objects.create(
                    production_order=order,
                    **item_data
                )
        
        return order
    
    @staticmethod
    @transaction.atomic
    def update_production_order(order_id, data):
        """Update production order"""
        order = ProductionRepository.get_production_order_by_id(order_id)
        
        # Only allow updates if not completed or cancelled
        if order.status in ['completed', 'cancelled']:
            raise ValidationError(
                f"Cannot update {order.status} production order"
            )
        
        for key, value in data.items():
            setattr(order, key, value)
        
        order.save()
        return order
    
    @staticmethod
    def delete_production_order(order_id):
        """Soft delete production order"""
        order = ProductionRepository.get_production_order_by_id(order_id)
        
        if order.status not in ['draft', 'cancelled']:
            raise ValidationError(
                "Only draft or cancelled orders can be deleted"
            )
        
        order.is_deleted = True
        order.items.update(is_deleted=True)
        order.save()
        return order
    
    @staticmethod
    @transaction.atomic
    def add_production_item(order_id, item_data):
        """Add item to production order"""
        order = ProductionRepository.get_production_order_by_id(order_id)
        
        if order.status != 'draft':
            raise ValidationError("Can only add items to draft orders")
        
        item = ProductionOrderItem.objects.create(
            production_order=order,
            **item_data
        )
        
        return item
    
    @staticmethod
    def get_production_statistics(filters=None):
        """Get production statistics"""
        queryset = ProductionOrder.objects.filter(is_deleted=False)
        
        if filters:
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        stats = queryset.aggregate(
            total_orders=Count('id'),
            assembly_orders=Count('id', filter=Q(order_type='assembly')),
            disassembly_orders=Count('id', filter=Q(order_type='disassembly')),
            completed_orders=Count('id', filter=Q(status='completed')),
            in_progress_orders=Count('id', filter=Q(status='in_progress')),
            total_material_cost=Sum('material_cost'),
            total_labor_cost=Sum('labor_cost'),
        )
        
        return stats
    
    @staticmethod
    def get_production_history(product_id, limit=10):
        """Get production history for a product"""
        return ProductionOrder.objects.filter(
            product_id=product_id,
            is_deleted=False
        ).select_related(
            'warehouse', 'created_by'
        ).order_by('-created_at')[:limit]
    
    # ==================== Production Phase Operations ====================
    
    @staticmethod
    @transaction.atomic
    def create_production_phase(order_id, phase_data):
        """Create a production phase"""
        order = ProductionRepository.get_production_order_by_id(order_id)
        
        phase = ProductionPhase.objects.create(
            production_order=order,
            **phase_data
        )
        
        return phase
    
    @staticmethod
    def get_phases_for_order(order_id):
        """Get all phases for a production order"""
        return ProductionPhase.objects.filter(
            production_order_id=order_id,
            is_deleted=False
        ).order_by('phase_number')