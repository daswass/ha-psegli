"""Config flow for PSEG Long Island integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml

from .const import DOMAIN, CONF_COOKIE, CONF_USERNAME, CONF_PASSWORD
from .psegli import PSEGLIClient
from .exceptions import InvalidAuth

_LOGGER = logging.getLogger(__name__)


class PSEGLIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PSEG Long Island."""

    VERSION = 1
    has_options = True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return PSEGLIOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Get username and password from user input
                username = user_input[CONF_USERNAME]
                password = user_input[CONF_PASSWORD]
                
                # Try to get fresh cookies using automated login
                from .auto_login import get_fresh_cookies
                cookies = await get_fresh_cookies(username, password)
                
                if not cookies:
                    errors["base"] = "login_failed"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._get_schema(),
                        errors=errors,
                    )
                
                # Convert cookies to cookie string
                cookie_string = "; ".join([f"{name}={value}" for name, value in cookies.items()])
                
                # Validate the cookie by making a test request
                client = PSEGLIClient(cookie_string)
                await client.test_connection()

                # Create the config entry
                return self.async_create_entry(
                    title="PSEG Long Island",
                    data={
                        CONF_COOKIE: cookie_string,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            errors=errors,
        )

    def _get_schema(self):
        """Return the schema for the config flow."""
        return vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })


class PSEGLIOptionsFlow(config_entries.OptionsFlow):
    """PSEG Long Island options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Manage the options for PSEG Long Island."""
        errors = {}

        if user_input is not None:
            try:
                # Get username and password from config entry
                username = self.config_entry.data.get(CONF_USERNAME)
                password = self.config_entry.data.get(CONF_PASSWORD)
                
                if not username or not password:
                    errors["base"] = "credentials_not_found"
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._get_options_schema(),
                        errors=errors,
                    )
                
                # Try to get fresh cookies using automated login
                from .auto_login import get_fresh_cookies
                cookies = await get_fresh_cookies(username, password)
                
                if not cookies:
                    errors["base"] = "login_failed"
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._get_options_schema(),
                        errors=errors,
                    )
                
                # Convert cookies to cookie string
                cookie_string = "; ".join([f"{name}={value}" for name, value in cookies.items()])
                
                # Validate the cookie by making a test request
                client = PSEGLIClient(cookie_string)
                await client.test_connection()

                # Update the config entry data
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_COOKIE: cookie_string},
                )
                
                # Clear any persistent notification about expired cookies
                await self.hass.services.async_call(
                    "persistent_notification",
                    "dismiss",
                    {"notification_id": "psegli_auth_failed"},
                )

                return self.async_create_entry(title="", data={})

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reconfigure")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
            errors=errors,
            description_placeholders={
                "current_cookie": self.config_entry.data.get(CONF_COOKIE, "")[:50] + "..." if self.config_entry.data.get(CONF_COOKIE) else "None"
            },
        )

    def _get_options_schema(self):
        """Return the schema for the options flow."""
        return vol.Schema({})


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth.""" 