"""Contact repository - Data access layer"""
from django.db.models import Q, Count, Sum
from layers.repositories.base_repository import BaseRepository
from layers.models.contact_models import Contact


class ContactRepository(BaseRepository):
    """Repository for Contact data operations"""
    
    def __init__(self):
        super().__init__(Contact)
    
    def find_by_code(self, code):
        """Find contact by code"""
        return self.model.objects.filter(code=code).first()
    
    def find_by_type(self, contact_type):
        """Find contacts by type"""
        return self.model.objects.filter(contact_type=contact_type, is_active=True)
    
    def find_customers(self):
        """Find all active customers"""
        return self.model.objects.filter(
            Q(contact_type=Contact.ContactType.CUSTOMER) | 
            Q(contact_type=Contact.ContactType.BOTH),
            is_active=True
        )
    
    def find_suppliers(self):
        """Find all active suppliers"""
        return self.model.objects.filter(
            Q(contact_type=Contact.ContactType.SUPPLIER) | 
            Q(contact_type=Contact.ContactType.BOTH),
            is_active=True
        )
    
    def search(self, query):
        """Search contacts by name, code, email, or phone"""
        return self.model.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(mobile__icontains=query) |
            Q(tax_number__icontains=query)
        )
    
    def filter_contacts(self, filters):
        """
        Filter contacts with multiple criteria
        
        Args:
            filters (dict): Filter parameters
                - contact_type (str): Type of contact
                - is_active (bool): Active status
                - city (str): City filter
                - country (str): Country filter
                - search (str): Search query
        """
        queryset = self.model.objects.all()
        
        if 'contact_type' in filters:
            queryset = queryset.filter(contact_type=filters['contact_type'])
        
        if 'is_active' in filters:
            is_active = str(filters['is_active']).lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if 'city' in filters:
            queryset = queryset.filter(city__icontains=filters['city'])
        
        if 'country' in filters:
            queryset = queryset.filter(country__icontains=filters['country'])
        
        if 'search' in filters:
            search_query = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        return queryset.select_related('created_by')
    
    def get_statistics(self):
        """Get contact statistics"""
        stats = self.model.objects.aggregate(
            total_contacts=Count('id'),
            total_customers=Count('id', filter=Q(
                Q(contact_type=Contact.ContactType.CUSTOMER) | 
                Q(contact_type=Contact.ContactType.BOTH)
            )),
            total_suppliers=Count('id', filter=Q(
                Q(contact_type=Contact.ContactType.SUPPLIER) | 
                Q(contact_type=Contact.ContactType.BOTH)
            )),
            active_contacts=Count('id', filter=Q(is_active=True)),
            total_receivables=Sum('current_balance', filter=Q(current_balance__gt=0)),
            total_payables=Sum('current_balance', filter=Q(current_balance__lt=0)),
        )
        
        # Handle None values
        stats['total_receivables'] = stats['total_receivables'] or 0
        stats['total_payables'] = abs(stats['total_payables'] or 0)
        
        return stats
    
    def get_over_credit_limit(self):
        """Get contacts that exceeded credit limit"""
        return self.model.objects.filter(
            is_active=True,
            credit_limit__gt=0
        ).exclude(
            current_balance__lte=models.F('credit_limit')
        )
    
    def get_top_customers_by_balance(self, limit=10):
        """Get top customers by receivable balance"""
        return self.model.objects.filter(
            Q(contact_type=Contact.ContactType.CUSTOMER) | 
            Q(contact_type=Contact.ContactType.BOTH),
            is_active=True,
            current_balance__gt=0
        ).order_by('-current_balance')[:limit]
    
    def get_top_suppliers_by_balance(self, limit=10):
        """Get top suppliers by payable balance"""
        return self.model.objects.filter(
            Q(contact_type=Contact.ContactType.SUPPLIER) | 
            Q(contact_type=Contact.ContactType.BOTH),
            is_active=True,
            current_balance__lt=0
        ).order_by('current_balance')[:limit]
    
    def generate_next_code(self, contact_type):
        """
        Generate next contact code
        Format: CUS-0001, SUP-0001
        """
        prefix = 'CUS' if contact_type == Contact.ContactType.CUSTOMER else 'SUP'
        
        last_contact = self.model.objects.filter(
            code__startswith=prefix
        ).order_by('-code').first()
        
        if last_contact:
            try:
                last_number = int(last_contact.code.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1
        
        return f"{prefix}-{next_number:04d}"