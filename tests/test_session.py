"""Session regressions using the real requests cookie jar and mocked HTTP."""
import ast
import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

import requests

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "psegli"
PACKAGE = "_psegli_session_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
ha_exceptions = types.ModuleType("homeassistant.exceptions")
ha_exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
with patch.dict(sys.modules, {PACKAGE: package, "homeassistant.exceptions": ha_exceptions}):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.psegli", ROOT / "psegli.py")
    client_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client_module)


def dashboard(body='<input name="__RequestVerificationToken" value="valid">', *, url=None):
    response = requests.Response()
    response.status_code = 200
    response.url = url or "https://mysmartenergy.psegliny.com/Dashboard"
    response.headers["Content-Type"] = "text/html"
    response._content = body.encode()
    return response


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.client = client_module.PSEGLIClient("MM_SID=old; __RequestVerificationToken=before")
        self.addCleanup(self.client.session.close)

    def test_rotated_cookie_replaces_original_on_chart_request(self):
        self.client.session.cookies.set("__RequestVerificationToken", "rotated",
                                        domain="mysmartenergy.psegliny.com", path="/")
        request = self.client.session.prepare_request(requests.Request(
            "POST", "https://mysmartenergy.psegliny.com/Dashboard/Chart"))
        self.assertIn("__RequestVerificationToken=rotated", request.headers["Cookie"])
        self.assertNotIn("before", request.headers["Cookie"])
        self.assertEqual(request.headers["Cookie"].count("__RequestVerificationToken="), 1)

    def test_update_cookie_clears_old_jar_values(self):
        self.client.update_cookie("MM_SID=new; extra=value=with=equals; malformed")
        self.assertEqual(self.client.session.cookies.get_dict(),
                         {"MM_SID": "new", "extra": "value=with=equals"})
        self.assertNotIn("Cookie", self.client.session.headers)

    def test_valid_dashboard_is_accepted(self):
        with patch.object(self.client.session, "get", return_value=dashboard()):
            self.assertTrue(self.client._test_connection_sync())

    def test_missing_or_empty_dashboard_token_is_rejected(self):
        for body in ["<html></html>", '<input name="__RequestVerificationToken" value="">']:
            with self.subTest(body=body), patch.object(self.client.session, "get", return_value=dashboard(body)):
                with self.assertRaises(client_module.InvalidAuth):
                    self.client._test_connection_sync()

    def test_ajax_logout_and_login_redirect_are_rejected(self):
        ajax = dashboard('{"AjaxResults":[{"Action":"Redirect","Value":"/"}]}')
        ajax.headers["Content-Type"] = "application/json"
        for response in [ajax, dashboard(url="https://mysmartenergy.psegliny.com/")]:
            with self.subTest(url=response.url), patch.object(self.client.session, "get", return_value=response):
                with self.assertRaises(client_module.InvalidAuth):
                    self.client._test_connection_sync()

    def test_transport_failures_preserve_cookie_and_are_not_invalid_auth(self):
        response = dashboard()
        response.status_code = 503
        for error in [requests.ConnectionError("DNS"), requests.Timeout("timeout"),
                      requests.exceptions.SSLError("TLS"), requests.HTTPError(response=response)]:
            with self.subTest(error=type(error)), patch.object(self.client.session, "get", side_effect=error):
                with self.assertRaises(client_module.PSEGConnectionError):
                    self.client._test_connection_sync()
                self.assertEqual(self.client.session.cookies.get("MM_SID"), "old")

    def test_pending_mfa_prevents_automatic_login(self):
        # Exercise the actual nested maintenance function without booting HA.
        tree = ast.parse((ROOT / "__init__.py").read_text())
        setup = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_setup_entry")
        scheduled = next(n for n in setup.body if isinstance(n, ast.AsyncFunctionDef)
                         and n.name == "async_scheduled_cookie_refresh")
        # Its closure variable is supplied as a global for this isolated test.
        scheduled.body = [ast.copy_location(ast.Global(names=n.names), n)
                          if isinstance(n, ast.Nonlocal) else n for n in scheduled.body]
        login = AsyncMock()
        namespace = {"mfa_pending": True, "_LOGGER": logging.getLogger(__name__),
                     "get_fresh_cookies": login}
        exec(compile(ast.Module(body=[scheduled], type_ignores=[]), str(ROOT / "__init__.py"), "exec"), namespace)
        asyncio.run(namespace[scheduled.name](update_statistics=True))
        login.assert_not_called()


if __name__ == "__main__":
    unittest.main()
