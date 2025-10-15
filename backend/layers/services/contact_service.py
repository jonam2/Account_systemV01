"""Contact service - Business logic layer"""
from layers.repositories.contact_repository import ContactRepository
from core.exceptions import ValidationError, NotFoundError, DuplicateError


class ContactService:
    """Service for contact business logic"""
    
    def __init__(self):
        self.repository = ContactRepository()
    
    def get_all_contacts(self, filters=None):
        """
        Get all contacts with optional filters
        
        Args:
            filters (dict): Optional filters
        
        Returns:
            QuerySet: Filtered contacts
        """
        if filters:
            return self.repository.filter_contacts(filters)
        return self.repository.get_all()
    
    def get_contact_by_id(self, contact_id):
        """
        Get contact by ID
        
        Args:
            contact_id (int): Contact ID
        
        Returns:
            Contact: Contact instance
        
        Raises:
            NotFoundError: If contact not found
        """
        contact = self.repository.get_by_id(contact_id)
        if not contact:
            raise NotFoundError(f"Contact with ID {contact_id} not found")
        return contact
    
    def get_contact_by_code(self, code):
        """
        Get contact by code
        
        Args:
            code (str): Contact code
        
        Returns:
            Contact: Contact instance
        
        Raises:
            NotFoundError: If contact not found
        """
        contact = self.repository.find_by_code(code)
        if not contact:
            raise NotFoundError(f"Contact with code {code} not found")
        return contact
    
    def create_contact(self, data):
        """
        Create new contact
        
        Args:
            data (dict): Contact data
        
        Returns:
            Contact: Created contact
        
        Raises:
            ValidationError: If validation fails
            DuplicateError: If contact code already exists
        """
        # Validate required fields
        if not data.get('name'):
            raise ValidationError("Contact name is required")
        
        # Generate code if not provided
        if not data.get('code'):
            contact_type = data.get('contact_type', 'customer')
            data['code'] = self.repository.generate_next_code(contact_type)
        
        # Check for duplicate code
        existing_contact = self.repository.find_by_code(data['code'])
        if existing_contact:
            raise DuplicateError(f"Contact with code {data['code']} already exists")
        
        # Validate email format if provided
        if data.get('email') and '@' not in data['email']:
            raise ValidationError("Invalid email format")
        
        # Validate credit limit
        if 'credit_limit' in data and data['credit_limit'] < 0:
            raise ValidationError("Credit limit cannot be negative")
        
        # Create contact
        contact = self.repository.create(data)
        return contact
    
    def update_contact(self, contact_id, data):
        """
        Update contact
        
        Args:
            contact_id (int): Contact ID
            data (dict): Updated data
        
        Returns:
            Contact: Updated contact
        
        Raises:
            NotFoundError: If contact not found
            ValidationError: If validation fails
            DuplicateError: If contact code already exists
        """
        contact = self.get_contact_by_id(contact_id)
        
        # Check for duplicate code if code is being updated
        if 'code' in data and data['code'] != contact.code:
            existing_contact = self.repository.find_by_code(data['code'])
            if existing_contact:
                raise DuplicateError(f"Contact with code {data['code']} already exists")
        
        # Validate email format if provided
        if data.get('email') and '@' not in data['email']:
            raise ValidationError("Invalid email format")
        
        # Validate credit limit
        if 'credit_limit' in data and data['credit_limit'] < 0:
            raise ValidationError("Credit limit cannot be negative")
        
        # Update contact
        updated_contact = self.repository.update(contact_id, data)
        return updated_contact
    
    def delete_contact(self, contact_id):
        """
        Delete contact (soft delete by setting is_active=False)
        
        Args:
            contact_id (int): Contact ID
        
        Raises:
            NotFoundError: If contact not found
        """
        contact = self.get_contact_by_id(contact_id)
        
        # Soft delete - just deactivate
        self.repository.update(contact_id, {'is_active': False})
    
    def get_customers(self):
        """Get all active customers"""
        return self.repository.find_customers()
    
    def get_suppliers(self):
        """Get all active suppliers"""
        return self.repository.find_suppliers()
    
    def search_contacts(self, query):
        """
        Search contacts
        
        Args:
            query (str): Search query
        
        Returns:
            QuerySet: Matching contacts
        """
        if not query:
            return self.repository.get_all()
        return self.repository.search(query)
    
    def get_contact_statistics(self):
        """
        Get contact statistics
        
        Returns:
            dict: Statistics data
        """
        return self.repository.get_statistics()
    
    def update_contact_balance(self, contact_id, amount):
        """
        Update contact balance
        
        Args:
            contact_id (int): Contact ID
            amount (Decimal): Amount to add/subtract
        
        Returns:
            Contact: Updated contact
        
        Raises:
            NotFoundError: If contact not found
        """
        contact = self.get_contact_by_id(contact_id)
        contact.update_balance(amount)
        return contact
    
    def check_credit_limit(self, contact_id, additional_amount):
        """
        Check if additional amount would exceed credit limit
        
        Args:
            contact_id (int): Contact ID
            additional_amount (Decimal): Amount to check
        
        Returns:
            dict: Credit check result
        
        Raises:
            NotFoundError: If contact not found
        """
        contact = self.get_contact_by_id(contact_id)
        
        if contact.credit_limit <= 0:
            return {
                'has_limit': False,
                'can_proceed': True,
                'message': 'No credit limit set'
            }
        
        new_balance = contact.current_balance + additional_amount
        
        if new_balance > contact.credit_limit:
            return {
                'has_limit': True,
                'can_proceed': False,
                'current_balance': float(contact.current_balance),
                'credit_limit': float(contact.credit_limit),
                'available_credit': float(contact.available_credit),
                'requested_amount': float(additional_amount),
                'message': f'Credit limit exceeded. Available credit: {contact.available_credit}'
            }
        
        return {
            'has_limit': True,
            'can_proceed': True,
            'current_balance': float(contact.current_balance),
            'credit_limit': float(contact.credit_limit),
            'available_credit': float(contact.available_credit),
            'requested_amount': float(additional_amount),
            'message': 'Credit check passed'
        }
    
    def get_top_customers(self, limit=10):
        """Get top customers by receivable balance"""
        return self.repository.get_top_customers_by_balance(limit)
    
    def get_top_suppliers(self, limit=10):
        """Get top suppliers by payable balance"""
        return self.repository.get_top_suppliers_by_balance(limit)