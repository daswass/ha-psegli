"""Config flow for PSEG Long Island integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import load_yaml

from .const import DOMAIN, CONF_COOKIE, CONF_USERNAME, CONF_PASSWORD, CONF_MFA_METHOD
from .psegli import PSEGLIClient
from .exceptions import InvalidAuth
from .auto_login import get_fresh_cookies, complete_mfa_login, MFA_REQUIRED

_LOGGER = logging.getLogger(__name__)


class PSEGLIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PSEG Long Island."""

    VERSION = 1
    has_options = True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return PSEGLIOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Get credentials from user input
                username = user_input[CONF_USERNAME]
                password = user_input[CONF_PASSWORD]
                cookie = user_input.get(CONF_COOKIE, "")
                
                # If no cookie provided, try to get one from the addon
                if not cookie:
                    _LOGGER.debug("No cookie provided, attempting to get fresh cookies from addon...")
                    try:
                        cookies = await get_fresh_cookies(
                            username, password, mfa_method=user_input.get(CONF_MFA_METHOD, "email")
                        )
                        
                        if cookies == MFA_REQUIRED:
                            # PSEG requires MFA - show form for verification code
                            # Store credentials for creating entry after MFA succeeds
                            self.context["username"] = username
                            self.context["password"] = password
                            self.context["mfa_method"] = user_input.get(CONF_MFA_METHOD, "sms")
                            return self.async_show_form(
                                step_id="mfa",
                                data_schema=vol.Schema({
                                    vol.Required("mfa_code"): str,
                                }),
                                description_placeholders={
                                    "message": "PSEG now requires multi-factor authentication. "
                                    "Check your email or phone for the verification code and enter it below.",
                                },
                            )
                        elif cookies:
                            cookie = cookies
                            _LOGGER.debug("Successfully obtained fresh cookies from addon")
                        else:
                            _LOGGER.warning("Addon not available or failed to get cookies")
                            # Don't fail here - user can provide cookie manually later
                    except Exception as e:
                        _LOGGER.warning("Failed to get cookies from addon: %s", e)
                        # Don't fail here - user can provide cookie manually later
                
                # If we have a cookie, validate it
                if cookie:
                    client = PSEGLIClient(cookie)
                    await client.test_connection()
                    _LOGGER.debug("Cookie validation successful")
                else:
                    _LOGGER.debug("No cookie available, integration will require manual cookie setup")

                # Create the config entry
                return self.async_create_entry(
                    title="PSEG Long Island",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_COOKIE: cookie,
                        CONF_MFA_METHOD: user_input.get(CONF_MFA_METHOD, "sms"),
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

    async def async_step_mfa(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle MFA verification code step."""
        errors = {}
        if user_input is not None:
            mfa_code = user_input.get("mfa_code", "").strip()
            if not mfa_code:
                errors["base"] = "mfa_code_required"
            else:
                try:
                    cookies = await complete_mfa_login(mfa_code)
                    if cookies:
                        username = self.context.get("username")
                        password = self.context.get("password")
                        mfa_method = self.context.get("mfa_method", "sms")
                        if username and password:
                            client = PSEGLIClient(cookies)
                            await client.test_connection()
                            return self.async_create_entry(
                                title="PSEG Long Island",
                                data={
                                    CONF_USERNAME: username,
                                    CONF_PASSWORD: password,
                                    CONF_COOKIE: cookies,
                                    CONF_MFA_METHOD: mfa_method,
                                },
                            )
                    errors["base"] = "mfa_failed"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.exception("MFA error: %s", e)
                    errors["base"] = "mfa_failed"

        return self.async_show_form(
            step_id="mfa",
            data_schema=vol.Schema({
                vol.Required("mfa_code"): str,
            }),
            description_placeholders={
                "message": "PSEG now requires multi-factor authentication. "
                "Check your email for the verification code and enter it below.",
            },
            errors=errors,
        )

    def _get_schema(self):
        """Return the schema for the config flow."""
        return vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_COOKIE): str,
            vol.Optional(CONF_MFA_METHOD, default="sms"): vol.In(["email", "sms"]),
        })


class PSEGLIOptionsFlow(config_entries.OptionsFlow):
    """PSEG Long Island options flow."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Manage the options for PSEG Long Island."""
        errors = {}

        if user_input is not None:
            try:
                # Get credentials from config entry
                username = self.config_entry.data.get(CONF_USERNAME)
                password = self.config_entry.data.get(CONF_PASSWORD)
                new_cookie = user_input.get(CONF_COOKIE, "")
                
                # If user provided a new cookie, validate it
                if new_cookie:
                    client = PSEGLIClient(new_cookie)
                    await client.test_connection()
                    _LOGGER.debug("New cookie validation successful")
                    
                    # Update the config entry with the new cookie
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, CONF_COOKIE: new_cookie},
                    )
                    
                    # Clear any persistent notification about expired cookies
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "dismiss",
                        {"notification_id": "psegli_auth_failed"},
                    )
                    
                    return self.async_create_entry(title="", data={})
                
                # If no new cookie provided, try to get one from the addon
                elif username and password:
                    _LOGGER.debug("No new cookie provided, attempting to get fresh cookies from addon...")
                    try:
                        mfa_method = user_input.get(CONF_MFA_METHOD, self.config_entry.data.get(CONF_MFA_METHOD, "sms"))
                        # Save mfa_method if changed
                        if mfa_method != self.config_entry.data.get(CONF_MFA_METHOD):
                            self.hass.config_entries.async_update_entry(
                                self.config_entry,
                                data={**self.config_entry.data, CONF_MFA_METHOD: mfa_method},
                            )
                        cookies = await get_fresh_cookies(username, password, mfa_method=mfa_method)
                        
                        if cookies == MFA_REQUIRED:
                            return self.async_show_form(
                                step_id="mfa",
                                data_schema=vol.Schema({
                                    vol.Required("mfa_code"): str,
                                }),
                                description_placeholders={
                                    "message": "PSEG requires MFA. Check your email or phone for the verification code.",
                                },
                            )
                        elif cookies:
                            # Cookies are already in string format from addon
                            cookie_string = cookies
                            
                            # Validate the cookie
                            client = PSEGLIClient(cookie_string)
                            await client.test_connection()
                            
                            # Update the config entry
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
                            
                            _LOGGER.debug("Successfully obtained and validated fresh cookies from addon")
                            return self.async_create_entry(title="", data={})
                        else:
                            errors["base"] = "addon_unavailable"
                    except Exception as e:
                        _LOGGER.error("Failed to get cookies from addon: %s", e)
                        errors["base"] = "addon_failed"
                else:
                    errors["base"] = "credentials_not_found"

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

    async def async_step_mfa(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle MFA verification code in options flow."""
        errors = {}
        if user_input is not None:
            mfa_code = user_input.get("mfa_code", "").strip()
            if not mfa_code:
                errors["base"] = "mfa_code_required"
            else:
                try:
                    cookies = await complete_mfa_login(mfa_code)
                    if cookies:
                        client = PSEGLIClient(cookies)
                        await client.test_connection()
                        self.hass.config_entries.async_update_entry(
                            self.config_entry,
                            data={**self.config_entry.data, CONF_COOKIE: cookies},
                        )
                        await self.hass.services.async_call(
                            "persistent_notification",
                            "dismiss",
                            {"notification_id": "psegli_auth_failed"},
                        )
                        return self.async_create_entry(title="", data={})
                    errors["base"] = "mfa_failed"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("MFA failed during options flow")
                    errors["base"] = "mfa_failed"

        return self.async_show_form(
            step_id="mfa",
            data_schema=vol.Schema({
                vol.Required("mfa_code"): str,
            }),
            description_placeholders={
                "message": "PSEG requires MFA. Check your email for the verification code.",
            },
            errors=errors,
        )

    def _get_options_schema(self):
        """Return the schema for the options flow."""
        return vol.Schema({
            vol.Optional(CONF_COOKIE, description="Leave empty to attempt automatic refresh via addon"): str,
            vol.Optional(
                CONF_MFA_METHOD,
                default=self.config_entry.data.get(CONF_MFA_METHOD, "sms"),
            ): vol.In(["email", "sms"]),
        })

