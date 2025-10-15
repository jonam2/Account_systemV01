"""Django admin configuration for all models"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from layers.models.user_models import User
from layers.models.product_models import Product, Category
from layers.models.contact_models import Contact
from layers.models.warehouse_models import Warehouse, Stock, StockMovement
from layers.models.invoice_models import Invoice, InvoiceItem, InvoicePayment


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin configuration"""
    list_display = ['username', 'email', 'role', 'department', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff', 'department']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'phone', 'department', 'salary', 'join_date', 'address', 'avatar')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'phone', 'department')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin configuration"""
    list_display = ['code', 'name', 'parent', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'parent', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product admin configuration"""
    list_display = ['code', 'name', 'category', 'unit', 'sale_price', 'cost_price', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'unit', 'created_at']
    search_fields = ['code', 'name', 'barcode', 'sku', 'description']
    readonly_fields = ['created_at', 'updated_at', 'profit_margin']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'category', 'description')
        }),
        ('Details', {
            'fields': ('unit', 'barcode', 'sku')
        }),
        ('Pricing', {
            'fields': ('sale_price', 'cost_price', 'currency', 'profit_margin')
        }),
        ('Dimensions', {
            'fields': ('weight', 'length', 'width', 'height'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Contact admin configuration"""
    list_display = ['code', 'name', 'contact_type', 'email', 'phone', 'city', 'current_balance', 'is_active']
    list_filter = ['contact_type', 'is_active', 'city', 'country']
    search_fields = ['code', 'name', 'email', 'phone', 'tax_number']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'available_credit', 'is_over_credit_limit']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('contact_type', 'code', 'name')
        }),
        ('Contact Details', {
            'fields': ('email', 'phone', 'mobile', 'website')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Business Information', {
            'fields': ('tax_number', 'tax_office')
        }),
        ('Financial Settings', {
            'fields': ('currency', 'payment_terms', 'credit_limit', 'current_balance', 'available_credit', 'is_over_credit_limit')
        }),
        ('Contact Person', {
            'fields': ('contact_person', 'contact_person_phone', 'contact_person_email')
        }),
        ('Additional', {
            'fields': ('notes', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    """Warehouse admin configuration"""
    list_display = ['code', 'name', 'city', 'country', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_default', 'city', 'country']
    search_fields = ['code', 'name', 'city']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name')
        }),
        ('Location', {
            'fields': ('address', 'city', 'country', 'postal_code')
        }),
        ('Contact Information', {
            'fields': ('manager_name', 'phone', 'email')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_default')
        }),
        ('Additional', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    """Stock admin configuration"""
    list_display = ['product', 'warehouse', 'quantity', 'reserved_quantity', 'min_quantity', 'is_low_stock']
    list_filter = ['warehouse', 'created_at']
    search_fields = ['product__name', 'product__code', 'warehouse__name']
    readonly_fields = ['created_at', 'updated_at', 'available_quantity', 'is_low_stock', 'is_out_of_stock', 'stock_value']
    
    fieldsets = (
        ('Reference', {
            'fields': ('warehouse', 'product')
        }),
        ('Quantities', {
            'fields': ('quantity', 'reserved_quantity', 'available_quantity')
        }),
        ('Reorder Settings', {
            'fields': ('min_quantity', 'max_quantity')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Information', {
            'fields': ('is_low_stock', 'is_out_of_stock', 'stock_value'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Stock Movement admin configuration"""
    list_display = ['id', 'warehouse', 'product', 'movement_type', 'quantity', 'quantity_after', 'created_by', 'created_at']
    list_filter = ['movement_type', 'warehouse', 'created_at']
    search_fields = ['product__name', 'product__code', 'reference_number']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Movement Details', {
            'fields': ('warehouse', 'product', 'movement_type', 'quantity')
        }),
        ('Before/After', {
            'fields': ('quantity_before', 'quantity_after')
        }),
        ('Transfer Details', {
            'fields': ('from_warehouse', 'to_warehouse'),
            'classes': ('collapse',)
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id', 'reference_number')
        }),
        ('Additional', {
            'fields': ('notes', 'created_by', 'created_at')
        }),
    )



class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'discount_percentage', 
              'tax_percentage', 'line_total']
    readonly_fields = ['line_total']


class InvoicePaymentInline(admin.TabularInline):
    model = InvoicePayment
    extra = 0
    fields = ['payment_date', 'amount', 'payment_method', 'reference_number']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'invoice_type', 'contact', 'invoice_date', 
                    'due_date', 'status', 'total_amount', 'balance_due']
    list_filter = ['invoice_type', 'status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'reference_number', 'contact__name']
    readonly_fields = ['invoice_number', 'subtotal', 'discount_amount', 
                       'tax_amount', 'total_amount', 'paid_amount', 'balance_due']
    inlines = [InvoiceItemInline, InvoicePaymentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_number', 'invoice_type', 'reference_number', 
                      'contact', 'warehouse', 'status')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date', 'payment_date', 
                      'payment_terms')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'discount_percentage', 'discount_amount',
                      'tax_percentage', 'tax_amount', 'shipping_cost',
                      'total_amount', 'paid_amount', 'balance_due')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms_and_conditions', 'inventory_updated')
        }),
        ('Audit', {
            'fields': ('created_by', 'approved_by', 'approved_date')
        }),
    )