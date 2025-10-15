"""Custom exceptions"""

class BaseException(Exception):
    """Base exception class"""
    def __init__(self, message="An error occurred"):
        self.message = message
        super().__init__(self.message)

class ValidationError(BaseException):
    """Raised when validation fails"""
    pass

class NotFoundError(BaseException):
    """Raised when resource is not found"""
    pass

class DuplicateError(BaseException):
    """Raised when duplicate resource is detected"""
    pass

class PermissionDeniedError(BaseException):
    """Raised when user doesn't have permission"""
    pass

class AuthenticationError(BaseException):
    """Raised when authentication fails"""
    pass