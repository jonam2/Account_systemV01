"""Product service with business logic"""
import re
from typing import List, Optional, Dict
from decimal import Decimal
from layers.repositories.product_repository import ProductRepository, CategoryRepository
from layers.models.product_models import Product, Category
from core.exceptions import ValidationError, NotFoundError, DuplicateError

class CategoryService:
    """Handles all category-related business logic"""
    
    def __init__(self):
        self.category_repo = CategoryRepository()
    
    def get_all_categories(self) -> List[Category]:
        """Get all active categories"""
        return self.category_repo.get_active_categories()
    
    def get_category_by_id(self, category_id: int) -> Category:
        """Get category by ID"""
        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundError(f"Category with ID {category_id} not found")
        return category
    
    def create_category(self, data: Dict) -> Category:
        """Create new category with validations"""
        # Validation: Name is required
        if not data.get('name'):
            raise ValidationError("Category name is required")
        
        # Validation: Check if name exists
        if self.category_repo.get_by_name(data['name']):
            raise DuplicateError(f"Category '{data['name']}' already exists")
        
        # Validation: Check parent exists (if provided)
        if data.get('parent'):
            parent = self.category_repo.get_by_id(data['parent'])
            if not parent:
                raise ValidationError("Parent category not found")
        
        return self.category_repo.create(**data)
    
    def update_category(self, category_id: int, data: Dict) -> Category:
        """Update category"""
        category = self.get_category_by_id(category_id)
        
        # Validation: Check name uniqueness (if changing)
        if data.get('name') and data['name'] != category.name:
            if self.category_repo.get_by_name(data['name']):
                raise DuplicateError(f"Category '{data['name']}' already exists")
        
        return self.category_repo.update(category_id, **data)
    
    def delete_category(self, category_id: int) -> bool:
        """Delete category"""
        category = self.get_category_by_id(category_id)
        
        # Business Rule: Cannot delete category with products
        if category.products.exists():
            raise ValidationError("Cannot delete category with existing products")
        
        return self.category_repo.delete(category_id)
    
    def get_root_categories(self) -> List[Category]:
        """Get root categories"""
        return self.category_repo.get_root_categories()
    
    def get_subcategories(self, category_id: int) -> List[Category]:
        """Get subcategories"""
        return self.category_repo.get_subcategories(category_id)


class ProductService:
    """Handles all product-related business logic"""
    
    def __init__(self):
        self.product_repo = ProductRepository()
        self.category_repo = CategoryRepository()
    
    def get_all_products(self, filters: Optional[Dict] = None) -> List[Product]:
        """Get all products with optional filters"""
        if not filters:
            return self.product_repo.get_all()
        
        products = self.product_repo.get_all()
        
        # Apply filters
        if filters.get('category_id'):
            products = products.filter(category_id=filters['category_id'])
        
        if filters.get('is_active') is not None:
            products = products.filter(is_active=filters['is_active'])
        
        if filters.get('search'):
            search = filters['search']
            products = products.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(barcode__icontains=search)
            )
        
        return products
    
    def get_product_by_id(self, product_id: int) -> Product:
        """Get product by ID"""
        product = self.product_repo.get_by_id(product_id)
        if not product or product.is_deleted:
            raise NotFoundError(f"Product with ID {product_id} not found")
        return product
    
    def create_product(self, data: Dict) -> Product:
        """Create new product with validations"""
        # Validation 1: Required fields
        required_fields = ['name', 'sku', 'category', 'selling_price']
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"{field} is required")
        
        # Validation 2: SKU uniqueness
        if self.product_repo.get_by_sku(data['sku']):
            raise DuplicateError(f"Product with SKU '{data['sku']}' already exists")
        
        # Validation 3: Barcode uniqueness (if provided)
        if data.get('barcode'):
            if self.product_repo.get_by_barcode(data['barcode']):
                raise DuplicateError(f"Product with barcode '{data['barcode']}' already exists")
        
        # Validation 4: Category exists
        category = self.category_repo.get_by_id(data['category'])
        if not category:
            raise ValidationError("Category not found")
        
        # Validation 5: Prices must be positive
        if Decimal(str(data.get('selling_price', 0))) < 0:
            raise ValidationError("Selling price must be positive")
        
        if Decimal(str(data.get('cost_price', 0))) < 0:
            raise ValidationError("Cost price must be positive")
        
        # Business Rule: Selling price should be >= cost price
        selling_price = Decimal(str(data.get('selling_price', 0)))
        cost_price = Decimal(str(data.get('cost_price', 0)))
        if selling_price > 0 and cost_price > 0 and selling_price < cost_price:
            # Warning: This is allowed but we can add a flag
            pass
        
        return self.product_repo.create(**data)
    
    def update_product(self, product_id: int, data: Dict) -> Product:
        """Update product with validations"""
        product = self.get_product_by_id(product_id)
        
        # Validation: SKU uniqueness (if changing)
        if data.get('sku') and data['sku'] != product.sku:
            if self.product_repo.get_by_sku(data['sku']):
                raise DuplicateError(f"Product with SKU '{data['sku']}' already exists")
        
        # Validation: Barcode uniqueness (if changing)
        if data.get('barcode') and data['barcode'] != product.barcode:
            if self.product_repo.get_by_barcode(data['barcode']):
                raise DuplicateError(f"Product with barcode '{data['barcode']}' already exists")
        
        # Validation: Category exists (if changing)
        if data.get('category'):
            category = self.category_repo.get_by_id(data['category'])
            if not category:
                raise ValidationError("Category not found")
        
        return self.product_repo.update(product_id, **data)
    
    def delete_product(self, product_id: int) -> bool:
        """Soft delete product"""
        product = self.get_product_by_id(product_id)
        
        # Soft delete
        product.is_deleted = True
        product.save()
        return True
    
    def get_product_statistics(self) -> Dict:
        """Get product statistics"""
        return self.product_repo.get_products_stats()
    
    def search_products(self, query: str) -> List[Product]:
        """Search products"""
        return self.product_repo.search(query)
    
    def get_products_by_category(self, category_id: int) -> List[Product]:
        """Get products by category"""
        # Validate category exists
        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundError(f"Category with ID {category_id} not found")
        
        return self.product_repo.get_by_category(category_id)