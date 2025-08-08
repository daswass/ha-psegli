#!/usr/bin/env python3
"""Automated login for PSEG Long Island using Playwright."""

import asyncio
import logging
from typing import Dict, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class PSEGAutoLogin:
    """Automated login for PSEG Long Island using Playwright."""

    def __init__(self, username: str, password: str):
        """Initialize automated login."""
        self.username = username
        self.password = password
        self.browser = None
        self.page = None

    async def setup_browser(self):
        """Set up the Playwright browser."""
        try:
            logger.info("Setting up Playwright browser for automated login...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            self.page = await self.browser.new_page()
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
            })
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            logger.info("Playwright browser initialized successfully")
            return True
        except Exception as e:
            logger.error("Failed to initialize Playwright browser: %s", e)
            return False

    async def get_fresh_cookies(self) -> Optional[Dict[str, str]]:
        """Get fresh cookies using automated login."""
        try:
            logger.info("Starting automated login to get fresh cookies...")
            if not await self.setup_browser():
                return None
                
            await self.page.goto("https://mysmartenergy.psegliny.com/")
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)  # Wait for reCAPTCHA to load
            
            await self.page.fill('input[name="LoginEmail"]', self.username)
            await self.page.fill('input[name="LoginPassword"]', self.password)
            
            try:
                remember_me = self.page.locator('input[name="RememberMe"]')
                if not await remember_me.is_checked():
                    await remember_me.check()
            except:
                pass
                
            logger.info("Simulating real mouse click on login button...")
            login_button = self.page.locator('button.loginBtn')
            await login_button.hover()
            await asyncio.sleep(0.5)
            await login_button.click(force=True)
            
            logger.info("Waiting for reCAPTCHA to be triggered...")
            await asyncio.sleep(3)
            
            logger.info("Waiting for login to complete...")
            for i in range(30):
                current_url = self.page.url
                if "login" not in current_url.lower() and "mysmartenergy.psegliny.com" in current_url:
                    logger.info("🎉 SUCCESS! Login appears to be successful!")
                    cookies = {}
                    for cookie in await self.page.context.cookies():
                        cookies[cookie['name']] = cookie['value']
                    logger.info("Cookies captured: %s", list(cookies.keys()))
                    return cookies
                await asyncio.sleep(1)
                
            logger.warning("Login did not complete after 30 seconds")
            return None
            
        except Exception as e:
            logger.error("Automated login failed: %s", e)
            return None
        finally:
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
            if hasattr(self, 'playwright'):
                try:
                    await self.playwright.stop()
                except:
                    pass

async def get_fresh_cookies(username: str, password: str) -> Optional[Dict[str, str]]:
    """Get fresh cookies using automated login."""
    auto_login = PSEGAutoLogin(username, password)
    return await auto_login.get_fresh_cookies()
