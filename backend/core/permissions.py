"""Custom permission classes"""
from rest_framework import permissions

class IsManager(permissions.BasePermission):
    """Only managers can access"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'manager'

class IsAccountant(permissions.BasePermission):
    """Managers and accountants can access"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'accountant']

class IsSales(permissions.BasePermission):
    """Managers and sales can access"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'sales']

class IsWarehouseManager(permissions.BasePermission):
    """Managers and warehouse managers can access"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['manager', 'warehouse_manager']