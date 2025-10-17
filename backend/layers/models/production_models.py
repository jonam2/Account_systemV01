"""
Production Models - Corrected Version
Fixed Issues:
- Added app_label to all models
- Fixed ALL ForeignKey references to use strings
- Added more indexes
- Added constraints
- Added helper methods
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from core.models import TimeStampedModel, SoftDeleteModel


class BillOfMaterials(TimeStampedModel, SoftDeleteModel):
    """
    Bill of Materials - Recipe for assembling a product
    Supports multi-level BOM (assembled products as components)
    """
    
    product = models.ForeignKey(
        'layers.Product',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='bom_as_product',
        help_text='Final product that will be assembled'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,  # ADDED: For searching
        help_text='BOM name/description'
    )
    name_ar = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Arabic name (optional)'
    )
    version = models.CharField(
        max_length=50,
        default='1.0',
        db_index=True,  # ADDED: For version queries
        help_text='BOM version for tracking changes'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,  # ADDED: For active filtering
        help_text='Is this BOM active?'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Additional notes'
    )
    
    # Variable yield support
    expected_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Expected output quantity (can vary in actual production)'
    )
    min_yield = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Minimum expected yield (e.g., 2 units)'
    )
    max_yield = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Maximum expected yield (e.g., 3 units)'
    )
    
    # Cost tracking
    estimated_material_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Calculated from components'
    )
    labor_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Labor cost per unit'
    )
    overhead_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Overhead cost per unit'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'bill_of_materials'
        verbose_name = 'Bill of Materials'
        verbose_name_plural = 'Bills of Materials'
        ordering = ['-created_at']
        unique_together = [['product', 'version']]
        indexes = [
            models.Index(fields=['product', 'is_active'], name='idx_bom_prod_active'),
            models.Index(fields=['is_active', '-created_at'], name='idx_bom_active_date'),
            models.Index(fields=['version'], name='idx_bom_version'),  # ADDED
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(expected_quantity__gt=0),
                name='bom_expected_qty_positive'
            ),
            models.CheckConstraint(
                check=models.Q(estimated_material_cost__gte=0),
                name='bom_material_cost_positive'
            ),
        ]
    
    def __str__(self):
        return f"BOM: {self.product.name} v{self.version}"
    
    @property
    def total_cost_per_unit(self):
        """Calculate total cost per unit"""
        return self.estimated_material_cost + self.labor_cost + self.overhead_cost
    
    @property
    def component_count(self):
        """Get number of components"""
        return self.components.filter(is_deleted=False).count()
    
    @property
    def has_variable_yield(self):
        """Check if BOM has variable yield"""
        return self.min_yield is not None or self.max_yield is not None


class BOMComponent(TimeStampedModel, SoftDeleteModel):
    """
    Components required for a BOM
    Supports both raw materials and assembled products
    """
    
    bom = models.ForeignKey(
        BillOfMaterials,
        on_delete=models.CASCADE,
        related_name='components',
        help_text='Parent BOM'
    )
    component = models.ForeignKey(
        'layers.Product',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='used_in_bom',
        help_text='Product/Material used as component'
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Quantity needed per assembly'
    )
    
    # Variable usage for raw materials
    is_variable = models.BooleanField(
        default=False,
        help_text='True for raw materials with unpredictable usage'
    )
    estimated_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        blank=True,
        null=True,
        help_text='Estimated quantity if variable'
    )
    
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Cost per unit of this component'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Component notes'
    )
    sequence = models.IntegerField(
        default=0,
        db_index=True,  # ADDED: For ordering
        help_text='Order of assembly (for phased disassembly)'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'bom_components'
        verbose_name = 'BOM Component'
        verbose_name_plural = 'BOM Components'
        ordering = ['sequence', 'created_at']
        unique_together = [['bom', 'component']]
        indexes = [
            models.Index(fields=['bom', 'sequence'], name='idx_comp_bom_seq'),
            models.Index(fields=['component'], name='idx_comp_component'),
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name='comp_quantity_positive'
            ),
            models.CheckConstraint(
                check=models.Q(unit_cost__gte=0),
                name='comp_cost_positive'
            ),
        ]
    
    def __str__(self):
        return f"{self.component.name} x{self.quantity}"
    
    @property
    def total_cost(self):
        """Calculate total cost for this component"""
        return self.quantity * self.unit_cost


class ProductionOrder(TimeStampedModel, SoftDeleteModel):
    """
    Production/Assembly/Disassembly Order
    Tracks the manufacturing process
    """
    
    TYPE_CHOICES = [
        ('assembly', 'Assembly'),
        ('disassembly', 'Disassembly'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text='Unique production order number'
    )
    order_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,  # ADDED: For filtering by type
        help_text='Assembly or Disassembly'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,  # ADDED: For status filtering
        help_text='Current order status'
    )
    
    # Product being produced/disassembled
    product = models.ForeignKey(
        'layers.Product',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='production_orders',
        help_text='Product being produced/disassembled'
    )
    bom = models.ForeignKey(
        BillOfMaterials,
        on_delete=models.PROTECT,
        related_name='production_orders',
        blank=True,
        null=True,
        help_text='Bill of Materials used'
    )
    
    # Quantities
    planned_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Planned production quantity'
    )
    actual_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Actual quantity produced (for variable yield)'
    )
    
    # Warehouse
    warehouse = models.ForeignKey(
        'layers.Warehouse',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='production_orders',
        help_text='Warehouse for production'
    )
    
    # Dates
    scheduled_date = models.DateField(
        db_index=True,  # ADDED: For date queries
        help_text='Scheduled production date'
    )
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Actual start time'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Actual completion time'
    )
    
    # Costs
    material_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total material cost'
    )
    labor_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total labor cost'
    )
    overhead_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total overhead cost'
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'layers.User',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='production_orders_created',
        help_text='User who created this order'
    )
    completed_by = models.ForeignKey(
        'layers.User',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='production_orders_completed',
        blank=True,
        null=True,
        help_text='User who completed this order'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Production notes'
    )
    
    # Phased disassembly tracking
    parent_order = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='child_orders',
        help_text='Parent production order for phased disassembly'
    )
    phase = models.IntegerField(
        default=0,
        help_text='Assembly/disassembly phase number'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'production_orders'
        verbose_name = 'Production Order'
        verbose_name_plural = 'Production Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number'], name='idx_prod_order_num'),
            models.Index(fields=['status', 'scheduled_date'], name='idx_prod_status_date'),
            models.Index(fields=['product', 'warehouse'], name='idx_prod_prod_wh'),
            models.Index(fields=['order_type', 'status'], name='idx_prod_type_status'),
            models.Index(fields=['scheduled_date'], name='idx_prod_sched_date'),  # ADDED
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(planned_quantity__gt=0),
                name='prod_planned_qty_positive'
            ),
            models.CheckConstraint(
                check=models.Q(actual_quantity__gte=0),
                name='prod_actual_qty_positive'
            ),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.get_order_type_display()}"
    
    @property
    def total_cost(self):
        """Calculate total production cost"""
        return self.material_cost + self.labor_cost + self.overhead_cost
    
    @property
    def variance_quantity(self):
        """Calculate variance between planned and actual"""
        return self.actual_quantity - self.planned_quantity
    
    @property
    def yield_percentage(self):
        """Calculate yield percentage"""
        if self.planned_quantity > 0:
            return (self.actual_quantity / self.planned_quantity) * 100
        return Decimal('0.00')
    
    @property
    def is_assembly(self):
        """Check if this is an assembly order"""
        return self.order_type == 'assembly'
    
    @property
    def is_disassembly(self):
        """Check if this is a disassembly order"""
        return self.order_type == 'disassembly'
    
    @property
    def is_completed(self):
        """Check if order is completed"""
        return self.status == 'completed'
    
    @property
    def is_in_progress(self):
        """Check if order is in progress"""
        return self.status == 'in_progress'
    
    @property
    def cost_per_unit(self):
        """Calculate cost per unit produced"""
        if self.actual_quantity > 0:
            return self.total_cost / self.actual_quantity
        elif self.planned_quantity > 0:
            return self.total_cost / self.planned_quantity
        return Decimal('0.00')


class ProductionOrderItem(TimeStampedModel, SoftDeleteModel):
    """
    Items (components) consumed or produced in a production order
    """
    
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Production order'
    )
    product = models.ForeignKey(
        'layers.Product',  # CHANGED: Use string reference
        on_delete=models.PROTECT,
        related_name='production_items',
        help_text='Component product'
    )
    
    # Quantities
    planned_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Planned quantity'
    )
    actual_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Actual quantity consumed/produced'
    )
    
    # Cost tracking
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Cost per unit'
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total cost for this item'
    )
    
    # Stock reservation
    reserved = models.BooleanField(
        default=False,
        db_index=True,  # ADDED: For reservation queries
        help_text='Is stock reserved?'
    )
    reservation_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Reservation identifier'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text='Item notes'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'production_order_items'
        verbose_name = 'Production Order Item'
        verbose_name_plural = 'Production Order Items'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['production_order'], name='idx_prod_item_order'),
            models.Index(fields=['product'], name='idx_prod_item_product'),
            models.Index(fields=['reserved'], name='idx_prod_item_reserved'),
        ]
        constraints = [  # ADDED: Database constraints
            models.CheckConstraint(
                check=models.Q(planned_quantity__gt=0),
                name='prod_item_planned_positive'
            ),
            models.CheckConstraint(
                check=models.Q(actual_quantity__gte=0),
                name='prod_item_actual_positive'
            ),
        ]
    
    def __str__(self):
        qty = self.actual_quantity if self.actual_quantity > 0 else self.planned_quantity
        return f"{self.product.name} x{qty}"
    
    @property
    def variance_quantity(self):
        """Calculate variance"""
        return self.actual_quantity - self.planned_quantity
    
    @property
    def variance_percentage(self):
        """Calculate variance percentage"""
        if self.planned_quantity > 0:
            return (self.variance_quantity / self.planned_quantity) * 100
        return Decimal('0.00')
    
    def calculate_total_cost(self):
        """Calculate and update total cost"""
        qty = self.actual_quantity if self.actual_quantity > 0 else self.planned_quantity
        self.total_cost = qty * self.unit_cost
        return self.total_cost


class ProductionPhase(TimeStampedModel, SoftDeleteModel):
    """
    Track production phases for complex assemblies
    Enables phased disassembly
    """
    
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name='phases',
        help_text='Production order'
    )
    phase_number = models.IntegerField(
        db_index=True,  # ADDED: For ordering
        help_text='Phase number (1, 2, 3, etc.)'
    )
    name = models.CharField(
        max_length=200,
        help_text='Phase name'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Phase description'
    )
    
    # Phase tracking
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Phase start time'
    )
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Phase completion time'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
        ],
        default='pending',
        db_index=True,  # ADDED: For status filtering
        help_text='Phase status'
    )
    
    # Components used in this phase
    components_snapshot = models.JSONField(
        default=list,
        help_text='Snapshot of components used in this phase'
    )
    
    class Meta:
        app_label = 'layers'  # ADDED: Required
        db_table = 'production_phases'
        verbose_name = 'Production Phase'
        verbose_name_plural = 'Production Phases'
        ordering = ['phase_number']
        unique_together = [['production_order', 'phase_number']]
        indexes = [
            models.Index(fields=['production_order', 'phase_number'], name='idx_phase_order_num'),
            models.Index(fields=['status'], name='idx_phase_status'),  # ADDED
        ]
    
    def __str__(self):
        return f"Phase {self.phase_number}: {self.name}"
    
    @property
    def is_completed(self):
        """Check if phase is completed"""
        return self.status == 'completed'
    
    @property
    def is_in_progress(self):
        """Check if phase is in progress"""
        return self.status == 'in_progress'
    
    @property
    def duration(self):
        """Calculate phase duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None