"""Exceptions for the PSEG Long Island integration."""

from homeassistant.exceptions import HomeAssistantError


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class PSEGLIError(HomeAssistantError):
    """Base exception for PSEG Long Island integration."""


class PSEGConnectionError(PSEGLIError):
    """Error to indicate PSEG could not be reached."""
