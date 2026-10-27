#!/usr/bin/env python3
"""
PSEG Long Island Auto Login Addon
Uses realistic browsing pattern to avoid detection and obtain authentication cookies.
"""

import asyncio
import logging
import random
import time
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)

class PSEGAutoLogin:
    """PSEG Long Island automated login using realistic browsing pattern."""
    
    def __init__(
        self,
        email: str,
        password: str,
        mfa_code: Optional[str] = None,
        mfa_method: str = "sms",  # "email" or "sms"
        headless: bool = True,
    ):
        """Initialize PSEG auto login."""
        self.email = email
        self.password = password
        self.mfa_code = mfa_code
        self.mfa_method = mfa_method.lower() if mfa_method else "sms"
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.login_cookies = {}
        self.exceptional_dashboard_data = None
        
        # URLs for the realistic browsing flow
        self.brave_search_url = "https://search.brave.com/search?q=pseg+long+island&source=desktop"
        self.pseg_main_url = "https://www.psegliny.com/"
        self.login_page_url = "https://myaccount.psegliny.com/user/login"
        self.id_domain = "https://id.myaccount.psegliny.com/"
        self.dashboard_url = "https://myaccount.psegliny.com/dashboards"
        self.exceptional_dashboard = "https://myaccount.psegliny.com/dashboards/exceptionaldashboard"
        self.mysmartenergy_redirect = "https://myaccount.psegliny.com/LI/Header/RedirectMDMWidget"
        self.final_dashboard = "https://mysmartenergy.psegliny.com/Dashboard"
    
    async def setup_browser(self) -> bool:
        """Initialize Playwright browser with stealth options."""
        try:
            _LOGGER.info("🚀 Initializing Playwright browser...")
            self.playwright = await async_playwright().start()
            
            # Launch browser with stealth options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection'
                ]
            )
            
            # Create context with stealth options
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                extra_http_headers={
                    'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"'
                },
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                screen={
                    'width': 1920,
                    'height': 1080
                }
            )
            
            # Create page and apply stealth
            self.page = await self.context.new_page()
            
            # Apply stealth techniques
            await self.page.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                    configurable: true
                });
                
                // Ensure window.chrome exists
                if (!window.chrome) {
                    Object.defineProperty(window, 'chrome', {
                        get: () => ({
                            runtime: {},
                            loadTimes: function() {},
                            csi: function() {},
                            app: {}
                        }),
                        configurable: true
                    });
                }
                
                // Override navigator.permissions
                if (!navigator.permissions) {
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: function() { return Promise.resolve({ state: 'granted' }); }
                        }),
                        configurable: true
                    });
                }
                
                // Override navigator.plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const pluginArray = [];
                        const pluginNames = ['Chrome PDF Plugin', 'Chrome PDF Viewer', 'Native Client'];
                        const pluginDescriptions = ['Portable Document Format', 'Portable Document Format', 'Native Client Executable'];
                        const pluginFilenames = ['internal-pdf-viewer', 'mhjfbmdgcfjbbpaeojofohoefgiehjai', 'internal-nacl-plugin'];
                        
                        for (let i = 0; i < pluginNames.length; i++) {
                            const plugin = {
                                name: pluginNames[i],
                                description: pluginDescriptions[i],
                                filename: pluginFilenames[i]
                            };
                            pluginArray[i] = plugin;
                        }
                        
                        Object.defineProperty(pluginArray, 'length', { value: pluginNames.length });
                        return pluginArray;
                    },
                    configurable: true
                });
                
                // Override window dimensions
                Object.defineProperty(window, 'outerWidth', {
                    get: () => 1922,
                    configurable: true
                });
                Object.defineProperty(window, 'outerHeight', {
                    get: () => 1055,
                    configurable: true
                });
                
                // Override deviceMemory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                    configurable: true
                });
                
                console.log('🔍 Stealth techniques applied');
            """)
            
            # Set up request interception
            await self.setup_request_interception()
            
            _LOGGER.info("✅ Playwright browser initialized successfully")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to setup browser: {e}")
            return False
    
    async def setup_request_interception(self):
        """Set up request interception to capture cookies and exceptional dashboard data."""
        try:
            await self.page.route("**/*", self.handle_request)
            _LOGGER.info("✅ Request interception setup complete")
        except Exception as e:
            _LOGGER.warning(f"Could not setup request interception: {e}")
    
    async def handle_request(self, route):
        """Handle intercepted requests to capture cookies and exceptional dashboard data."""
        try:
            request = route.request
            if "mysmartenergy.psegliny.com" in request.url:
                # Capture cookies from MySmartEnergy requests
                if hasattr(request, 'headers') and 'cookie' in request.headers:
                    cookie_header = request.headers['cookie']
                    if cookie_header:
                        # Parse cookies and store them
                        self.parse_cookies(cookie_header)
            elif "exceptionaldashboard" in request.url and request.method == "POST":
                # Capture exceptional dashboard request data
                _LOGGER.info("🔍 Intercepted exceptional dashboard POST request")
                self.exceptional_dashboard_data = {
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data if hasattr(request, 'post_data') else None
                }
                _LOGGER.info(f"📋 Captured exceptional dashboard data")
        except Exception as e:
            _LOGGER.debug(f"Error handling request: {e}")
        
        # Continue with the request
        await route.continue_()
    
    def _log_mfa_error(self, current_url: str):
        """Log clear error when MFA is required."""
        _LOGGER.error("❌ PSEG now requires multi-factor authentication (MFA).")
        _LOGGER.error("   After entering your password, you receive a verification code via email or SMS.")
        _LOGGER.error("   This addon cannot complete MFA automatically.")
        _LOGGER.error("   Workaround: Use the 'mfa_code' parameter when calling the addon API")
        _LOGGER.error("   (check your email for the code, then retry with the code).")
        _LOGGER.error("   Or log in manually in a browser and export cookies for the integration.")
        _LOGGER.error(f"   Current URL: {current_url[:100]}...")
    
    def parse_cookies(self, cookie_header: str):
        """Parse cookie header and extract important cookies."""
        try:
            cookies = cookie_header.split(';')
            for cookie in cookies:
                cookie = cookie.strip()
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    
                    # Store important cookies
                    if name in ['MM_SID', '__RequestVerificationToken', 'ASP.NET_SessionId']:
                        self.login_cookies[name] = value
        except Exception as e:
            _LOGGER.warning(f"Error parsing cookies: {e}")
    
    async def simulate_realistic_browsing(self) -> bool:
        """Simulate realistic browsing pattern to avoid detection."""
        try:
            _LOGGER.info("🌐 Starting realistic browsing pattern...")
            
            # Set page timeout to be more generous for the entire process
            self.page.set_default_timeout(30000)  # 30 seconds instead of 20
            
            # Step 1: Start with Brave search
            _LOGGER.info("🔍 Step 1: Navigating to Brave search...")
            await self.page.goto(self.brave_search_url, wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(2.0, 3.0))
            
            # Simulate reading search results
            await self.page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            _LOGGER.info("✅ Brave search loaded")
            
            # Step 2: Navigate to PSEG main site
            _LOGGER.info("🏠 Step 2: Navigating to PSEG main site...")
            await self.page.goto(self.pseg_main_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle')
            
            _LOGGER.info("✅ PSEG main site loaded")
            
            # Step 3: Find and click login button
            _LOGGER.info("🔑 Step 3: Looking for login button...")
            login_button = await self.page.wait_for_selector('#login', timeout=10000)
            
            if not login_button:
                _LOGGER.error("❌ Login button not found")
                return False
            
            _LOGGER.info("✅ Login button found, clicking...")
            await login_button.click()
            
            # Wait for login page to load
            try:
                await self.page.wait_for_url(lambda url: "id.myaccount.psegliny.com" in url, timeout=15000)
                await self.page.wait_for_load_state('networkidle')
                _LOGGER.info("✅ Login page loaded")
            except Exception as e:
                _LOGGER.warning(f"⚠️ Login page navigation wait failed: {e}")
                # Check current URL and continue if we're already on the right page
                current_url = self.page.url
                if "id.myaccount.psegliny.com" in current_url:
                    _LOGGER.info(f"✅ Already on login page: {current_url}")
                else:
                    _LOGGER.error(f"❌ Not on expected login page: {current_url}")
                    return False
            
            # Step 4: Fill login form
            _LOGGER.info("📝 Step 4: Filling login form...")
            
            # Wait for form fields
            await self.page.wait_for_selector('input[name="username"], input[type="email"], input[type="text"]', timeout=10000)
            await self.page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)
            
            # Find username field
            username_field = await self.page.query_selector('input[name="username"], input[type="email"], input[type="text"]')
            if username_field:
                await username_field.click()
                await username_field.fill(self.email)
                _LOGGER.info("✅ Username entered")
            else:
                _LOGGER.error("❌ Username field not found")
                return False
            
            # Find password field
            password_field = await self.page.query_selector('input[name="password"], input[type="password"]')
            if password_field:
                await password_field.click()
                await password_field.fill(self.password)
                _LOGGER.info("✅ Password entered")
            else:
                _LOGGER.error("❌ Password field not found")
                return False
            
            # Find and click LOG IN button
            _LOGGER.info("🔘 Looking for LOG IN button...")
            login_submit_button = await self.page.wait_for_selector('button[type="submit"]:has-text("LOG IN"), button:has-text("LOG IN")', timeout=10000)
            
            if not login_submit_button:
                _LOGGER.error("❌ LOG IN button not found")
                return False
            
            _LOGGER.info("✅ LOG IN button found, clicking...")
            
            # Click the login button
            await login_submit_button.click()
            
            # Wait for page to settle (either dashboard redirect or MFA challenge)
            _LOGGER.info("🔄 Waiting for dashboard or MFA challenge...")
            await asyncio.sleep(3.0)
            
            current_url = self.page.url
            
            # Check if we hit an MFA/verification challenge (PSEG added MFA in late 2024/early 2025)
            if "id.myaccount.psegliny.com" in current_url and "dashboards" not in current_url:
                page_content = await self.page.content()
                mfa_indicators = [
                    "verification code", "enter the code", "one-time",
                    "multi-factor", "multi factor", "mfa", "2fa", "two-factor",
                    "authenticate", "verify your identity", "security code",
                    "we sent a code", "sent to your", "check your email"
                ]
                is_mfa_page = any(indicator in page_content.lower() for indicator in mfa_indicators)
                
                if is_mfa_page:
                    _LOGGER.info("🔐 MFA/verification challenge detected")
                    
                    # Select the requested delivery factor before sending a code.
                    # The provider often defaults to email, so skipping this for one
                    # method makes delivery depend on whichever factor Okta last used.
                    if self.mfa_method in {"sms", "email"}:
                        # "Use a different method" may reveal the requested factor.
                        diff_method = None
                        for diff_sel in ['a:has-text("Use a different method")', 'a:has-text("Try another way")', 'a:has-text("Choose a different")']:
                            diff_method = await self.page.query_selector(diff_sel)
                            if diff_method:
                                break
                        if diff_method:
                            _LOGGER.info("🔐 Expanding MFA delivery options...")
                            await diff_method.click()
                            await asyncio.sleep(2.0)
                        
                        delivery_selectors = {
                            "sms": [
                                'a:has-text("SMS")', 'a:has-text("Text")',
                                'button:has-text("SMS")', 'button:has-text("Text")',
                                'a:has-text("Send code via SMS")', 'a:has-text("Text me")',
                                'a:has-text("phone")', 'button:has-text("phone")',
                                '[data-se="sms"]', '[data-se="phone"]',
                            ],
                            "email": [
                                'a:has-text("Email")', 'button:has-text("Email")',
                                'a:has-text("Email me")', 'button:has-text("Email me")',
                                'a:has-text("Send code via email")',
                                'button:has-text("Send code via email")',
                                '[data-se="email"]', '[data-se="email-authenticator"]',
                            ],
                        }
                        method_clicked = False
                        for sel in delivery_selectors[self.mfa_method]:
                            el = await self.page.query_selector(sel)
                            if el:
                                _LOGGER.info("📨 Selecting %s MFA delivery", self.mfa_method)
                                await el.click()
                                await asyncio.sleep(2.0)
                                method_clicked = True
                                break
                        if not method_clicked:
                            _LOGGER.warning("⚠️ %s MFA option not found - saving page to mfa_page_debug.html for debug", self.mfa_method)
                            try:
                                debug_content = await self.page.content()
                                with open("mfa_page_debug.html", "w", encoding="utf-8") as f:
                                    f.write(debug_content)
                            except Exception:
                                pass
                    
                    # Click "Send code" / "Receive code" - required to trigger the verification code
                    send_selectors = (
                        [
                            'button:has-text("Receive a code via email")',
                            'input[value="Receive a code via email"]',
                            'a:has-text("Receive a code via email")',
                            'button:has-text("Email me a code")',
                            'input[value="Email me a code"]',
                        ] if self.mfa_method == "email" else [
                            'button:has-text("Receive a code via SMS")',
                            'input[value="Receive a code via SMS"]',
                            'a:has-text("Receive a code via SMS")',
                            'button:has-text("Send code via SMS")',
                            'button:has-text("Text me a code")',
                            'input[value="Text me a code"]',
                        ]
                    ) + [
                        'button:has-text("Send Code")',
                        'input[value="Send Code"]',
                        'input[value="Send code"]',
                        'button:has-text("Send code")',
                        'a:has-text("Send Code")',
                    ]
                    # Wait for the send/receive button to appear (page may load after SMS option click)
                    send_code_btn = None
                    for _ in range(3):  # Retry a few times as page may still be loading
                        for sel in send_selectors:
                            send_code_btn = await self.page.query_selector(sel)
                            if send_code_btn:
                                break
                        if send_code_btn:
                            break
                        await asyncio.sleep(1.5)
                    if send_code_btn:
                        _LOGGER.info("📤 Clicking to trigger verification code...")
                        await send_code_btn.click()
                        await asyncio.sleep(3.0)
                    
                    if self.mfa_code:
                        # Try to enter the MFA code
                        _LOGGER.info("📝 Entering MFA code...")
                        try:
                            # Okta typically uses input[name="answer"] or similar for verification codes
                            mfa_input = await self.page.query_selector(
                                'input[name="answer"], input[name="verificationCode"], '
                                'input[type="text"][autocomplete="one-time-code"], '
                                'input[id*="verification"], input[id*="answer"]'
                            )
                            if mfa_input:
                                await mfa_input.click()
                                await mfa_input.fill(self.mfa_code)
                                
                                # Find and click Verify/Submit button
                                verify_btn = await self.page.query_selector(
                                    'input[type="submit"], button[type="submit"], '
                                    'button:has-text("Verify"), button:has-text("Submit"), '
                                    'input[value="Verify"], input[value="Submit"]'
                                )
                                if verify_btn:
                                    await verify_btn.click()
                                    _LOGGER.info("✅ MFA code submitted, waiting for dashboard...")
                                    await asyncio.sleep(2.0)
                                else:
                                    _LOGGER.warning("⚠️ Verify button not found, trying Enter key")
                                    await self.page.keyboard.press("Enter")
                            else:
                                _LOGGER.error("❌ MFA input field not found on page")
                                self._log_mfa_error(current_url)
                                return False
                        except Exception as mfa_err:
                            _LOGGER.error(f"❌ MFA code entry failed: {mfa_err}")
                            self._log_mfa_error(current_url)
                            return False
                    else:
                        # MFA required but no code provided - signal caller to use two-phase flow
                        return "MFA_REQUIRED"
            
            # Wait for dashboard to load
            _LOGGER.info("🔄 Waiting for dashboard to load...")
            
            try:
                # Wait for redirect to dashboard
                await self.page.wait_for_url(lambda url: "myaccount.psegliny.com/dashboards" in url, timeout=25000)
                await self.page.wait_for_load_state('networkidle')
                _LOGGER.info("✅ Dashboard loaded")
            except Exception as e:
                # Check if we're still on the login/OAuth page (login failed)
                current_url = self.page.url
                if "id.myaccount.psegliny.com/oauth2" in current_url:
                    page_content = await self.page.content()
                    if any(x in page_content.lower() for x in ["verification", "code", "multi-factor", "authenticate"]):
                        self._log_mfa_error(current_url)
                    else:
                        _LOGGER.error(f"❌ Login failed - still on login page: {current_url}")
                    return False
                else:
                    _LOGGER.error(f"❌ Failed to reach dashboard: {current_url}")
                    return False
            
            # Step 5: Wait for exceptional dashboard to load and manually make redirect request
            _LOGGER.info("⚡ Step 5: Waiting for exceptional dashboard and manually making redirect request...")
            
            # Wait for the exceptional dashboard POST request to complete
            await asyncio.sleep(3.0)  # Give time for the POST request to complete
            
            # Scroll to simulate browsing and wait for content to load
            await self.page.mouse.wheel(0, random.randint(600, 800))
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Add additional wait to ensure page is fully loaded
            try:
                await self.page.wait_for_load_state('domcontentloaded', timeout=10000)
            except Exception as e:
                _LOGGER.warning(f"⚠️ DOM content load wait failed: {e}")
            
            # Check if we captured the exceptional dashboard data
            if not self.exceptional_dashboard_data:
                _LOGGER.warning("⚠️ Exceptional dashboard data not captured, trying direct navigation...")
                await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded')
            else:
                _LOGGER.info("✅ Exceptional dashboard data captured, manually making redirect request...")
                
                # Manually make the redirect request with the captured headers
                try:
                    # Extract the important headers from the exceptional dashboard request
                    headers = self.exceptional_dashboard_data['headers']
                    important_headers = {
                        'accept': headers.get('accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'),
                        'accept-language': headers.get('accept-language', 'en-US,en;q=0.5'),
                        'referer': headers.get('referer', self.exceptional_dashboard),
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'same-origin',
                        'upgrade-insecure-requests': '1'
                    }
                    
                    # Get cookies from context for the request
                    context_cookies = await self.context.cookies()
                    cookie_string = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in context_cookies if cookie['domain'] in ['.psegliny.com', '.myaccount.psegliny.com']])
                    
                    if cookie_string:
                        important_headers['cookie'] = cookie_string
                    
                    _LOGGER.info(f"🔍 Making manual redirect request to {self.mysmartenergy_redirect}")
                    
                    # Make the redirect request manually
                    response = await self.page.request.get(self.mysmartenergy_redirect, headers=important_headers)
                    
                    if response.status == 302:
                        _LOGGER.info("✅ Redirect response received (302)")
                        # Follow the redirect by getting the final URL
                        final_url = response.headers.get('location')
                        if final_url:
                            _LOGGER.info(f"🔄 Following redirect to: {final_url}")
                            try:
                                await self.page.goto(final_url, wait_until='domcontentloaded', timeout=20000)
                            except Exception as nav_error:
                                _LOGGER.warning(f"⚠️ Redirect navigation failed: {nav_error}, trying direct navigation...")
                                await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
                        else:
                            _LOGGER.warning("⚠️ No location header in redirect, trying direct navigation...")
                            await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
                    else:
                        _LOGGER.warning(f"⚠️ Unexpected response status: {response.status}, trying direct navigation...")
                        await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
                        
                except Exception as e:
                    _LOGGER.warning(f"⚠️ Manual redirect failed: {e}, falling back to direct navigation...")
                    await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
            
            # Wait for MySmartEnergy dashboard - use more robust navigation approach
            try:
                # First try to wait for the URL change
                await self.page.wait_for_url(lambda url: "mysmartenergy.psegliny.com/Dashboard" in url, timeout=20000)
            except Exception as e:
                _LOGGER.warning(f"⚠️ URL wait failed: {e}, trying alternative approach...")
                # Fallback: wait for any navigation to complete and check current URL
                await self.page.wait_for_load_state('networkidle', timeout=20000)
                
                # Check if we're on the right page
                current_url = self.page.url
                if "mysmartenergy.psegliny.com/Dashboard" not in current_url:
                    _LOGGER.warning(f"⚠️ Not on expected dashboard, current URL: {current_url}")
                    # Try to navigate directly if we're not on the right page
                    await self.page.goto(self.final_dashboard, wait_until='domcontentloaded', timeout=20000)
            
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            _LOGGER.info("✅ MySmartEnergy Dashboard loaded")
            
            # Step 6: Get cookies from the final dashboard
            _LOGGER.info("🍪 Step 6: Capturing cookies from final dashboard...")
            
            # Wait a moment for any additional requests to complete
            await asyncio.sleep(3.0)
            
            # Get cookies from browser context
            context_cookies = await self.context.cookies()
            for cookie in context_cookies:
                if cookie['domain'] in ['.psegliny.com', '.myaccount.psegliny.com', '.mysmartenergy.psegliny.com']:
                    self.login_cookies[cookie['name']] = cookie['value']
                    _LOGGER.info(f"🍪 Context cookie: {cookie['name']} = {cookie['value'][:50]}...")
            
            _LOGGER.info("✅ Realistic browsing pattern completed successfully")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Error during realistic browsing: {e}")
            return False
    
    async def continue_after_mfa(self, mfa_code: str) -> Optional[str]:
        """
        Continue login flow after MFA challenge. Call when get_cookies() returns 'MFA_REQUIRED'.
        Browser must still be on the MFA challenge page.
        """
        try:
            _LOGGER.info("📝 Entering MFA code...")
            # Wait for code input - check main frame and iframes (Okta may use iframe)
            mfa_input_selectors = [
                'input[name="answer"]',
                'input[name="verificationCode"]',
                'input[type="text"][autocomplete="one-time-code"]',
                'input[type="tel"][inputmode="numeric"]',
                'input[type="tel"]',
                'input[id*="verification"]',
                'input[id*="answer"]',
                'input[data-se="answer"]',
                'input[type="text"]',  # Fallback: any text input
            ]
            mfa_input = None
            mfa_frame = self.page.main_frame  # Frame containing the MFA form
            frames_to_check = [self.page.main_frame]
            try:
                frames_to_check.extend([f for f in self.page.frames if f != self.page.main_frame])
            except Exception:
                pass
            for frame in frames_to_check:
                for sel in mfa_input_selectors:
                    try:
                        mfa_input = await frame.wait_for_selector(sel, state="visible", timeout=2000)
                        if mfa_input:
                            # Skip if it looks like a long text field (not OTP)
                            try:
                                maxlen = await mfa_input.get_attribute("maxlength")
                                if maxlen and int(maxlen) > 20:
                                    mfa_input = None
                                    continue
                            except (TypeError, ValueError):
                                pass
                            mfa_frame = frame
                            _LOGGER.info("Found MFA input with selector: %s", sel)
                            break
                    except Exception:
                        mfa_input = None
                        continue
                if mfa_input:
                    break
            
            # Fallback: try get_by_placeholder (Okta often uses "Enter code" or similar)
            if not mfa_input:
                for placeholder in ["Enter code", "Verification code", "Code", "Enter the code"]:
                    try:
                        loc = self.page.get_by_placeholder(placeholder).first
                        await loc.wait_for(state="visible", timeout=2000)
                        mfa_input = await loc.element_handle()
                        if mfa_input:
                            _LOGGER.info("Found MFA input via placeholder: %s", placeholder)
                            break
                    except Exception:
                        mfa_input = None
                        continue
            
            if not mfa_input:
                _LOGGER.error("❌ MFA input field not found - page may have changed. Current URL: %s", self.page.url)
                try:
                    content = await self.page.content()
                    if len(content) > 500:
                        with open("mfa_fail_debug.html", "w", encoding="utf-8") as f:
                            f.write(content)
                    _LOGGER.error("Page saved to mfa_fail_debug.html for inspection")
                except Exception:
                    pass
                return None
            
            await mfa_input.click()
            await mfa_input.fill(mfa_code)
            
            # Find and click Verify/Submit - Okta uses various button patterns
            verify_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Verify")',
                'button:has-text("Submit")',
                'input[value="Verify"]',
                'input[value="Submit"]',
                'button:has-text("Next")',
                'a:has-text("Verify")',
                'input[data-se="verify"]',
            ]
            verify_btn = None
            for sel in verify_selectors:
                try:
                    verify_btn = await mfa_frame.query_selector(sel)
                    if verify_btn and await verify_btn.is_visible():
                        break
                except Exception:
                    continue
            if verify_btn:
                await verify_btn.click()
            else:
                _LOGGER.info("Verify button not found, pressing Enter")
                await mfa_input.press("Enter")
            
            await asyncio.sleep(2.0)  # Let form submit
            _LOGGER.info("🔄 Waiting for dashboard after MFA...")
            await self.page.wait_for_url(lambda url: "myaccount.psegliny.com/dashboards" in url, timeout=25000)
            await self.page.wait_for_load_state('networkidle')
            _LOGGER.info("✅ Dashboard loaded after MFA")
            
            # Continue from Step 5 (exceptional dashboard)
            await asyncio.sleep(3.0)
            await self.page.mouse.wheel(0, random.randint(600, 800))
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            if not self.exceptional_dashboard_data:
                await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded')
            else:
                try:
                    headers = self.exceptional_dashboard_data['headers']
                    important_headers = {
                        'accept': headers.get('accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                        'accept-language': headers.get('accept-language', 'en-US,en;q=0.5'),
                        'referer': headers.get('referer', self.exceptional_dashboard),
                        'sec-fetch-dest': 'document', 'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'same-origin', 'upgrade-insecure-requests': '1'
                    }
                    context_cookies = await self.context.cookies()
                    cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in context_cookies if c['domain'] in ['.psegliny.com', '.myaccount.psegliny.com']])
                    if cookie_string:
                        important_headers['cookie'] = cookie_string
                    response = await self.page.request.get(self.mysmartenergy_redirect, headers=important_headers)
                    if response.status == 302:
                        final_url = response.headers.get('location')
                        if final_url:
                            await self.page.goto(final_url, wait_until='domcontentloaded', timeout=20000)
                        else:
                            await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
                    else:
                        await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
                except Exception as e:
                    _LOGGER.warning(f"Manual redirect failed: {e}")
                    await self.page.goto(self.mysmartenergy_redirect, wait_until='domcontentloaded', timeout=20000)
            
            await self.page.wait_for_url(lambda url: "mysmartenergy.psegliny.com/Dashboard" in url, timeout=20000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(3.0)
            
            context_cookies = await self.context.cookies()
            for cookie in context_cookies:
                if cookie['domain'] in ['.psegliny.com', '.myaccount.psegliny.com', '.mysmartenergy.psegliny.com']:
                    self.login_cookies[cookie['name']] = cookie['value']
            
            return self.format_cookies_for_api()
        except Exception as e:
            _LOGGER.error("MFA continuation failed: %s (type: %s)", e, type(e).__name__)
            _LOGGER.error("Current URL at failure: %s", self.page.url if self.page else "no page")
            import traceback
            _LOGGER.debug("Traceback: %s", traceback.format_exc())
            return None
    
    def format_cookies_for_api(self) -> str:
        """Format cookies in the format expected by the API."""
        try:
            cookie_strings = []
            if 'MM_SID' in self.login_cookies:
                cookie_strings.append(f"MM_SID={self.login_cookies['MM_SID']}")
            if '__RequestVerificationToken' in self.login_cookies:
                cookie_strings.append(f"__RequestVerificationToken={self.login_cookies['__RequestVerificationToken']}")
            
            if cookie_strings:
                result = "; ".join(cookie_strings)
                _LOGGER.info(f"🍪 Formatted cookies for API: {result[:100]}...")
                return result
            else:
                _LOGGER.warning("⚠️ No valid cookies to format for API")
                return ""
                
        except Exception as e:
            _LOGGER.warning(f"Error formatting cookies for API: {e}")
            return ""
    
    async def get_cookies(self) -> Optional[str]:
        """Get cookies by following the realistic browsing pattern."""
        result = None
        try:
            if not await self.setup_browser():
                _LOGGER.error("❌ Failed to setup browser")
                return None
            
            # Follow the realistic browsing pattern
            result = await self.simulate_realistic_browsing()
            if result is False:
                _LOGGER.error("❌ Realistic browsing pattern failed")
                return None
            if result == "MFA_REQUIRED":
                # Caller should use continue_after_mfa(code) - do NOT cleanup, keep browser alive
                return "MFA_REQUIRED"
            
            # Check if we got the cookies we need
            if self.login_cookies:
                _LOGGER.info("✅ SUCCESS: Got cookies from realistic browsing pattern")
                for name, value in self.login_cookies.items():
                    _LOGGER.info(f"🍪 {name}: {value[:50]}...")
                
                # Format cookies for API use
                return self.format_cookies_for_api()
            else:
                _LOGGER.warning("⚠️ No cookies captured, but browsing completed")
                return ""
                
        except Exception as e:
            _LOGGER.error(f"Error getting cookies: {e}")
            return None
        finally:
            # Don't cleanup when MFA is required - caller needs the browser for continue_after_mfa()
            if result != "MFA_REQUIRED":
                await self.cleanup()
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            _LOGGER.warning(f"Error during cleanup: {e}")

# API Endpoints for Home Assistant integration
async def get_pseg_cookies(email: str, password: str) -> Optional[str]:
    """
    Get PSEG cookies for Home Assistant integration.
    
    Args:
        email: PSEG account email/username
        password: PSEG account password
    
    Returns:
        Cookie string in format "MM_SID=value; __RequestVerificationToken=value" or None if failed
    """
    try:
        _LOGGER.info("🚀 Starting PSEG cookie acquisition for Home Assistant...")
        cookie_getter = PSEGAutoLogin(email=email, password=password)
        return await cookie_getter.get_cookies()
    except Exception as e:
        _LOGGER.error(f"Failed to get PSEG cookies: {e}")
        return None

def get_pseg_cookies_sync(email: str, password: str) -> Optional[str]:
    """
    Synchronous wrapper for get_pseg_cookies.
    
    Args:
        email: PSEG account email/username
        password: PSEG account password
    
    Returns:
        Cookie string in format "MM_SID=value; __RequestVerificationToken=value" or None if failed
    """
    try:
        return asyncio.run(get_pseg_cookies(email, password))
    except Exception as e:
        _LOGGER.error(f"Failed to get PSEG cookies synchronously: {e}")
        return None

# Compatibility wrapper for existing integration
async def get_fresh_cookies(username: str, password: str) -> Optional[str]:
    """
    Compatibility wrapper for existing integration.
    This function maintains the same interface as the old implementation.
    
    Args:
        username: PSEG account email/username
        password: PSEG account password
    
    Returns:
        Cookie string in format "MM_SID=value; __RequestVerificationToken=value" or None if failed
    """
    try:
        _LOGGER.info(f"Login attempt for user: {username}")
        return await get_pseg_cookies(username, password)
    except Exception as e:
        _LOGGER.error(f"Login error: {e}")
        return None

# Test function for standalone usage
async def main():
    """Test function for standalone usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='PSEG Long Island Auto Login - Home Assistant Addon')
    parser.add_argument('--email', required=True, help='PSEG account email/username')
    parser.add_argument('--password', required=True, help='PSEG account password')
    parser.add_argument('--mfa-method', choices=['email', 'sms'], default='sms',
                        help='MFA delivery: email (default) or sms')
    parser.add_argument('--headed', action='store_true',
                        help='Run with visible browser (for debugging)')
    
    args = parser.parse_args()
    
    _LOGGER.info("🚀 Starting PSEG Auto Login - Home Assistant Addon")
    _LOGGER.info(f"📧 Email: {args.email}")
    _LOGGER.info("🔒 Headless mode: %s", not args.headed)
    _LOGGER.info("📱 MFA method: %s", args.mfa_method)
    
    cookie_getter = PSEGAutoLogin(
        email=args.email,
        password=args.password,
        mfa_method=args.mfa_method,
        headless=not args.headed,
    )
    cookies = await cookie_getter.get_cookies()
    
    if cookies == "MFA_REQUIRED":
        _LOGGER.error("❌ MFA required - PSEG sends a verification code to your email or phone.")
        _LOGGER.error("   Check for the code, then run again with the addon API:")
        _LOGGER.error("   POST /login (triggers email) → POST /login/mfa with code")
        return 1
    elif cookies:
        _LOGGER.info("🎉 SUCCESS: Cookies obtained successfully!")
        _LOGGER.info("=" * 80)
        _LOGGER.info("COOKIE STRING (for Home Assistant integration):")
        _LOGGER.info("=" * 80)
        _LOGGER.info(cookies)
        _LOGGER.info("=" * 80)
        _LOGGER.info(f"📋 Total length: {len(cookies)} characters")
        return 0
    else:
        _LOGGER.error("❌ FAILED: Could not obtain cookies")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)