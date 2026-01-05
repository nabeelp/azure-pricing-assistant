"""Shared exception definitions for the application."""


class PricingAssistantError(Exception):
    """Base exception for Pricing Assistant errors."""

    pass


class ConfigurationError(PricingAssistantError):
    """Raised when configuration is missing or invalid."""

    pass


class SessionError(PricingAssistantError):
    """Raised when session operations fail."""

    pass


class WorkflowError(PricingAssistantError):
    """Raised when workflow operations fail."""

    pass


class InterfaceError(PricingAssistantError):
    """Raised when interface operations fail."""

    pass
