"""Custom exceptions"""

class ValidationError(BaseException):
    """Raised when validation fails"""
    pass

class NotFoundError(BaseException):
    """Raised when resource is not found"""
    pass

class DuplicateError(BaseException):
    """Raised when duplicate resource is detected"""
    pass
    """Raised when authentication fails"""


class AuthenticationError(BaseException):
    pass


class PermissionDeniedError(BaseException):
    """Raised when user doesn't have permission"""
    pass

class InsufficientStockError(Exception):
    """Raised when there's insufficient stock"""
    pass

class BusinessLogicError(Exception):
    """Raised when business logic validation fails"""
    pass

class BaseException(Exception):
    """Base exception class"""
    def __init__(self, message="An error occurred"):
        self.message = message
        super().__init__(self.message)




