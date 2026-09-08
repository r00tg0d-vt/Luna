import streamlit as st
import requests
import time as time_module

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# CONFIG
# ============================================================

SHOP = "pawesome-adventures.myshopify.com"
UUID = "40178447122621"
TIMEZONE = "Europe/London"

BOOKING_URL = "https://fairchildes-pawpark.co.uk/products/55-minutes"
API_URL = "https://app.appointo.me/scripttag/calendar_availability"

HEADERS = {
    "Origin": "https://fairchildes-pawpark.co.uk",
    "Referer": "https://fairchildes-pawpark.co.uk/",
}

SCAN_DAYS = 180
BLOCK_SIZE = 30
APP_PASSWORD = "r00t"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fairchildes Paw Park",
    page_icon="🐾",
    layout="wide",
)


# ============================================================
# AUTHENTICATION GATE
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.get("password_input") == APP_PASSWORD:
        st.session_state.authenticated = True
        del st.session_state["password_input"]
    else:
        st.error("Incorrect password")

if not st.session_state.authenticated:
    st.title("🐾 Fairchildes Paw Park")
    st.text_input(
        "Enter Password to Access",
        type="password",
        on_change=check_password,
        key="password_input",
    )
    st.stop()


# ============================================================
# SELENIUM AUTOMATION ENGINE
# ============================================================

def run_selenium_booking(target_date_iso, target_time_text, customer_info):
    """
    Automates slot selection on the Appointo widget and navigates to Shopify checkout.
    - target_date_iso: "YYYY-MM-DD"
    - target_time_text: e.g. "6:00 AM" or "06:00"
    - customer_info: dict with email, first_name, last_name, phone
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    wait = WebDriverWait(driver, 20)

    try:
        # 1. Open the booking page
        driver.get(BOOKING_URL)

        # 2. Locate Appointo iframe if present, or wait for widget container
        time_module.sleep(3)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            src = frame.get_attribute("src") or ""
            if "appointo" in src:
                driver.switch_to.frame(frame)
                break

        # 3. Locate and select the date button matching the target day
        date_obj = datetime.strptime(target_date_iso, "%Y-%m-%d")
        day_str = str(date_obj.day)

        date_xpath = (
            f"//*[contains(@data-date, '{target_date_iso}') or "
            f"contains(@aria-label, '{target_date_iso}') or "
            f"(self::button and normalize-space()='{day_str}')]"
        )
        date_elem = wait.until(EC.element_to_be_clickable((By.XPATH, date_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", date_elem)
        date_elem.click()

        # 4. Locate and select the target time slot
        clean_time = target_time_text.strip().lstrip("0")
        time_xpath = f"//*[contains(text(), '{clean_time}') or contains(text(), '{target_time_text}')]"
        time_elem = wait.until(EC.element_to_be_clickable((By.XPATH, time_xpath)))
        driver.execute_script("arguments[0].scrollIntoView(true);", time_elem)
        time_elem.click()

        # 5. Click the Book Now / Add to Cart button
        driver.switch_to.default_content()
        book_btn_xpath = (
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book now') or "
            "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'add to cart') or "
            "contains(@class, 'appointo-btn')]"
        )
        book_btn = wait.until(EC.element_to_be_clickable((By.XPATH, book_btn_xpath)))
        book_btn.click()

        # 6. Wait for redirect into Shopify checkout
        wait.until(EC.url_contains("/checkouts/"))
        checkout_url = driver.current_url

        # 7. Prefill email if available on Shopify checkout
        try:
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_field.send_keys(customer_info.get("email", ""))
        except Exception:
            pass  # Some Shopify themes use alternative forms or skip directly to contact step

        return True, checkout_url

    except Exception as exc:
        return False, str(exc)

    finally:
        driver.quit()


# ============================================================
# SESSION STATE
# ============================================================

if "days" not in st.session_state:
    st.session_state.days = {}

if "failed_blocks" not in st.session_state:
    st.session_state.failed_blocks = 0

if "scanned" not in st.session_state:
    st.session_state.scanned = False

if "time_matches" not in st.session_state:
    st.session_state.time_matches = None

if "checkout_url" not in st.session_state:
    st.session_state.checkout_url = None


# ============================================================
# SIDEBAR - AUTO-CHECKOUT SETTINGS
# ============================================================

with st.sidebar:
    st.header("⚙️ Auto-Checkout Details")
    st.caption("Prefilled into Shopify when automating bookings.")
    user_email = st.text_input("Email", value="user@example.com")
    user_first = st.text_input("First Name", value="Alex")
    user_last = st.text_input("Last Name", value="Smith")
    user_phone = st.text_input("Phone", value="07123456789")

    customer_info = {
        "email": user_email,
        "first_name": user_first,
        "last_name": user_last,
        "phone": user_phone,
    }


# ============================================================
# HEADER
# ============================================================

st.title("🐾 Fairchildes Paw Park")
st.subheader("Availability Scanner & Quick Booker")

st.write(
    f"Scanning the next **{SCAN_DAYS} days** "
    f"using **{TIMEZONE}** timezone."
)

st.divider()


# ============================================================
# SCAN AVAILABILITY
# ============================================================

def scan_availability(progress_bar, status_text):
    all_days = []
    failed_blocks = 0

    total_blocks = (
        SCAN_DAYS + BLOCK_SIZE - 1
    ) // BLOCK_SIZE

    london_tz = ZoneInfo(TIMEZONE)

    for block_number, day_offset in enumerate(
        range(0, SCAN_DAYS, BLOCK_SIZE),
        start=1,
    ):
        now = datetime.now(london_tz)
        start = now + timedelta(days=day_offset)
        end = now + timedelta(days=day_offset + BLOCK_SIZE)

        start_date = start.strftime("%Y-%m-%d")
        end_date = end.strftime("%Y-%m-%d")

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "shop": SHOP,
            "duration_uuid": UUID,
            "timezone": TIMEZONE,
        }

        progress = block_number / total_blocks
        progress_bar.progress(progress)
        status_text.write(
            f"Scanning block **{block_number}/{total_blocks}** "
            f"· {start_date} → {end_date}"
        )

        try:
            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            days = (
                data
                .get("calendly_events", {})
                .get("days", [])
            )
            if isinstance(days, list):
                all_days.extend(days)
        except requests.RequestException as error:
            failed_blocks += 1
            st.warning(f"Block {block_number} failed: {error}")
        except ValueError:
            failed_blocks += 1
            st.warning(f"Block {block_number} returned invalid JSON.")

        time_module.sleep(0.05)

    return all_days, failed_blocks


# ============================================================
# UTILITIES
# ============================================================

def remove_duplicate_days(days):
    unique_days = {}
    for day in days:
        if not isinstance(day, dict):
            continue
        date = day.get("date")
        if date:
            unique_days[date] = day
    return unique_days

def get_available_slots(day):
    if not isinstance(day, dict):
        return []
    spots = day.get("spots", [])
    if not isinstance(spots, list):
        return []

    available = []
    for spot in spots:
        if not isinstance(spot, dict):
            continue
        if spot.get("status") != "available":
            continue
        if spot.get("is_available") is not True:
            continue
        available.append(spot)
    return available

def format_slot_time(start_time):
    if not start_time:
        return None
    try:
        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo(TIMEZONE))
    except (ValueError, TypeError):
        return None

def find_slots_at_time(unique_days, selected_time):
    target_time = selected_time.strftime("%H:%M")
    matches = []

    for day in unique_days.values():
        available_slots = get_available_slots(day)
        for slot in available_slots:
            start_time = slot.get("start_time")
            local_time = format_slot_time(start_time)
            if local_time is None:
                continue
            if local_time.strftime("%H:%M") == target_time:
                matches.append((local_time, slot))

    seen = set()
    unique_matches = []
    for local_time, slot in matches:
        key = local_time.isoformat()
        if key in seen:
            continue
        seen.add(key)
        unique_matches.append((local_time, slot))

    unique_matches.sort(key=lambda item: item[0])
    return unique_matches

def format_price(price):
    if price is None:
        return None
    try:
        return f"£{float(price):.2f}"
    except (ValueError, TypeError):
        return f"£{price}"


# ============================================================
# SCAN BUTTON
# ============================================================

st.subheader("🔍 Availability Scan")

if st.button("🔍 Scan Availability", type="primary", use_container_width=True):
    progress_bar = st.progress(0)
    status_text = st.empty()

    with st.spinner(f"Scanning the next {SCAN_DAYS} days..."):
        days, failed_blocks = scan_availability(progress_bar, status_text)

    unique_days = remove_duplicate_days(days)
    st.session_state.days = unique_days
    st.session_state.failed_blocks = failed_blocks
    st.session_state.scanned = True
    st.session_state.time_matches = None

    progress_bar.progress(1.0)
    status_text.success(f"✓ Scan complete. Found {len(unique_days)} dates.")


# ============================================================
# RESULTS & AUTOMATED ACTIONS
# ============================================================

if st.session_state.scanned:
    unique_days = st.session_state.days
    failed_blocks = st.session_state.failed_blocks

    available_days = 0
    total_slots = 0

    for date_str in sorted(unique_days):
        day = unique_days[date_str]
        available = get_available_slots(day)
        if available:
            available_days += 1
            total_slots += len(available)

    st.divider()
    st.subheader("📊 Scan Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Days with availability", available_days)
    with col2:
        st.metric("Available slots", total_slots)
    with col3:
        st.metric("Failed blocks", failed_blocks)

    # Active checkout link banner if one was generated
    if st.session_state.checkout_url:
        st.success("🎉 Slot reserved in checkout!")
        st.link_button(
            "👉 Complete Payment on Shopify",
            st.session_state.checkout_url,
            type="primary",
            use_container_width=True,
        )

    # ========================================================
    # SPECIFIC TIME SEARCH
    # ========================================================

    st.divider()
    st.subheader("🕐 Check a Specific Time")

    time_col, button_col = st.columns([3, 1])
    with time_col:
        selected_time = st.time_input(
            "Choose a time",
            value=time(6, 0),
            step=timedelta(minutes=30),
        )
    with button_col:
        st.write("")
        check_clicked = st.button("🔎 Check Time", use_container_width=True)

    if check_clicked:
        st.session_state.time_matches = find_slots_at_time(unique_days, selected_time)

    if st.session_state.time_matches is not None:
        matches = st.session_state.time_matches
        formatted_search_time = selected_time.strftime("%I:%M %p").lstrip("0")

        st.markdown(f"### 🔎 Time Search: {formatted_search_time}")

        if not matches:
            st.warning(f"No availability found at {formatted_search_time}.")
        else:
            st.success(f"Found {len(matches)} matching slot(s).")
            for idx, (local_time, slot) in enumerate(matches):
                date_iso = local_time.strftime("%Y-%m-%d")
                date_text = local_time.strftime("%A, %d %B %Y")
                time_text = local_time.strftime("%I:%M %p").lstrip("0")
                price_text = format_price(slot.get("price"))

                with st.container(border=True):
                    card_left, card_right = st.columns([3, 1])
                    with card_left:
                        st.markdown(f"### 📅 {date_text}")
                        st.write(f"🕐 **{time_text}**")
                        if price_text:
                            st.write(f"💷 **{price_text}**")
                    with card_right:
                        st.write("")
                        if st.button(f"⚡ Instant Book", key=f"quick_match_{idx}_{date_iso}"):
                            with st.spinner("Automating booking via Selenium..."):
                                success, result = run_selenium_booking(
                                    date_iso, time_text, customer_info
                                )
                                if success:
                                    st.session_state.checkout_url = result
                                    st.rerun()
                                else:
                                    st.error(f"Booking error: {result}")

    # ========================================================
    # ALL AVAILABLE SLOTS
    # ========================================================

    st.divider()
    st.subheader("📅 Available Slots")

    if not available_days:
        st.info(f"No available slots found within the next {SCAN_DAYS} days.")
    else:
        for date_str in sorted(unique_days):
            day = unique_days[date_str]
            available = get_available_slots(day)
            if not available:
                continue

            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                friendly_date = date_obj.strftime("%A, %d %B %Y")
            except ValueError:
                friendly_date = date_str

            times = []
            for spot in available:
                local_time = format_slot_time(spot.get("start_time"))
                if local_time is None:
                    continue
                times.append(local_time.strftime("%I:%M %p").lstrip("0"))

            times = list(dict.fromkeys(times))
            prices = {spot.get("price") for spot in available if spot.get("price") is not None}
            price_text = format_price(next(iter(prices))) if prices else None

            with st.container(border=True):
                slot_left, slot_right = st.columns([3, 1])
                with slot_left:
                    st.markdown(f"### 📅 {friendly_date}")
                    if times:
                        st.write("🕐 **" + "   •   ".join(times) + "**")
                    if price_text:
                        st.write(f"💷 **{price_text}**")
                    slot_word = "slot" if len(available) == 1 else "slots"
                    st.caption(f"{len(available)} {slot_word} available")

                with slot_right:
                    st.write("")
                    first_time = times[0] if times else "06:00"
                    if st.button(f"⚡ Book {first_time}", key=f"book_all_{date_str}"):
                        with st.spinner("Automating booking via Selenium..."):
                            success, result = run_selenium_booking(
                                date_str, first_time, customer_info
                            )
                            if success:
                                st.session_state.checkout_url = result
                                st.rerun()
                            else:
                                st.error(f"Booking error: {result}")

    # ========================================================
    # BOOKING
    # ========================================================

    st.divider()
    st.subheader("🔗 Booking")
    st.link_button(
        "🐾 Book at Fairchildes Paw Park",
        BOOKING_URL,
        use_container_width=True,
    )
