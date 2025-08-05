"""
Custom exceptions for the Temporal Explorator module.
"""

from typing import Optional, Any, Dict


class TemporalExploratorError(Exception):
    """Base exception for Temporal Explorator module."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ValidationError(TemporalExploratorError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field, "value": value})


class StateMappingError(TemporalExploratorError):
    """Raised when state mapping fails."""
    
    def __init__(self, message: str, action: Optional[str] = None, response: Optional[str] = None):
        super().__init__(message, "STATE_MAPPING_ERROR", {"action": action, "response": response})


class PromptGenerationError(TemporalExploratorError):
    """Raised when prompt generation fails."""
    
    def __init__(self, message: str, action: Optional[str] = None, session_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PROMPT_GENERATION_ERROR", {"action": action, "session_data": session_data})


class SessionError(TemporalExploratorError):
    """Raised when session operations fail."""
    
    def __init__(self, message: str, bt_id: Optional[str] = None, session_id: Optional[str] = None):
        super().__init__(message, "SESSION_ERROR", {"bt_id": bt_id, "session_id": session_id})


class ModelCommunicationError(TemporalExploratorError):
    """Raised when communication with the model fails."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, retry_count: Optional[int] = None):
        super().__init__(message, "MODEL_COMMUNICATION_ERROR", {"model_name": model_name, "retry_count": retry_count})


class ConfigurationError(TemporalExploratorError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, expected_type: Optional[str] = None):
        super().__init__(message, "CONFIGURATION_ERROR", {"config_key": config_key, "expected_type": expected_type})


class FileOperationError(TemporalExploratorError):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, operation: Optional[str] = None):
        super().__init__(message, "FILE_OPERATION_ERROR", {"file_path": file_path, "operation": operation}) 