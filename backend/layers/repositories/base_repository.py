"""Base repository class for all repositories"""
from django.db import models


class BaseRepository:
    """Base repository with common CRUD operations"""
    
    def __init__(self, model):
        """
        Initialize repository with model
        
        Args:
            model: Django model class
        """
        self.model = model
    
    def get_all(self):
        """Get all records"""
        return self.model.objects.all()
    
    def get_by_id(self, id):
        """
        Get record by ID
        
        Args:
            id: Record ID
        
        Returns:
            Model instance or None
        """
        try:
            return self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            return None
    
    def create(self, data):
        """
        Create new record
        
        Args:
            data (dict): Record data
        
        Returns:
            Model instance
        """
        return self.model.objects.create(**data)
    
    def update(self, id, data):
        """
        Update record
        
        Args:
            id: Record ID
            data (dict): Updated data
        
        Returns:
            Updated model instance or None
        """
        try:
            instance = self.model.objects.get(id=id)
            for key, value in data.items():
                setattr(instance, key, value)
            instance.save()
            return instance
        except self.model.DoesNotExist:
            return None
    
    def delete(self, id):
        """
        Delete record
        
        Args:
            id: Record ID
        
        Returns:
            Boolean indicating success
        """
        try:
            instance = self.model.objects.get(id=id)
            instance.delete()
            return True
        except self.model.DoesNotExist:
            return False
    
    def filter(self, **kwargs):
        """
        Filter records
        
        Args:
            **kwargs: Filter parameters
        
        Returns:
            QuerySet
        """
        return self.model.objects.filter(**kwargs)
    
    def exists(self, **kwargs):
        """
        Check if record exists
        
        Args:
            **kwargs: Filter parameters
        
        Returns:
            Boolean
        """
        return self.model.objects.filter(**kwargs).exists()
    
    def count(self, **kwargs):
        """
        Count records
        
        Args:
            **kwargs: Filter parameters
        
        Returns:
            Integer count
        """
        if kwargs:
            return self.model.objects.filter(**kwargs).count()
        return self.model.objects.count()