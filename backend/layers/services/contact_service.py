"""
Contact Service - Complete Business Logic Layer
Handles customer and supplier management
"""
from django.db import transaction
import logging

from layers.repositories.contact_repository import ContactRepository
from core.exceptions import ValidationError, NotFoundError, DuplicateError

logger = logging.getLogger(__name__)


class ContactService:
    """Service for contact operations"""
    
    def __init__(self):
        self.contact_repo = ContactRepository()
    
    @transaction.atomic
    def create_contact(self, data):
        """Create a new contact"""
        try:
            # Check for duplicate code
            if self.contact_repo.find_by_code(data.get('code')):
                raise DuplicateError(f"Contact with code {data['code']} already exists")
            
            # Generate code if not provided
            if not data.get('code'):
                data['code'] = self.contact_repo.generate_next_code(
                    data.get('contact_type', 'customer')
                )
            
            contact = self.contact_repo.create(data)
            logger.info(f"Contact created: {contact.code} - {contact.name}")
            return contact
            
        except DuplicateError as e:
            logger.warning(f"Contact creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating contact: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create contact: {str(e)}")
    
    @transaction.atomic
    def update_contact(self, contact_id, data):
        """Update contact"""
        try:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact {contact_id} not found")
            
            # Check for duplicate code if changing
            if 'code' in data and data['code'] != contact.code:
                if self.contact_repo.find_by_code(data['code']):
                    raise DuplicateError(f"Contact with code {data['code']} already exists")
            
            updated = self.contact_repo.update(contact_id, data)
            logger.info(f"Contact updated: {updated.code}")
            return updated
            
        except (NotFoundError, DuplicateError) as e:
            logger.warning(f"Contact update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating contact: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update contact: {str(e)}")
    
    @transaction.atomic
    def delete_contact(self, contact_id):
        """Delete contact"""
        try:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact {contact_id} not found")
            
            # Check if contact has transactions
            from layers.models import Invoice, Order
            if Invoice.objects.filter(contact_id=contact_id).exists():
                raise ValidationError("Cannot delete contact with invoices")
            if Order.objects.filter(contact_id=contact_id).exists():
                raise ValidationError("Cannot delete contact with orders")
            
            self.contact_repo.delete(contact_id)
            logger.info(f"Contact deleted: {contact.code}")
            return True
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Contact deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting contact: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete contact: {str(e)}")
    
    def get_all_contacts(self, filters=None):
        """Get all contacts with filters"""
        try:
            filters = filters or {}
            return self.contact_repo.filter_contacts(filters)
        except Exception as e:
            logger.error(f"Error listing contacts: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to list contacts: {str(e)}")
    
    def get_contact_by_id(self, contact_id):
        """Get contact by ID"""
        contact = self.contact_repo.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact {contact_id} not found")
        return contact
    
    def get_customers(self):
        """Get all customers"""
        return self.contact_repo.find_customers()
    
    def get_suppliers(self):
        """Get all suppliers"""
        return self.contact_repo.find_suppliers()
    
    def get_contact_statistics(self):
        """Get contact statistics"""
        return self.contact_repo.get_statistics()
    
    @transaction.atomic
    def update_contact_balance(self, contact_id, amount):
        """Update contact balance"""
        try:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact {contact_id} not found")
            
            contact.update_balance(amount)
            logger.info(f"Contact {contact.code} balance updated by {amount}")
            return contact
            
        except NotFoundError as e:
            logger.warning(f"Balance update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating balance: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update balance: {str(e)}")
    
    def check_credit_limit(self, contact_id, amount):
        """Check if amount would exceed credit limit"""
        try:
            contact = self.contact_repo.get_by_id(contact_id)
            if not contact:
                raise NotFoundError(f"Contact {contact_id} not found")
            
            if not contact.is_customer:
                return {'allowed': True, 'message': 'Not a customer'}
            
            if contact.credit_limit <= 0:
                return {'allowed': True, 'message': 'No credit limit set'}
            
            new_balance = contact.current_balance + amount
            would_exceed = new_balance > contact.credit_limit
            
            return {
                'allowed': not would_exceed,
                'current_balance': contact.current_balance,
                'credit_limit': contact.credit_limit,
                'available_credit': contact.available_credit,
                'new_balance': new_balance,
                'message': 'Credit limit exceeded' if would_exceed else 'OK'
            }
            
        except NotFoundError as e:
            logger.warning(f"Credit check failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error checking credit: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to check credit: {str(e)}")