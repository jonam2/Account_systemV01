"""
Invoice Serializers - Data Transfer Objects
Handles serialization/deserialization of invoice data
"""
from rest_framework import serializers
from layers.models.invoice_models import Invoice, InvoiceItem, InvoicePayment
from layers.serializers.contact_serializers import ContactSummarySerializer
from layers.serializers.warehouse_serializers import WarehouseSummarySerializer
from layers.serializers.product_serializers import ProductSummarySerializer
from layers.serializers.user_serializers import UserSummarySerializer


class InvoiceItemSerializer(serializers.ModelSerializer):
    """Serializer for invoice items"""
    product = ProductSummarySerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = [
            'id',
            'product',
            'product_id',
            'description',
            'quantity',
            'unit_price',
            'discount_percentage',
            'discount_amount',
            'tax_percentage',
            'tax_amount',
            'line_total',
            'notes',
            'sort_order',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'line_total', 'created_at', 'updated_at']


class InvoiceItemCreateSerializer(serializers.Serializer):
    """Serializer for creating invoice items"""
    product_id = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        required=False
    )
    discount_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        required=False
    )
    tax_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class InvoicePaymentSerializer(serializers.ModelSerializer):
    """Serializer for invoice payments"""
    recorded_by = UserSummarySerializer(read_only=True)
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )
    
    class Meta:
        model = InvoicePayment
        fields = [
            'id',
            'payment_date',
            'amount',
            'payment_method',
            'payment_method_display',
            'reference_number',
            'recorded_by',
            'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'recorded_by', 'created_at']


class InvoicePaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating payments"""
    payment_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_method = serializers.ChoiceField(
        choices=InvoicePayment.PAYMENT_METHOD_CHOICES
    )
    reference_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer for invoice list view (summary)"""
    contact = ContactSummarySerializer(read_only=True)
    warehouse = WarehouseSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    invoice_type_display = serializers.CharField(
        source='get_invoice_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'invoice_type',
            'invoice_type_display',
            'reference_number',
            'contact',
            'warehouse',
            'invoice_date',
            'due_date',
            'payment_date',
            'status',
            'status_display',
            'total_amount',
            'paid_amount',
            'balance_due',
            'is_overdue',
            'days_until_due',
            'created_by',
            'created_at'
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed invoice view"""
    contact = ContactSummarySerializer(read_only=True)
    warehouse = WarehouseSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    approved_by = UserSummarySerializer(read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = InvoicePaymentSerializer(many=True, read_only=True)
    
    invoice_type_display = serializers.CharField(
        source='get_invoice_type_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    payment_terms_display = serializers.CharField(
        source='get_payment_terms_display',
        read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'invoice_type',
            'invoice_type_display',
            'reference_number',
            'contact',
            'warehouse',
            'created_by',
            'approved_by',
            'invoice_date',
            'due_date',
            'payment_date',
            'approved_date',
            'payment_terms',
            'payment_terms_display',
            'subtotal',
            'discount_percentage',
            'discount_amount',
            'tax_percentage',
            'tax_amount',
            'shipping_cost',
            'total_amount',
            'paid_amount',
            'balance_due',
            'status',
            'status_display',
            'notes',
            'terms_and_conditions',
            'is_recurring',
            'inventory_updated',
            'is_overdue',
            'days_until_due',
            'items',
            'payments',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'invoice_number',
            'subtotal',
            'discount_amount',
            'tax_amount',
            'total_amount',
            'paid_amount',
            'balance_due',
            'approved_by',
            'approved_date',
            'payment_date',
            'inventory_updated',
            'created_at',
            'updated_at'
        ]


class InvoiceCreateSerializer(serializers.Serializer):
    """Serializer for creating invoices"""
    invoice_type = serializers.ChoiceField(choices=Invoice.INVOICE_TYPE_CHOICES)
    reference_number = serializers.CharField(required=False, allow_blank=True)
    contact_id = serializers.IntegerField()
    warehouse_id = serializers.IntegerField()
    invoice_date = serializers.DateField()
    due_date = serializers.DateField(required=False)
    payment_terms = serializers.ChoiceField(
        choices=Invoice.PAYMENT_TERMS_CHOICES,
        default='NET_30'
    )
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        required=False
    )
    tax_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        required=False
    )
    shipping_cost = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    terms_and_conditions = serializers.CharField(required=False, allow_blank=True)
    items = InvoiceItemCreateSerializer(many=True)
    
    def validate_items(self, value):
        """Validate that at least one item is provided"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one item is required")
        return value


class InvoiceUpdateSerializer(serializers.Serializer):
    """Serializer for updating invoices"""
    reference_number = serializers.CharField(required=False, allow_blank=True)
    contact_id = serializers.IntegerField(required=False)
    warehouse_id = serializers.IntegerField(required=False)
    invoice_date = serializers.DateField(required=False)
    due_date = serializers.DateField(required=False)
    payment_terms = serializers.ChoiceField(
        choices=Invoice.PAYMENT_TERMS_CHOICES,
        required=False
    )
    discount_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False
    )
    tax_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False
    )
    shipping_cost = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    terms_and_conditions = serializers.CharField(required=False, allow_blank=True)
    items = InvoiceItemCreateSerializer(many=True, required=False)


class InvoiceStatsSerializer(serializers.Serializer):
    """Serializer for invoice statistics"""
    total_invoices = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_invoices = serializers.IntegerField()
    paid_invoices = serializers.IntegerField()
    overdue_invoices = serializers.IntegerField()
    overdue_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class ContactInvoiceSummarySerializer(serializers.Serializer):
    """Serializer for contact invoice summary"""
    total_invoices = serializers.IntegerField()
    total_invoiced = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_outstanding = serializers.DecimalField(max_digits=15, decimal_places=2)
    invoices = InvoiceListSerializer(many=True, read_only=True)