"""Contact serializers - Data transfer objects"""
from rest_framework import serializers
from layers.models.contact_models import Contact


class ContactSerializer(serializers.ModelSerializer):
    """Main contact serializer for responses"""
    
    created_by_name = serializers.CharField(
        source='created_by.full_name',
        read_only=True,
        allow_null=True
    )
    contact_type_display = serializers.CharField(
        source='get_contact_type_display',
        read_only=True
    )
    payment_terms_display = serializers.CharField(
        source='get_payment_terms_display',
        read_only=True
    )
    available_credit = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    is_over_credit_limit = serializers.BooleanField(read_only=True)
    is_customer = serializers.BooleanField(read_only=True)
    is_supplier = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Contact
        fields = [
            'id',
            'contact_type',
            'contact_type_display',
            'code',
            'name',
            'email',
            'phone',
            'mobile',
            'website',
            'address',
            'city',
            'state',
            'country',
            'postal_code',
            'tax_number',
            'tax_office',
            'currency',
            'payment_terms',
            'payment_terms_display',
            'credit_limit',
            'current_balance',
            'available_credit',
            'is_over_credit_limit',
            'contact_person',
            'contact_person_phone',
            'contact_person_email',
            'notes',
            'is_active',
            'is_customer',
            'is_supplier',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContactCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating contacts"""
    
    class Meta:
        model = Contact
        fields = [
            'contact_type',
            'code',
            'name',
            'email',
            'phone',
            'mobile',
            'website',
            'address',
            'city',
            'state',
            'country',
            'postal_code',
            'tax_number',
            'tax_office',
            'currency',
            'payment_terms',
            'credit_limit',
            'contact_person',
            'contact_person_phone',
            'contact_person_email',
            'notes',
            'is_active',
            'created_by',
        ]
    
    def validate_name(self, value):
        """Validate contact name"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")
        return value.strip()
    
    def validate_email(self, value):
        """Validate email format"""
        if value and '@' not in value:
            raise serializers.ValidationError("Invalid email format")
        return value
    
    def validate_credit_limit(self, value):
        """Validate credit limit"""
        if value < 0:
            raise serializers.ValidationError("Credit limit cannot be negative")
        return value


class ContactUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating contacts"""
    
    class Meta:
        model = Contact
        fields = [
            'contact_type',
            'code',
            'name',
            'email',
            'phone',
            'mobile',
            'website',
            'address',
            'city',
            'state',
            'country',
            'postal_code',
            'tax_number',
            'tax_office',
            'currency',
            'payment_terms',
            'credit_limit',
            'current_balance',
            'contact_person',
            'contact_person_phone',
            'contact_person_email',
            'notes',
            'is_active',
        ]
    
    def validate_name(self, value):
        """Validate contact name"""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")
        return value.strip() if value else value
    
    def validate_email(self, value):
        """Validate email format"""
        if value and '@' not in value:
            raise serializers.ValidationError("Invalid email format")
        return value
    
    def validate_credit_limit(self, value):
        """Validate credit limit"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Credit limit cannot be negative")
        return value


class ContactListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for contact lists"""
    
    contact_type_display = serializers.CharField(
        source='get_contact_type_display',
        read_only=True
    )
    available_credit = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Contact
        fields = [
            'id',
            'code',
            'name',
            'contact_type',
            'contact_type_display',
            'email',
            'phone',
            'city',
            'country',
            'current_balance',
            'credit_limit',
            'available_credit',
            'is_active',
        ]


class ContactBalanceUpdateSerializer(serializers.Serializer):
    """Serializer for updating contact balance"""
    
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=True
    )
    
    def validate_amount(self, value):
        """Validate amount"""
        if value == 0:
            raise serializers.ValidationError("Amount cannot be zero")
        return value


class CreditCheckSerializer(serializers.Serializer):
    """Serializer for credit limit check"""
    
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=True
    )
    
    def validate_amount(self, value):
        """Validate amount"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value
    
class ContactSummarySerializer(serializers.ModelSerializer):
    """Lightweight contact serializer for nested representations"""
    contact_type_display = serializers.CharField(
        source='get_contact_type_display',
        read_only=True
    )
    
    class Meta:
        model = Contact
        fields = [
            'id',
            'name',
            'contact_type',
            'contact_type_display',
            'email',
            'phone',
            'company'
        ]
