"""
Product Service - Complete Business Logic Layer
Handles product and category management
"""
from django.db import transaction
import logging

from layers.repositories.product_repository import ProductRepository, CategoryRepository
from core.exceptions import ValidationError, NotFoundError, DuplicateError

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product operations"""
    
    def __init__(self):
        self.product_repo = ProductRepository()
    
    @transaction.atomic
    def create_product(self, data):
        """Create a new product"""
        try:
            # Check for duplicate code
            if self.product_repo.find_by_code(data.get('code')):
                raise DuplicateError(f"Product with code {data['code']} already exists")
            
            # Check for duplicate barcode if provided
            if data.get('barcode') and self.product_repo.find_by_barcode(data['barcode']):
                raise DuplicateError(f"Product with barcode {data['barcode']} already exists")
            
            # Generate code if not provided
            if not data.get('code'):
                data['code'] = self.product_repo.generate_next_code()
            
            product = self.product_repo.create(data)
            logger.info(f"Product created: {product.code} - {product.name}")
            return product
            
        except DuplicateError as e:
            logger.warning(f"Product creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating product: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create product: {str(e)}")
    
    @transaction.atomic
    def update_product(self, product_id, data):
        """Update product"""
        try:
            product = self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"Product {product_id} not found")
            
            # Check for duplicate code if changing
            if 'code' in data and data['code'] != product.code:
                if self.product_repo.find_by_code(data['code']):
                    raise DuplicateError(f"Product with code {data['code']} already exists")
            
            # Check for duplicate barcode if changing
            if 'barcode' in data and data['barcode'] != product.barcode:
                if data['barcode'] and self.product_repo.find_by_barcode(data['barcode']):
                    raise DuplicateError(f"Product with barcode {data['barcode']} already exists")
            
            updated = self.product_repo.update(product_id, data)
            logger.info(f"Product updated: {updated.code}")
            return updated
            
        except (NotFoundError, DuplicateError) as e:
            logger.warning(f"Product update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating product: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update product: {str(e)}")
    
    @transaction.atomic
    def delete_product(self, product_id):
        """Delete product"""
        try:
            product = self.product_repo.get_by_id(product_id)
            if not product:
                raise NotFoundError(f"Product {product_id} not found")
            
            # Check if product has stock
            from layers.models import Stock
            if Stock.objects.filter(product_id=product_id, quantity__gt=0).exists():
                raise ValidationError("Cannot delete product with stock")
            
            # Check if product is used in transactions
            from layers.models import InvoiceItem, OrderItem
            if InvoiceItem.objects.filter(product_id=product_id).exists():
                raise ValidationError("Cannot delete product used in invoices")
            if OrderItem.objects.filter(product_id=product_id).exists():
                raise ValidationError("Cannot delete product used in orders")
            
            self.product_repo.delete(product_id)
            logger.info(f"Product deleted: {product.code}")
            return True
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Product deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting product: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete product: {str(e)}")
    
    def get_all_products(self, filters=None):
        """Get all products with filters"""
        try:
            filters = filters or {}
            return self.product_repo.filter_products(filters)
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to list products: {str(e)}")
    
    def get_product_by_id(self, product_id):
        """Get product by ID"""
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")
        return product
    
    def get_product_statistics(self):
        """Get product statistics"""
        return self.product_repo.get_statistics()


class CategoryService:
    """Service for category operations"""
    
    def __init__(self):
        self.category_repo = CategoryRepository()
    
    @transaction.atomic
    def create_category(self, data):
        """Create a new category"""
        try:
            # Check for duplicate code
            if self.category_repo.find_by_code(data.get('code')):
                raise DuplicateError(f"Category with code {data['code']} already exists")
            
            # Generate code if not provided
            if not data.get('code'):
                data['code'] = self.category_repo.generate_next_code()
            
            category = self.category_repo.create(data)
            logger.info(f"Category created: {category.code} - {category.name}")
            return category
            
        except DuplicateError as e:
            logger.warning(f"Category creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating category: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to create category: {str(e)}")
    
    @transaction.atomic
    def update_category(self, category_id, data):
        """Update category"""
        try:
            category = self.category_repo.get_by_id(category_id)
            if not category:
                raise NotFoundError(f"Category {category_id} not found")
            
            # Check for duplicate code if changing
            if 'code' in data and data['code'] != category.code:
                if self.category_repo.find_by_code(data['code']):
                    raise DuplicateError(f"Category with code {data['code']} already exists")
            
            updated = self.category_repo.update(category_id, data)
            logger.info(f"Category updated: {updated.code}")
            return updated
            
        except (NotFoundError, DuplicateError) as e:
            logger.warning(f"Category update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating category: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to update category: {str(e)}")
    
    @transaction.atomic
    def delete_category(self, category_id):
        """Delete category"""
        try:
            category = self.category_repo.get_by_id(category_id)
            if not category:
                raise NotFoundError(f"Category {category_id} not found")
            
            # Check if category has products
            if category.products.exists():
                raise ValidationError("Cannot delete category with products")
            
            # Check if category has children
            if category.children.exists():
                raise ValidationError("Cannot delete category with subcategories")
            
            self.category_repo.delete(category_id)
            logger.info(f"Category deleted: {category.code}")
            return True
            
        except (NotFoundError, ValidationError) as e:
            logger.warning(f"Category deletion failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting category: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to delete category: {str(e)}")
    
    def get_all_categories(self):
        """Get all categories"""
        return self.category_repo.get_all()
    
    def get_category_by_id(self, category_id):
        """Get category by ID"""
        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundError(f"Category {category_id} not found")
        return category