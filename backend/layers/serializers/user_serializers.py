"""User serializers for data validation and transformation"""
from rest_framework import serializers
from layers.models.user_models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - Read operations"""
    
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'role_display', 'phone', 'department',
            'salary', 'join_date', 'address', 'avatar',
            'is_active', 'date_joined', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']

class UserCreateSerializer(serializers.Serializer):
    """Serializer for creating users"""
    
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=['manager', 'accountant', 'sales', 'warehouse_manager'],
        required=True
    )
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    department = serializers.CharField(max_length=50, required=False, allow_blank=True)
    salary = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    join_date = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)

class UserUpdateSerializer(serializers.Serializer):
    """Serializer for updating users"""
    
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    role = serializers.ChoiceField(
        choices=['manager', 'accountant', 'sales', 'warehouse_manager'],
        required=False
    )
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    department = serializers.CharField(max_length=50, required=False, allow_blank=True)
    salary = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    join_date = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing users"""
    
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name',
            'role', 'role_display', 'department', 'is_active'
        ]

class UserSummarySerializer(serializers.ModelSerializer):
    """Lightweight user serializer for nested representations"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

