"""Product repository - Data access layer"""
from django.db.models import Q, Count, Sum
from layers.repositories.base_repository import BaseRepository
from layers.models.product_models import Product, Category


class CategoryRepository(BaseRepository):
    """Repository for Category data operations"""
    
    def __init__(self):
        super().__init__(Category)
    
    def find_by_code(self, code):
        """Find category by code"""
        return self.model.objects.filter(code=code).first()
    
    def get_root_categories(self):
        """Get categories without parent"""
        return self.model.objects.filter(parent__isnull=True, is_active=True)
    
    def get_children(self, parent_id):
        """Get child categories"""
        return self.model.objects.filter(parent_id=parent_id, is_active=True)
    
    def filter_categories(self, filters):
        """Filter categories"""
        queryset = self.model.objects.all()
        
        if 'is_active' in filters:
            is_active = str(filters['is_active']).lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if 'search' in filters:
            search = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        
        return queryset
    
    def generate_next_code(self):
        """Generate next category code"""
        last_category = self.model.objects.filter(
            code__startswith='CAT-'
        ).order_by('-code').first()
        
        if last_category:
            try:
                last_number = int(last_category.code.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1
        
        return f"CAT-{next_number:04d}"


class ProductRepository(BaseRepository):
    """Repository for Product data operations"""
    
    def __init__(self):
        super().__init__(Product)
    
    def find_by_code(self, code):
        """Find product by code"""
        return self.model.objects.filter(code=code).first()
    
    def find_by_barcode(self, barcode):
        """Find product by barcode"""
        return self.model.objects.filter(barcode=barcode).first()
    
    def find_by_category(self, category_id):
        """Find products by category"""
        return self.model.objects.filter(category_id=category_id, is_active=True)
    
    def get_active_products(self):
        """Get all active products"""
        return self.model.objects.filter(is_active=True)
    
    def search(self, query):
        """Search products"""
        return self.model.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(barcode__icontains=query) |
            Q(sku__icontains=query)
        )
    
    def filter_products(self, filters):
        """Filter products"""
        queryset = self.model.objects.select_related('category')
        
        if 'category_id' in filters:
            queryset = queryset.filter(category_id=filters['category_id'])
        
        if 'is_active' in filters:
            is_active = str(filters['is_active']).lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        if 'unit' in filters:
            queryset = queryset.filter(unit=filters['unit'])
        
        if 'search' in filters:
            search = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(barcode__icontains=search)
            )
        
        return queryset
    
    def get_statistics(self):
        """Get product statistics"""
        return {
            'total_products': self.model.objects.count(),
            'active_products': self.model.objects.filter(is_active=True).count(),
            'by_category': dict(
                self.model.objects.values('category__name').annotate(
                    count=Count('id')
                ).values_list('category__name', 'count')
            ),
        }
    
    def generate_next_code(self):
        """Generate next product code"""
        last_product = self.model.objects.filter(
            code__startswith='PRD-'
        ).order_by('-code').first()
        
        if last_product:
            try:
                last_number = int(last_product.code.split('-')[1])
                next_number = last_number + 1
            except (IndexError, ValueError):
                next_number = 1
        else:
            next_number = 1
        
        return f"PRD-{next_number:04d}"