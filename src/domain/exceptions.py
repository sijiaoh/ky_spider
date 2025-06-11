class DomainException(Exception):
    """Base exception for domain layer"""
    pass


class ScrapingException(DomainException):
    """Exception raised during scraping operations"""
    pass


class DataIntegrityException(DomainException):
    """Exception raised when data integrity is compromised"""
    pass


class DataProcessingException(DomainException):
    """Exception raised during data processing"""
    pass


class ExportException(DomainException):
    """Exception raised during data export"""
    pass


class ValidationException(DomainException):
    """Exception raised when validation fails"""
    pass