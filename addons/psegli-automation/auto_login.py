#!/usr/bin/env python3
"""Automated login for PSEG Long Island using Playwright."""

import logging
import time
import random
import re
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

# Import stealth with graceful fallback
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    _LOGGER.warning("playwright-stealth not available, will use manual stealth methods")

class PSEGAutoLogin:
    """Automated login for PSEG Long Island using Playwright."""
    
    def __init__(self, email: str, password: str):
        """Initialize PSEG auto login."""
        self.email = email
        self.password = password
        self.login_url = "https://mysmartenergy.psegliny.com/Home/Login"
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.login_cookies = None  # Store cookies from login request
    
    def setup_browser(self) -> bool:
        """Set up Playwright browser with stealth techniques."""
        try:
            _LOGGER.info("Setting up Playwright browser...")
            
            self.playwright = sync_playwright().start()
            
            # Launch browser with stealth-friendly options
            self.browser = self.playwright.chromium.launch(
                headless=True,  # Must be headless in container environment
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-ipc-flooding-protection',
                    '--disable-renderer-backgrounding',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-client-side-phishing-detection',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-domain-reliability',
                    '--disable-features=TranslateUI',
                    '--disable-hang-monitor',
                    '--disable-prompt-on-repost',
                    '--disable-sync',
                    '--metrics-recording-only',
                    '--no-default-browser-check',
                    '--safebrowsing-disable-auto-update',
                ]
            )
            
            # Create a new context with stealth
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                # Additional stealth context options
                has_touch=False,
                is_mobile=False,
                device_scale_factor=1,
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )
            
            # Create page and apply stealth
            self.page = self.context.new_page()
            
            # Apply comprehensive stealth techniques
            _LOGGER.info("Applying comprehensive stealth techniques...")
            
            # Apply playwright-stealth
            if STEALTH_AVAILABLE:
                try:
                    stealth_instance = Stealth()
                    # Use the correct method for playwright-stealth 2.0.0+
                    if hasattr(stealth_instance, 'apply_stealth_sync'):
                        stealth_instance.apply_stealth_sync(self.page)
                        _LOGGER.info("Applied stealth using apply_stealth_sync method")
                    elif hasattr(stealth_instance, 'apply_stealth'):
                        stealth_instance.apply_stealth(self.page)
                        _LOGGER.info("Applied stealth using apply_stealth method")
                    elif hasattr(stealth_instance, 'stealth'):
                        stealth_instance.stealth(self.page)
                        _LOGGER.info("Applied stealth using stealth method")
                    else:
                        # Fallback: apply stealth manually
                        _LOGGER.warning("Stealth library API not recognized, applying manual stealth")
                        self.page.add_init_script("""
                            // Manual stealth overrides
                            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                            window.chrome = { runtime: {} };
                        """)
                except Exception as e:
                    _LOGGER.warning(f"Stealth library failed, applying manual stealth: {e}")
                    self.page.add_init_script("""
                        // Manual stealth overrides
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                        window.chrome = { runtime: {} };
                    """)
            else:
                _LOGGER.info("Using manual stealth methods (playwright-stealth not available)")
                self.page.add_init_script("""
                    // Manual stealth overrides
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                    window.chrome = { runtime: {} };
                """)
            
            # Additional stealth: Override navigator properties that detect automation
            _LOGGER.info("Applying additional stealth overrides...")
            self.page.add_init_script("""
                // Override properties that detect automation
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Override plugins to look more human
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override chrome runtime
                window.chrome = {
                    runtime: {},
                };
                
                // Override permissions
                const originalGetProperty = Object.getOwnPropertyDescriptor;
                Object.getOwnPropertyDescriptor = function(obj, prop) {
                    if (prop === 'webdriver') {
                        return undefined;
                    }
                    return originalGetProperty(obj, prop);
                };
            """)
            
            # Add human-like behavior: random scrolling and mouse movements
            _LOGGER.info("Adding human-like behavior...")
            try:
                # Random scroll down and up to simulate human reading
                scroll_amount = random.uniform(100, 300)
                self.page.mouse.wheel(0, scroll_amount)
                time.sleep(random.uniform(0.5, 1.5))
                self.page.mouse.wheel(0, -scroll_amount)
                time.sleep(random.uniform(0.3, 0.8))
                
                # Random mouse movement to simulate human behavior
                self.page.mouse.move(
                    random.uniform(100, 800),
                    random.uniform(100, 600)
                )
                time.sleep(random.uniform(0.2, 0.6))
            except Exception as e:
                _LOGGER.warning(f"Human-like behavior simulation failed: {e}")
            
            _LOGGER.info("✅ Playwright browser initialized successfully")
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to set up browser: %s", e)
            return False
    
    def setup_request_interception(self):
        """Set up request interception to capture cookies from login request."""
        try:
            _LOGGER.info("Setting up request interception to capture login cookies...")
            
            def handle_request(request):
                url = request.url
                method = request.method
                
                # Check for reCAPTCHA requests (but don't flag normal flow as captcha)
                if "recaptcha" in url.lower() and "google.com" in url.lower():
                    _LOGGER.info(f"🤖 reCAPTCHA request detected: {method} {url}")
                    
                    # Only flag actual image captcha challenges, not normal reCAPTCHA flow
                    if "api2/payload" in url and "imageselect" in url:
                        _LOGGER.error(f"🚨 IMAGE CAPTCHA REQUEST DETECTED: {url}")
                        _LOGGER.error(f"🚨 This indicates an image captcha is being loaded!")
                        
                        # Store this as a captcha request
                        self.captcha_request = {
                            'url': url,
                            'method': method,
                            'timestamp': time.time()
                        }
                
                # Check for login requests
                elif "/Home/Login" in url and method == "POST":
                    _LOGGER.info(f"Intercepted login request: {url}")
                    _LOGGER.info(f"Login request headers: {dict(request.headers)}")
                    # Store the request for later analysis
                    self.login_request = request
                
                # Check for Chart requests (successful login indicator)
                elif "/Dashboard/Chart" in url and method == "GET":
                    _LOGGER.info(f"Intercepted Chart request: {url}")
                    _LOGGER.info(f"Chart request method: {method}")
                    
                    # Check for cookies in the request headers
                    if "cookie" in request.headers:
                        cookies = request.headers.get("cookie", "")
                        _LOGGER.info(f"✅ Found cookies in Chart request: {cookies[:100]}...")
                        
                        # Parse the cookies
                        parsed_cookies = []
                        cookie_pairs = cookies.split(";")
                        for cookie_pair in cookie_pairs:
                            if "=" in cookie_pair:
                                name_value = cookie_pair.strip().split("=", 1)
                                if len(name_value) == 2:
                                    name, value = name_value
                                    if name.strip() in ['MM_SID', '__RequestVerificationToken']:
                                        parsed_cookies.append(f"{name.strip()}={value.strip()}")
                                        _LOGGER.info(f"Captured cookie from Chart request: {name.strip()}={value.strip()[:20]}...")
                        
                        if len(parsed_cookies) >= 2:
                            # Ensure MM_SID is first, then __RequestVerificationToken
                            ordered_cookies = []
                            for cookie in parsed_cookies:
                                if cookie.startswith('MM_SID='):
                                    ordered_cookies.insert(0, cookie)  # Put MM_SID first
                                elif cookie.startswith('__RequestVerificationToken='):
                                    ordered_cookies.append(cookie)  # Put RequestVerificationToken second
                            
                            self.login_cookies = "; ".join(ordered_cookies)
                            _LOGGER.info(f"✅ SUCCESS: Captured cookies from Chart request: {self.login_cookies[:50]}...")
                        else:
                            _LOGGER.warning(f"Only captured {len(parsed_cookies)} cookies from Chart request")
                    else:
                        _LOGGER.warning("No cookies found in Chart request headers")
                        _LOGGER.info(f"All Chart request headers: {dict(request.headers)}")
            
            def handle_response(response):
                # Intercept both the login response and the redirect response
                if "/Home/Login" in response.url and response.request.method == "POST":
                    _LOGGER.info(f"Intercepted login response: {response.url}")
                    _LOGGER.info(f"Response status: {response.status}")
                    _LOGGER.info(f"Response content type: {response.headers.get('content-type', 'unknown')}")
                    _LOGGER.info(f"Response headers: {dict(response.headers)}")
                    
                    # The login response is usually a redirect, so check for redirect headers
                    if response.status in [301, 302, 303, 307, 308]:
                        _LOGGER.info("✅ Login response is a redirect - cookies will be set on the redirect target")
                        _LOGGER.info(f"Redirect location: {response.headers.get('location', 'Not specified')}")
                    else:
                        _LOGGER.info("Login response is not a redirect")
                        
                    # Check for cookies in the response
                    if "set-cookie" in response.headers:
                        cookies = response.headers.get("set-cookie", "").split(",")
                        _LOGGER.info(f"Found {len(cookies)} cookies in login response")
                        for cookie in cookies:
                            _LOGGER.info(f"Login response cookie: {cookie.strip()}")
                    else:
                        _LOGGER.info("No set-cookie headers in login response")
                
                elif "/Dashboard" in response.url and response.request.method == "GET":
                    _LOGGER.info(f"Intercepted Dashboard redirect response: {response.url}")
                    _LOGGER.info(f"Response status: {response.status}")
                    
                    # Extract cookies from the Dashboard redirect response headers
                    if "set-cookie" in response.headers:
                        cookies = response.headers.get("set-cookie", "").split(",")
                        _LOGGER.info(f"Found {len(cookies)} cookies in Dashboard response headers")
                        
                        # Parse the cookies
                        parsed_cookies = []
                        for cookie in cookies:
                            if "=" in cookie:
                                name_value = cookie.split(";")[0].strip()
                                if "=" in name_value:
                                    name, value = name_value.split("=", 1)
                                    if name.strip() in ['MM_SID', '__RequestVerificationToken']:
                                        parsed_cookies.append(f"{name.strip()}={value.strip()}")
                                        _LOGGER.info(f"Captured cookie: {name.strip()}={value.strip()[:20]}...")
                        
                        if len(parsed_cookies) >= 2:
                            # Ensure MM_SID is first, then __RequestVerificationToken
                            ordered_cookies = []
                            for cookie in parsed_cookies:
                                if cookie.startswith('MM_SID='):
                                    ordered_cookies.insert(0, cookie)  # Put MM_SID first
                                elif cookie.startswith('__RequestVerificationToken='):
                                    ordered_cookies.append(cookie)  # Put RequestVerificationToken second
                            
                            self.login_cookies = "; ".join(ordered_cookies)
                            _LOGGER.info(f"✅ Captured login cookies from Dashboard redirect: {self.login_cookies[:50]}...")
                        else:
                            _LOGGER.warning(f"Only captured {len(parsed_cookies)} cookies from Dashboard response")
                    else:
                        _LOGGER.warning("No set-cookie headers found in Dashboard response")
                        # Check if cookies might be in a different header
                        for header_name, header_value in response.headers.items():
                            if "cookie" in header_name.lower():
                                _LOGGER.info(f"Found cookie-related header: {header_name} = {header_value}")
                        
                        # Also check if cookies might be in the response body or other locations
                        _LOGGER.info("Checking if cookies are stored in browser context...")
                        try:
                            # Get cookies from browser context immediately after this response
                            context_cookies = self.context.cookies()
                            _LOGGER.info(f"Browser context has {len(context_cookies)} cookies")
                            for cookie in context_cookies:
                                if cookie['name'] in ['MM_SID', '__RequestVerificationToken']:
                                    _LOGGER.info(f"Found cookie in browser context: {cookie['name']}={cookie['value'][:20]}...")
                        except Exception as e:
                            _LOGGER.warning(f"Could not check browser context cookies: {e}")
            
            # Set up the handlers
            self.page.on("request", handle_request)
            self.page.on("response", handle_response)
            
            # Also listen for console errors that might affect reCAPTCHA
            def handle_console_error(msg):
                if msg.type == 'error':
                    _LOGGER.warning(f"Console error: {msg.text}")
                    if 'recaptcha' in msg.text.lower():
                        _LOGGER.error(f"reCAPTCHA-related error: {msg.text}")
            
            self.page.on("console", handle_console_error)
            
            _LOGGER.info("✅ Request interception set up successfully")
            
        except Exception as e:
            _LOGGER.error(f"Failed to set up request interception: {e}")
    
    def get_request_verification_token(self) -> Optional[str]:
        """Get the request verification token from the login page."""
        try:
            _LOGGER.info("Getting request verification token from login page...")
            
            # Step 1: Visit the main page to establish session
            _LOGGER.info("Step 1: Visiting main page to establish session...")
            self.page.goto("https://mysmartenergy.psegliny.com/")
            self.page.wait_for_load_state("networkidle")
            time.sleep(3.5)  # Small delay to let page settle naturally
            
            main_title = self.page.title()
            main_url = self.page.url
            _LOGGER.info("Main page title: %s", main_title)
            _LOGGER.info("Main page URL: %s", main_url)
            
            # Step 2: Wait for the page to load and reCAPTCHA to initialize
            _LOGGER.info("Step 2: Waiting for page to load and reCAPTCHA to initialize...")
            
            # Wait for the page to be fully loaded and stable
            try:
                _LOGGER.info("Waiting for page to reach network idle state...")
                self.page.wait_for_load_state('networkidle', timeout=30000)
                _LOGGER.info("✅ Page reached network idle state")
            except Exception as e:
                _LOGGER.warning(f"Network idle timeout, continuing anyway: {e}")
            
            # Additional wait for reCAPTCHA to initialize with human-like timing
            _LOGGER.info("Waiting for reCAPTCHA to initialize...")
            wait_time = random.uniform(6, 10)  # Random wait between 6-10 seconds
            _LOGGER.info(f"Waiting {wait_time:.1f} seconds (human-like timing)...")
            time.sleep(wait_time)
            
            current_title = self.page.title()
            current_url = self.page.url
            content_length = len(self.page.content())
            _LOGGER.info("Current page title: %s", current_title)
            _LOGGER.info("Current page URL: %s", current_url)
            _LOGGER.info("Page content length: %d characters", content_length)
            _LOGGER.info("Page content preview (first 500 chars): %s", self.page.content()[:500])
            
            # Debug: Check for forms and inputs
            forms = self.page.locator('form')
            inputs = self.page.locator('input')
            _LOGGER.info("Number of forms found: %d", forms.count())
            _LOGGER.info("Number of inputs found: %d", inputs.count())
            
            # Look for reCAPTCHA elements
            recaptcha_elements = self.page.locator('.g-recaptcha, [data-sitekey], iframe[src*="recaptcha"]')
            _LOGGER.info("reCAPTCHA elements found: %d", recaptcha_elements.count())
            for i in range(recaptcha_elements.count()):
                try:
                    recaptcha = recaptcha_elements.nth(i)
                    _LOGGER.info("reCAPTCHA %d: %s", i, recaptcha.get_attribute('class') or 'no-class')
                    
                    # Check for additional reCAPTCHA attributes
                    sitekey = recaptcha.get_attribute('data-sitekey')
                    if sitekey:
                        _LOGGER.info("  reCAPTCHA sitekey: %s", sitekey)
                    
                    # Check if reCAPTCHA is properly initialized
                    try:
                        is_ready = self.page.evaluate("""
                            () => {
                                if (typeof grecaptcha !== 'undefined') {
                                    return grecaptcha.getResponse() !== '';
                                }
                                return false;
                            }
                        """)
                        _LOGGER.info("  reCAPTCHA ready state: %s", is_ready)
                    except Exception as e:
                        _LOGGER.warning("  Could not check reCAPTCHA ready state: %s", e)
                        
                except Exception as e:
                    _LOGGER.warning("Error examining reCAPTCHA element %d: %s", i, e)
            
            # Check for JavaScript errors that might affect reCAPTCHA
            _LOGGER.info("Checking for JavaScript errors...")
            try:
                js_errors = self.page.evaluate("""
                    () => {
                        if (window.jsErrors && window.jsErrors.length > 0) {
                            return window.jsErrors;
                        }
                        return [];
                    }
                """)
                if js_errors:
                    _LOGGER.warning("JavaScript errors found: %s", js_errors)
                else:
                    _LOGGER.info("No JavaScript errors detected")
            except Exception as e:
                _LOGGER.info("Could not check for JavaScript errors: %s", e)
            
            # Method 1: Look for visible input first
            token = None
            try:
                token_input = self.page.locator('input[name="__RequestVerificationToken"]')
                if token_input.count() > 0:
                    token = token_input.first.get_attribute('value')
                    _LOGGER.info("✅ Found token in input field")
            except Exception as e:
                _LOGGER.warning("Method 1 failed: %s", e)
            
            # Method 2: Look for hidden input
            if not token:
                try:
                    token_input = self.page.locator('input[type="hidden"][name="__RequestVerificationToken"]')
                    if token_input.count() > 0:
                        token = token_input.first.get_attribute('value')
                        _LOGGER.info("✅ Found token in hidden input field")
                except Exception as e:
                    _LOGGER.warning("Method 2 failed: %s", e)
            
            # Method 3: Extract from page HTML
            if not token:
                try:
                    page_content = self.page.content()
                    # Look for the token in the HTML
                    token_match = re.search(r'name="__RequestVerificationToken"\s+value="([^"]+)"', page_content)
                    if token_match:
                        token = token_match.group(1)
                        _LOGGER.info("✅ Found token in page HTML")
                except Exception as e:
                    _LOGGER.warning("Failed to extract token from HTML: %s", e)
            
            # Method 4: Check if we're already on a different page
            if not token:
                current_url = self.page.url
                _LOGGER.info("Current URL: %s", current_url)
                
                # If we're redirected, try to get the token from the current page
                if "login" not in current_url.lower():
                    _LOGGER.info("Appears to be redirected, checking current page for token...")
                    try:
                        token_input = self.page.locator('input[name="__RequestVerificationToken"]')
                        if token_input.count() > 0:
                            token = token_input.first.get_attribute('value')
                            _LOGGER.info("✅ Found token on redirected page")
                    except:
                        pass
            
            if token:
                _LOGGER.info("✅ Got request verification token: %s...", token[:20])
                return token
            else:
                _LOGGER.error("❌ Could not find request verification token")
                return None
                
        except Exception as e:
            _LOGGER.error("Failed to get request verification token: %s", e)
            return None
    
    def detect_image_captcha(self) -> bool:
        """Detect if an image captcha modal is present."""
        try:
            _LOGGER.info("🔍 Checking for image captcha...")
            
            # First check: Have we detected a captcha request?
            if hasattr(self, 'captcha_request') and self.captcha_request:
                _LOGGER.error(f"🚨 CAPTCHA REQUEST DETECTED: {self.captcha_request['url']}")
                _LOGGER.error("🚨 This indicates an image captcha was loaded - treating as captcha detected")
                return True
            
            # Primary check: Look for the specific instruction text that appears
            try:
                # This is the most reliable indicator - the instruction text
                instruction_elements = self.page.locator("div.rc-imageselect-desc-no-canonical")
                if instruction_elements.count() > 0:
                    for i in range(instruction_elements.count()):
                        element = instruction_elements.nth(i)
                        if element and element.is_visible():
                            text = element.text_content() or ""
                            if "Select all" in text and ("squares with" in text or "images with" in text):
                                _LOGGER.error(f"❌ IMAGE CAPTCHA DETECTED! Text: {text}")
                                return True
            except Exception as e:
                _LOGGER.debug(f"Primary instruction check failed: {e}")
            
            # Secondary check: Look for the overall captcha structure
            try:
                payload_elements = self.page.locator("div.rc-imageselect-payload")
                if payload_elements.count() > 0:
                    for i in range(payload_elements.count()):
                        element = payload_elements.nth(i)
                        if element and element.is_visible():
                            # Double-check by looking for the instruction text within this element
                            try:
                                instruction_text = element.locator("div.rc-imageselect-desc-no-canonical").text_content() or ""
                                if "Select all" in instruction_text:
                                    _LOGGER.error(f"❌ IMAGE CAPTCHA DETECTED via payload! Text: {instruction_text}")
                                    return True
                            except:
                                # If we can't get the text, but the payload is visible, it's likely a captcha
                                _LOGGER.error("❌ IMAGE CAPTCHA DETECTED via payload structure!")
                                return True
            except Exception as e:
                _LOGGER.debug(f"Secondary payload check failed: {e}")
            
            # Tertiary check: Look for the image grid
            try:
                table_elements = self.page.locator("table.rc-imageselect-table")
                if table_elements.count() > 0:
                    for i in range(table_elements.count()):
                        element = table_elements.nth(i)
                        if element and element.is_visible():
                            _LOGGER.error("❌ IMAGE CAPTCHA DETECTED via image grid!")
                            return True
            except Exception as e:
                _LOGGER.debug(f"Tertiary table check failed: {e}")
            
            # Fallback: Check for any rc-imageselect elements
            try:
                any_captcha_elements = self.page.locator("[class*='rc-imageselect']")
                if any_captcha_elements.count() > 0:
                    for i in range(any_captcha_elements.count()):
                        element = any_captcha_elements.nth(i)
                        if element and element.is_visible():
                            # Only flag if it's a substantial captcha element, not just CSS classes
                            class_name = element.get_attribute('class') or ''
                            if any(keyword in class_name for keyword in ['payload', 'instructions', 'challenge', 'table']):
                                _LOGGER.error(f"❌ IMAGE CAPTCHA DETECTED via class: {class_name}")
                                return True
            except Exception as e:
                _LOGGER.debug(f"Fallback class check failed: {e}")
            
            _LOGGER.info("✅ No image captcha detected")
            return False
            
        except Exception as e:
            _LOGGER.error(f"❌ Error detecting image captcha: {e}")
            # If we can't detect, assume no captcha to avoid false positives
            return False

    def solve_recaptcha(self) -> Optional[str]:
        """Solve the invisible reCAPTCHA v2 and return the response token."""
        try:
            _LOGGER.info("Handling invisible reCAPTCHA v2...")
            
            # For invisible reCAPTCHA v2, we need to trigger it by clicking the login button
            # This will cause the reCAPTCHA to solve and generate a response token
            _LOGGER.info("Triggering reCAPTCHA by clicking login button...")
            
            # Find and click the login button to trigger reCAPTCHA
            login_button_selectors = [
                'button.btn-primary.loginBtn.g-recaptcha',  # The exact login button
                'button.loginBtn.g-recaptcha',              # Login button with reCAPTCHA
                'button.loginBtn',                          # Login button class
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    button = self.page.locator(selector)
                    if button.count() > 0:
                        login_button = button.first
                        _LOGGER.info("✅ Found login button with selector: %s", selector)
                        break
                except:
                    continue
            
            if not login_button:
                _LOGGER.warning("No login button found to trigger reCAPTCHA")
                return None
            
            # Click the button to trigger reCAPTCHA
            _LOGGER.info("Clicking login button to trigger reCAPTCHA...")
            login_button.click()
            _LOGGER.info("✅ Login button clicked, reCAPTCHA should now be solving...")
            
            # Wait for reCAPTCHA to be solved and response token to appear
            max_wait_time = 15
            check_interval = 0.5
            
            for i in range(int(max_wait_time / check_interval)):
                try:
                    # Look for reCAPTCHA response token in multiple locations
                    recaptcha_response = self.page.locator('textarea[name="g-recaptcha-response"]')
                    if recaptcha_response.count() > 0:
                        token = recaptcha_response.input_value()
                        if token and len(token) > 100:  # reCAPTCHA tokens are long
                            _LOGGER.info("✅ reCAPTCHA response token found!")
                            return token
                    
                    # Also check if the token is in a hidden input or other location
                    hidden_recaptcha = self.page.locator('input[name="g-recaptcha-response"], [name="g-recaptcha-response"]')
                    if hidden_recaptcha.count() > 0:
                        token = hidden_recaptcha.first.get_attribute('value')
                        if token and len(token) > 100:
                            _LOGGER.info("✅ reCAPTCHA response token found in hidden input!")
                            return token
                    
                    # Check if reCAPTCHA is visible and has been solved
                    recaptcha_elements = self.page.locator('.g-recaptcha, [data-sitekey]')
                    if recaptcha_elements.count() > 0:
                        for j in range(recaptcha_elements.count()):
                            try:
                                recaptcha = recaptcha_elements.nth(j)
                                # Check if reCAPTCHA shows as solved
                                aria_label = recaptcha.get_attribute('aria-label') or ''
                                if 'solved' in aria_label.lower() or 'verified' in aria_label.lower():
                                    _LOGGER.info("✅ reCAPTCHA appears to be solved!")
                                    # Try to find the token again
                                    break
                            except:
                                pass
                
                except Exception as e:
                    _LOGGER.debug("reCAPTCHA check iteration %d failed: %s", i, e)
                
                time.sleep(check_interval)
                if i % 4 == 0:  # Log every 2 seconds
                    _LOGGER.info("Waiting for reCAPTCHA response... (%d seconds elapsed)", i * check_interval)
            
            _LOGGER.warning("⚠️ reCAPTCHA may not be fully solved, but continuing...")
            return None
            
        except Exception as e:
            _LOGGER.error("Failed to solve reCAPTCHA: %s", e)
            return None
    
    def fill_login_form(self) -> bool:
        """Fill in the login form fields."""
        try:
            _LOGGER.info("Filling in login form fields...")
            
            # Wait for form fields to be ready
            _LOGGER.info("Waiting for form fields to be ready...")
            self.page.wait_for_selector('input[name="LoginEmail"]', timeout=10000)
            self.page.wait_for_selector('input[name="LoginPassword"]', timeout=10000)
            
            # Fill in all required form fields with human-like behavior
            _LOGGER.info("Filling email field: %s", self.email)
            
            # Move mouse to email field naturally
            email_field = self.page.locator('input[name="LoginEmail"]')
            email_box = email_field.bounding_box()
            if email_box:
                self.page.mouse.move(
                    email_box['x'] + email_box['width'] / 2 + random.uniform(-5, 5),
                    email_box['y'] + email_box['height'] / 2 + random.uniform(-2, 2)
                )
                time.sleep(random.uniform(0.3, 0.8))
            
            # Click and type with human-like delays
            email_field.click()
            time.sleep(random.uniform(0.2, 0.5))
            
            # Type email character by character with random delays
            for char in self.email:
                email_field.type(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(random.uniform(0.5, 1.0))
            
            _LOGGER.info("Filling password field...")
            password_field = self.page.locator('input[name="LoginPassword"]')
            
            # Move mouse to password field naturally
            password_box = password_field.bounding_box()
            if password_box:
                self.page.mouse.move(
                    password_box['x'] + password_box['width'] / 2 + random.uniform(-5, 5),
                    password_box['y'] + password_box['height'] / 2 + random.uniform(-2, 2)
                )
                time.sleep(random.uniform(0.3, 0.8))
            
            # Click and type with human-like delays
            password_field.click()
            time.sleep(random.uniform(0.2, 0.5))
            
            # Type password character by character with random delays
            for char in self.password:
                password_field.type(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            time.sleep(random.uniform(0.5, 1.0))
            
            # Submit the form using Enter key instead of clicking button
            _LOGGER.info("Submitting form with Enter key...")
            password_field.press("Enter")
            _LOGGER.info("✅ Enter key pressed - form submitted")
            
            # IMMEDIATELY check for image captcha after Enter key
            _LOGGER.info("🔍 IMMEDIATE check for image captcha after Enter key...")
            
            # Wait for DOM to potentially update with new captcha elements
            try:
                # Wait for either the captcha to appear OR for navigation to start
                _LOGGER.info("Waiting for DOM update after Enter key...")
                
                # Check if image captcha appears within 3 seconds
                captcha_appeared = False
                for i in range(30):  # Check 30 times over 3 seconds
                    if self.detect_image_captcha():
                        _LOGGER.error("❌ IMAGE CAPTCHA DETECTED IMMEDIATELY AFTER ENTER KEY!")
                        captcha_appeared = True
                        break
                    
                    # Also check if we're starting to navigate away (good sign)
                    try:
                        current_url = self.page.url
                        if "Dashboard" in current_url or "Login" not in current_url:
                            _LOGGER.info("✅ Navigation started - no captcha appeared")
                            break
                    except:
                        pass
                    
                    time.sleep(0.1)  # Check every 100ms
                
                if captcha_appeared:
                    return False
                    
            except Exception as e:
                _LOGGER.warning(f"Error during captcha check after Enter: {e}")
                # Continue anyway, main flow will catch it
            
            # Wait a moment for the form submission to process
            time.sleep(random.uniform(1.0, 2.0))
            
            # Check remember me if not already checked (do this before form submission)
            try:
                remember_me = self.page.locator('input[name="RememberMe"]')
                if remember_me.count() > 0 and not remember_me.first.is_checked():
                    remember_me.first.check()
            except:
                pass
            
            _LOGGER.info("✅ Form submitted successfully - returning to main flow")
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to fill login form: %s", e)
            return False

    def click_login_button(self) -> bool:
        """Click the login button to submit the form."""
        try:
            _LOGGER.info("Looking for login button...")
            
            # Try multiple selectors for the login button
            login_button_selectors = [
                'button.btn-primary.loginBtn.g-recaptcha',
                'button.loginBtn.g-recaptcha', 
                'button.loginBtn',
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign In")'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = self.page.locator(selector).first
                    if login_button.is_visible():
                        _LOGGER.info("Found visible login button with selector: %s", selector)
                        break
                except Exception:
                    continue
            
            if not login_button:
                _LOGGER.error("❌ No login button found with any selector")
                return False
            
            # Wait for button to be visible and clickable
            try:
                login_button.wait_for(state="visible", timeout=10000)
            except Exception as e:
                _LOGGER.warning("Button not visible, trying force click: %s", e)
            
            # Check the button attributes to understand how reCAPTCHA is configured
            _LOGGER.info("Analyzing login button attributes...")
            button_attributes = {}
            for attr in ['data-callback', 'data-sitekey', 'data-action', 'onclick']:
                try:
                    value = login_button.get_attribute(attr)
                    if value:
                        button_attributes[attr] = value
                        _LOGGER.info(f"Button {attr}: {value}")
                except Exception:
                    pass
            
            # Execute the invisible reCAPTCHA properly
            if 'data-sitekey' in button_attributes:
                site_key = button_attributes['data-sitekey']
                _LOGGER.info(f"Executing invisible reCAPTCHA with site key: {site_key}")
                
                # Wait for reCAPTCHA to be fully loaded and ready
                _LOGGER.info("Waiting for reCAPTCHA to be fully loaded...")
                try:
                    # Wait for grecaptcha to be available and ready
                    self.page.wait_for_function("""
                        () => {
                            return typeof grecaptcha !== 'undefined' && 
                                   grecaptcha.ready && 
                                   typeof grecaptcha.ready === 'function';
                        }
                    """, timeout=15000)
                    _LOGGER.info("✅ reCAPTCHA library is loaded and ready")
                    
                    # Wait a bit more for reCAPTCHA to fully initialize
                    time.sleep(random.uniform(1.0, 2.0))
                    
                    # Execute the invisible reCAPTCHA
                    _LOGGER.info("Executing invisible reCAPTCHA...")
                    result = self.page.evaluate(f"""
                        return new Promise((resolve, reject) => {{
                            try {{
                                if (typeof grecaptcha !== 'undefined' && grecaptcha.ready) {{
                                    grecaptcha.ready(function() {{
                                        grecaptcha.execute('{site_key}', {{action: 'submit'}}).then(function(token) {{
                                            console.log('reCAPTCHA executed successfully, token:', token);
                                            resolve({{success: true, token: token}});
                                        }}).catch(function(error) {{
                                            console.error('reCAPTCHA execution failed:', error);
                                            reject(error);
                                        }});
                                    }});
                                }} else {{
                                    reject('grecaptcha not ready');
                                }}
                            }} catch (error) {{
                                reject(error);
                            }}
                        }});
                    """)
                    
                    if result and result.get('success'):
                        _LOGGER.info("✅ reCAPTCHA executed successfully")
                    else:
                        _LOGGER.warning("reCAPTCHA execution returned unexpected result")
                        
                except Exception as e:
                    _LOGGER.warning(f"reCAPTCHA execution failed: {e}")
                    
                    # Fallback: try simpler reCAPTCHA execution
                    try:
                        _LOGGER.info("Trying fallback reCAPTCHA execution...")
                        self.page.evaluate(f"""
                            if (typeof grecaptcha !== 'undefined' && grecaptcha.ready) {{
                                grecaptcha.ready(function() {{
                                    grecaptcha.execute('{site_key}');
                                }});
                            }}
                        """)
                        _LOGGER.info("✅ Fallback reCAPTCHA execution attempted")
                    except Exception as e2:
                        _LOGGER.warning(f"Fallback also failed: {e2}")
            else:
                _LOGGER.warning("No site key found for reCAPTCHA")
            
            # Wait for reCAPTCHA to process
            _LOGGER.info("Waiting for reCAPTCHA to process...")
            time.sleep(random.uniform(2.0, 4.0))
            
            # Check for image captcha modal - if it appears, fail fast
            _LOGGER.info("Checking for image captcha modal...")
            try:
                # Look for common image captcha selectors
                image_captcha_selectors = [
                    '.rc-imageselect-payload',  # The specific image captcha we're seeing
                    '.recaptcha-image-container',
                    '.g-recaptcha-response',
                    'iframe[src*="recaptcha"]',
                    '.recaptcha-challenge',
                    '#recaptcha_challenge_image',
                    '.captcha-image',
                    'img[src*="captcha"]',
                    '[class*="rc-imageselect"]',  # Any reCAPTCHA image select elements
                    '[class*="imageselect"]'      # Broader image select pattern
                ]
                
                for selector in image_captcha_selectors:
                    try:
                        captcha_element = self.page.locator(selector).first
                        if captcha_element.is_visible(timeout=1000):
                            _LOGGER.error(f"❌ IMAGE CAPTCHA DETECTED with selector: {selector}")
                            _LOGGER.error("Stealth techniques failed - image captcha is visible")
                            _LOGGER.error("This means the automation was detected")
                            return False
                    except Exception:
                        continue
                
                # Also check for any visible captcha text or instructions
                captcha_text_selectors = [
                    'text=Please complete the captcha',
                    'text=Please solve the captcha',
                    'text=Enter the text shown in the image',
                    'text=Type the characters you see',
                    'text=Select all squares with',  # The specific image captcha text we're seeing
                    'text=If there are none, click skip',  # Another part of the image captcha
                    'text=Please try again',  # Error message from image captcha
                    'text=Please select all matching images',  # Another error message
                    'text=Please also check the new images',  # Another error message
                    'text=Please select around the object'  # Another error message
                ]
                
                for selector in captcha_text_selectors:
                    try:
                        captcha_text = self.page.locator(selector).first
                        if captcha_text.is_visible(timeout=1000):
                            _LOGGER.error(f"❌ CAPTCHA TEXT DETECTED: {selector}")
                            _LOGGER.error("Stealth techniques failed - captcha instructions are visible")
                            return False
                    except Exception:
                        continue
                
                _LOGGER.info("✅ No image captcha detected - proceeding with login")
                
                # Additional check: Look for the specific HTML structure we're seeing
                try:
                    # Check for the specific rc-imageselect-payload div
                    payload_check = self.page.locator('.rc-imageselect-payload').count()
                    if payload_check > 0:
                        _LOGGER.error("❌ IMAGE CAPTCHA DETECTED: rc-imageselect-payload div found")
                        _LOGGER.error("This is the exact image captcha we want to avoid")
                        _LOGGER.error("Stealth techniques failed - automation was detected")
                        return False
                    
                    # Check for any elements with rc-imageselect in the class name
                    imageselect_check = self.page.locator('[class*="rc-imageselect"]').count()
                    if imageselect_check > 0:
                        _LOGGER.error(f"❌ IMAGE CAPTCHA DETECTED: {imageselect_check} rc-imageselect elements found")
                        _LOGGER.error("Stealth techniques failed - automation was detected")
                        return False
                        
                except Exception as e:
                    _LOGGER.warning(f"Error in additional image captcha check: {e}")
                
            except Exception as e:
                _LOGGER.warning(f"Error checking for image captcha: {e}")
            
            # Move mouse to button naturally before clicking
            button_box = login_button.bounding_box()
            if button_box:
                # Move to a random point near the button first
                self.page.mouse.move(
                    button_box['x'] + random.uniform(-20, 20),
                    button_box['y'] + random.uniform(-20, 20)
                )
                time.sleep(random.uniform(0.2, 0.6))
                
                # Then move to the button center with slight randomness
                self.page.mouse.move(
                    button_box['x'] + button_box['width'] / 2 + random.uniform(-3, 3),
                    button_box['y'] + button_box['height'] / 2 + random.uniform(-2, 2)
                )
                time.sleep(random.uniform(0.1, 0.4))
            
            # Click the login button
            _LOGGER.info("Clicking login button...")
            try:
                login_button.click(force=True)
                _LOGGER.info("✅ Login button clicked successfully")
            except Exception as e:
                _LOGGER.error("❌ Failed to click login button: %s", e)
                return False
            
            # Wait a moment for the form submission to process
            time.sleep(random.uniform(1.5, 2.5))
            
            return True
                    
        except Exception as e:
            _LOGGER.error("Error in click_login_button: %s", e)
            return False
    
    def cleanup(self):
        """Clean up browser resources."""
        try:
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.close()
                except:
                    pass
                self.page = None
            
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.close()
                except:
                    pass
                self.context = None
            
            if hasattr(self, 'browser') and self.browser:
                try:
                    self.browser.close()
                except:
                    pass
                self.browser = None
                
            if hasattr(self, 'playwright') and self.playwright:
                try:
                    self.playwright.stop()
                except:
                    pass
                self.playwright = None
                
            # Reset other state variables
            if hasattr(self, 'login_cookies'):
                self.login_cookies = None
                
        except Exception as e:
            _LOGGER.warning("Error during cleanup: %s", e)

    def get_fresh_cookies(self):
        """Get cookies by automating the login process."""
        for attempt in range(1, 4):  # Try up to 3 times
            try:
                _LOGGER.info("🔄 Attempt %d: Setting up browser...", attempt)
                
                # Ensure clean state before each attempt
                self.cleanup()
                
                if not self.setup_browser():
                    _LOGGER.error("❌ Failed to setup browser on attempt %d", attempt)
                    continue
                
                # Set up request interception to capture login cookies
                self.setup_request_interception()
                
                # Navigate to main page (which contains the login form)
                _LOGGER.info("🌐 Navigating to main page...")
                self.page.goto("https://mysmartenergy.psegliny.com/")
                self.page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                # Check for image captcha
                if self.detect_image_captcha():
                    _LOGGER.error("❌ Image captcha detected - failing fast")
                    continue
                
                _LOGGER.info("✅ No image captcha detected")
                
                # Get request verification token
                if not self.get_request_verification_token():
                    _LOGGER.error("❌ Failed to get verification token")
                    continue
                
                # Fill and submit login form
                if not self.fill_login_form():
                    _LOGGER.error("❌ Login form submission failed (likely due to image captcha)")
                    continue
                
                # Wait for successful login redirect to Dashboard
                try:
                    _LOGGER.info("⏳ Waiting for successful login redirect...")
                    
                    # Log the initial URL after form submission
                    initial_url = self.page.url
                    _LOGGER.info("Initial URL after form submission: %s", initial_url)
                    
                    # Use a shorter timeout and check for captcha periodically
                    start_time = time.time()
                    timeout = 30000  # 30 seconds
                    check_interval = 2000  # Check every 2 seconds
                    
                    while time.time() - start_time < timeout / 1000:
                        try:
                            # Check if we've reached the dashboard or any successful redirect
                            current_url = self.page.url
                            _LOGGER.info("Checking redirect status - current URL: %s (attempt %d)", current_url, int((time.time() - start_time) / (check_interval / 1000)) + 1)
                            if ("Dashboard" in current_url or 
                                "Login" not in current_url or 
                                "login" not in current_url.lower() or
                                current_url != "https://mysmartenergy.psegliny.com/"):
                                _LOGGER.info("✅ Successfully redirected from login page to: %s", current_url)
                                break
                            
                            # Check for image captcha
                            if self.detect_image_captcha():
                                _LOGGER.error("❌ Image captcha appeared during redirect wait - failing fast")
                                raise Exception("Image captcha detected during redirect")
                            
                            # Wait a bit before next check
                            time.sleep(check_interval / 1000)
                            
                        except Exception as e:
                            if "Image captcha detected" in str(e):
                                raise e
                            # Continue waiting for redirect
                            pass
                    else:
                        # Timeout reached
                        raise Exception("Timeout waiting for successful login redirect")
                        
                except Exception as e:
                    _LOGGER.error("❌ Failed to detect successful login redirect: %s", e)
                    continue
                
                # Check if we got cookies from request headers
                if self.login_cookies:
                    _LOGGER.info("✅ SUCCESS: Got cookies from request headers: %s", self.login_cookies)
                    return self.login_cookies
                
                # Wait a bit more for cookies to be set in the browser
                _LOGGER.info("Waiting for cookies to be set in browser...")
                time.sleep(3)
                
                # Check if we're still on the login page (which would indicate failure)
                current_url = self.page.url
                _LOGGER.info("Current URL after waiting: %s", current_url)
                
                if current_url == "https://mysmartenergy.psegliny.com/" or "login" in current_url.lower():
                    _LOGGER.warning("⚠️ Still on login page - form submission may have failed")
                    _LOGGER.warning("Checking for error messages...")
                    
                    # Look for error messages
                    try:
                        error_elements = self.page.locator('.alert, .error, .text-danger, [class*="error"], [class*="alert"]')
                        if error_elements.count() > 0:
                            for i in range(error_elements.count()):
                                error_text = error_elements.nth(i).text_content()
                                if error_text:
                                    _LOGGER.error("❌ Error message found: %s", error_text.strip())
                    except Exception as e:
                        _LOGGER.debug("Could not check for error messages: %s", e)
                
                # Fallback: get cookies from browser context
                _LOGGER.info("🔄 No cookies in request headers, checking browser context...")
                context_cookies = self.page.context.cookies()
                _LOGGER.info("Found %d cookies in browser context", len(context_cookies))
                
                if context_cookies:
                    # Log all cookies for debugging
                    for i, cookie in enumerate(context_cookies):
                        _LOGGER.debug("Cookie %d: %s = %s", i, cookie['name'], cookie['value'][:20] + "..." if len(cookie['value']) > 20 else cookie['value'])
                    
                    # Format cookies for use
                    cookie_dict = {}
                    for cookie in context_cookies:
                        if cookie['name'] in ['__RequestVerificationToken', 'MM_SID']:
                            cookie_dict[cookie['name']] = cookie['value']
                    
                    if cookie_dict:
                        _LOGGER.info("✅ SUCCESS: Got cookies from browser context: %s", cookie_dict)
                        # Convert to string format for compatibility - MM_SID must come FIRST
                        cookie_strings = []
                        # Ensure MM_SID is first, then __RequestVerificationToken
                        if 'MM_SID' in cookie_dict:
                            cookie_strings.append(f"MM_SID={cookie_dict['MM_SID']}")
                        if '__RequestVerificationToken' in cookie_dict:
                            cookie_strings.append(f"__RequestVerificationToken={cookie_dict['__RequestVerificationToken']}")
                        result = "; ".join(cookie_strings)
                        _LOGGER.info("🎉 LOGIN SUCCESSFUL - Returning cookies immediately!")
                        return result
                    else:
                        _LOGGER.warning("❌ Required cookies not found in browser context")
                        _LOGGER.warning("Looking for: __RequestVerificationToken, MM_SID")
                        _LOGGER.warning("Available cookies: %s", [c['name'] for c in context_cookies])
                else:
                    _LOGGER.error("❌ No cookies found in browser context")
                
                continue
                
            except Exception as e:
                _LOGGER.error("❌ Failed on attempt %d: %s", attempt, e)
                # Always cleanup to avoid resource leaks
                try:
                    self.cleanup()
                except Exception as cleanup_error:
                    _LOGGER.warning(f"Cleanup error: {cleanup_error}")
                continue
        
        _LOGGER.error("❌ All attempts failed")
        return None


def get_pseg_cookies(email: str, password: str):
    """Get PSEG cookies using automated login."""
    _LOGGER.info("🔐 Getting PSEG cookies using automated login...")
    _LOGGER.info("This will simulate a real mouse click to bypass reCAPTCHA.")
    
    cookie_getter = PSEGAutoLogin(email, password)
    cookie_string = cookie_getter.get_fresh_cookies()
    
    if cookie_string:
        _LOGGER.info("✅ SUCCESS! Cookies obtained successfully!")
        _LOGGER.info("=" * 80)
        _LOGGER.info("COOKIE STRING (copy this for testing):")
        _LOGGER.info("=" * 80)
        _LOGGER.info(cookie_string)
        _LOGGER.info("=" * 80)
        _LOGGER.info("📋 Cookie details:")
        _LOGGER.info(f"  - Total length: {len(cookie_string)} characters")
        _LOGGER.info(f"  - Cookie pairs: {cookie_string.count(';') + 1}")
        return cookie_string
    else:
        _LOGGER.error("❌ Failed to get cookies")
        _LOGGER.error("Check the logs above for details.")
        return None


if __name__ == "__main__":
    print("🍪 PSEG Cookie Acquisition Tool")
    print("=" * 50)
    print()
    
    # Replace with your credentials
    email = "eman3488+psegliny@gmail.com"
    password = "NXg=7.iZ:0voA1\"'"
    
    cookie_string = get_pseg_cookies(email, password)
    
    if cookie_string:
        print("\n🎉 READY TO TEST!")
        print("You can now use this cookie string with:")
        print("  python3 test_psegli_api_standalone.py")
        print()
        print("Or copy it directly into your integration configuration.")
    else:
        print("\n❌ Cookie acquisition failed.")
        print("Check the logs above for details.")