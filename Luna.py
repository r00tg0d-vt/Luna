import subprocess
import streamlit as st
import requests
import time as time_module

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright


# Ensure Playwright browser binary exists in the container
def ensure_playwright_installed():
    try:
        with sync_playwright() as p:
            p.chromium.launch(headless=True)
    except Exception:
        subprocess.run(["playwright", "install", "chromium"], check=True)


# ============================================================
# PLAYWRIGHT AUTOMATION ENGINE
# ============================================================

def run_browser_booking(target_date_iso, target_time_text, customer_info):
    """
    Automates slot selection using Playwright and captures the Shopify checkout URL.
    - target_date_iso: 'YYYY-MM-DD'
    - target_time_text: e.g. '6:00 AM' or '06:00'
    - customer_info: dict with email, first_name, last_name, phone
    """
    ensure_playwright_installed()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        try:
            # 1. Open the booking page
            page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # 2. Check for Appointo frame or main document
            appointo_frame = None
            for frame in page.frames:
                if "appointo" in frame.url:
                    appointo_frame = frame
                    break
            target_scope = appointo_frame if appointo_frame else page

            # 3. Click the target date
            date_obj = datetime.strptime(target_date_iso, "%Y-%m-%d")
            day_str = str(date_obj.day)

            date_selector = (
                f"[data-date='{target_date_iso}'], "
                f"[aria-label*='{target_date_iso}'], "
                f"button:has-text('{day_str}')"
            )
            target_scope.wait_for_selector(date_selector, timeout=15000)
            target_scope.locator(date_selector).first.click()

            # 4. Click the target time slot
            clean_time = target_time_text.strip().lstrip("0")
            time_selector = f"text={clean_time}"
            target_scope.wait_for_selector(time_selector, timeout=10000)
            target_scope.locator(time_selector).first.click()

            # 5. Click Book Now / Add to Cart
            btn_selector = (
                "button:has-text('Book Now'), "
                "button:has-text('Add to Cart'), "
                ".appointo-btn"
            )
            page.wait_for_selector(btn_selector, timeout=10000)
            page.locator(btn_selector).first.click()

            # 6. Wait for navigation into Shopify checkout
            page.wait_for_url("**/checkouts/**", timeout=20000)
            checkout_url = page.url

            # 7. Prefill email if the input appears
            try:
                page.wait_for_selector("input[name='email']", timeout=5000)
                page.fill("input[name='email']", customer_info.get("email", ""))
            except Exception:
                pass

            browser.close()
            return True, checkout_url

        except Exception as exc:
            browser.close()
            return False, str(exc)
