"""
Error Handler - Custom exceptions and error handling utilities.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base exception for the application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class NotFoundError(AppException):
    """Resource not found error."""
    
    def __init__(self, resource: str, id: str):
        super().__init__(
            message=f"{resource} with ID '{id}' not found",
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": id}
        )


class ValidationError(AppException):
    """Validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={"field": field} if field else {}
        )


class LLMError(AppException):
    """Error from LLM service."""
    
    def __init__(self, message: str, original_error: Optional[str] = None):
        super().__init__(
            message=f"LLM service error: {message}",
            error_code="LLM_ERROR",
            status_code=503,
            details={"original_error": original_error} if original_error else {}
        )


class DatabaseError(AppException):
    """Database operation error."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=f"Database error: {message}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation} if operation else {}
        )


class FileProcessingError(AppException):
    """File processing error (PDF parsing, etc.)."""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(
            message=f"File processing error: {message}",
            error_code="FILE_PROCESSING_ERROR",
            status_code=400,
            details={"filename": filename} if filename else {}
        )


class EmailError(AppException):
    """Email ingestion error."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Email error: {message}",
            error_code="EMAIL_ERROR",
            status_code=500
        )


def handle_exception(exc: Exception) -> Dict[str, Any]:
    """
    Convert an exception to a standardized error response.
    
    Args:
        exc: The exception to handle
        
    Returns:
        Dict suitable for JSON response
    """
    if isinstance(exc, AppException):
        return exc.to_dict()
    
    if isinstance(exc, HTTPException):
        return {
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "details": {"status_code": exc.status_code}
        }
    
    # Generic error
    return {
        "error": "INTERNAL_ERROR",
        "message": str(exc),
        "details": {}
    }


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    FastAPI exception handler for AppException.
    
    Usage:
        app.add_exception_handler(AppException, app_exception_handler)
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    FastAPI exception handler for generic exceptions.
    
    Usage:
        app.add_exception_handler(Exception, generic_exception_handler)
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {"type": type(exc).__name__}
        }
    )
