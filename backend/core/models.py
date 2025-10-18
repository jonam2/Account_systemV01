"""
Core Models - Base models for the entire application
All domain models should inherit from these base classes
"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides timestamp fields
    Automatically tracks creation and modification times
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class SoftDeleteModel(models.Model):
    """
    Abstract base model that provides soft delete functionality
    Records are marked as deleted instead of being removed from the database
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indicates if the record has been soft deleted"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the record was soft deleted"
    )

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the record"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
#here

    def restore(self):
        """Restore a soft deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class ActiveModel(models.Model):
    """
    Abstract base model that provides active/inactive flag
    Useful for temporarily disabling records without deleting them
    """
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Indicates if the record is active"
    )

    class Meta:
        abstract = True

    def activate(self):
        """Activate the record"""
        self.is_active = True
        self.save(update_fields=['is_active'])

    def deactivate(self):
        """Deactivate the record"""
        self.is_active = False
        self.save(update_fields=['is_active'])


class AuditModel(models.Model):
    """
    Abstract base model that provides audit trail fields
    Tracks who created and last modified the record
    """
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        help_text="User who created this record"
    )
    updated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        help_text="User who last updated this record"
    )

    class Meta:
        abstract = True


class TenantModel(models.Model):
    """
    Abstract base model for multi-tenancy support
    Each record belongs to a specific company/organization
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='%(class)s_records',
        help_text="Company this record belongs to"
    )

    class Meta:
        abstract = True


# Commonly used combination models

class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    Most common base model combining timestamps and soft delete
    Use this for most domain models
    """
    class Meta:
        abstract = True


class FullAuditModel(TimeStampedModel, SoftDeleteModel, AuditModel):
    """
    Full audit model with timestamps, soft delete, and user tracking
    Use this for sensitive or important records
    """
    class Meta:
        abstract = True