import streamlit as st
import requests
import time as time_module

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo


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
        del st.session_state["password_input"]  # Clear from memory
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


# ============================================================
# HEADER
# ============================================================

st.title("🐾 Fairchildes Paw Park")

st.subheader("Availability Scanner")

st.write(
    f"Scanning the next **{SCAN_DAYS} days** "
    f"using **{TIMEZONE}** timezone."
)

st.divider()


# ============================================================
# SCAN AVAILABILITY
# ============================================================

def scan_availability(progress_bar, status_text):
    """
    Scan the Appointo availability API in 30-day blocks.
    """

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

        end = now + timedelta(
            days=day_offset + BLOCK_SIZE
        )

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

            st.warning(
                f"Block {block_number} failed: {error}"
            )

        except ValueError:

            failed_blocks += 1

            st.warning(
                f"Block {block_number} returned invalid JSON."
            )

        time_module.sleep(0.05)

    return all_days, failed_blocks


# ============================================================
# REMOVE DUPLICATE DAYS
# ============================================================

def remove_duplicate_days(days):
    """
    Keep one entry per date.
    """

    unique_days = {}

    for day in days:

        if not isinstance(day, dict):
            continue

        date = day.get("date")

        if date:
            unique_days[date] = day

    return unique_days


# ============================================================
# GET AVAILABLE SLOTS
# ============================================================

def get_available_slots(day):
    """
    Return only genuinely available slots.
    """

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


# ============================================================
# CONVERT API TIME TO LONDON TIME
# ============================================================

def format_slot_time(start_time):
    """
    Convert the API's start_time into Europe/London time.
    """

    if not start_time:
        return None

    try:

        dt = datetime.fromisoformat(
            start_time.replace("Z", "+00:00")
        )

        london_time = dt.astimezone(
            ZoneInfo(TIMEZONE)
        )

        return london_time

    except (
        ValueError,
        TypeError,
    ):

        return None


# ============================================================
# FIND SPECIFIC TIME
# ============================================================

def find_slots_at_time(
    unique_days,
    selected_time,
):
    """
    Find all available slots matching the selected
    London time.
    """

    target_time = selected_time.strftime(
        "%H:%M"
    )

    matches = []

    for day in unique_days.values():

        available_slots = get_available_slots(
            day
        )

        for slot in available_slots:

            start_time = slot.get(
                "start_time"
            )

            local_time = format_slot_time(
                start_time
            )

            if local_time is None:
                continue

            if local_time.strftime(
                "%H:%M"
            ) == target_time:

                matches.append(
                    (
                        local_time,
                        slot,
                    )
                )

    # Remove duplicate slots
    seen = set()
    unique_matches = []

    for local_time, slot in matches:

        key = local_time.isoformat()

        if key in seen:
            continue

        seen.add(key)

        unique_matches.append(
            (
                local_time,
                slot,
            )
        )

    unique_matches.sort(
        key=lambda item: item[0]
    )

    return unique_matches


# ============================================================
# FORMAT PRICE
# ============================================================

def format_price(price):
    """
    Format a price as £12.00 where possible.
    """

    if price is None:
        return None

    try:

        return f"£{float(price):.2f}"

    except (
        ValueError,
        TypeError,
    ):

        return f"£{price}"


# ============================================================
# SCAN BUTTON
# ============================================================

st.subheader("🔍 Availability Scan")

if st.button(
    "🔍 Scan Availability",
    type="primary",
    use_container_width=True,
):

    progress_bar = st.progress(0)

    status_text = st.empty()

    with st.spinner(
        f"Scanning the next {SCAN_DAYS} days..."
    ):

        days, failed_blocks = scan_availability(
            progress_bar,
            status_text,
        )

    unique_days = remove_duplicate_days(
        days
    )

    st.session_state.days = unique_days

    st.session_state.failed_blocks = (
        failed_blocks
    )

    st.session_state.scanned = True

    st.session_state.time_matches = None

    progress_bar.progress(1.0)

    status_text.success(
        f"✓ Scan complete. "
        f"Found {len(unique_days)} dates."
    )


# ============================================================
# RESULTS
# ============================================================

if st.session_state.scanned:

    unique_days = st.session_state.days

    failed_blocks = (
        st.session_state.failed_blocks
    )

    # ========================================================
    # CALCULATE SUMMARY
    # ========================================================

    available_days = 0
    total_slots = 0

    for date_str in sorted(
        unique_days
    ):

        day = unique_days[date_str]

        available = get_available_slots(
            day
        )

        if available:

            available_days += 1

            total_slots += len(
                available
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    st.divider()

    st.subheader("📊 Scan Summary")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Days with availability",
            available_days,
        )

    with col2:

        st.metric(
            "Available slots",
            total_slots,
        )

    with col3:

        st.metric(
            "Failed blocks",
            failed_blocks,
        )

    # ========================================================
    # SPECIFIC TIME SEARCH
    # ========================================================

    st.divider()

    st.subheader(
        "🕐 Check a Specific Time"
    )

    time_col, button_col = st.columns(
        [3, 1]
    )

    with time_col:

        selected_time = st.time_input(
            "Choose a time",
            value=time(6, 0),
            step=timedelta(
                minutes=30
            ),
        )

    with button_col:

        st.write("")

        check_clicked = st.button(
            "🔎 Check Time",
            use_container_width=True,
        )

    if check_clicked:

        st.session_state.time_matches = (
            find_slots_at_time(
                unique_days,
                selected_time,
            )
        )

    # ========================================================
    # TIME SEARCH RESULTS
    # ========================================================

    if (
        st.session_state.time_matches
        is not None
    ):

        matches = (
            st.session_state.time_matches
        )

        formatted_search_time = (
            selected_time
            .strftime("%I:%M %p")
            .lstrip("0")
        )

        st.markdown(
            f"### 🔎 Time Search: "
            f"{formatted_search_time}"
        )

        if not matches:

            st.warning(
                f"No availability found at "
                f"{formatted_search_time}."
            )

        else:

            st.success(
                f"Found {len(matches)} "
                f"matching slot(s)."
            )

            for local_time, slot in matches:

                date_text = (
                    local_time
                    .strftime(
                        "%A, %d %B %Y"
                    )
                )

                time_text = (
                    local_time
                    .strftime("%I:%M %p")
                    .lstrip("0")
                )

                price_text = format_price(
                    slot.get("price")
                )

                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"### 📅 {date_text}"
                    )

                    st.write(
                        f"🕐 **{time_text}**"
                    )

                    if price_text:

                        st.write(
                            f"💷 **{price_text}**"
                        )

    # ========================================================
    # ALL AVAILABLE SLOTS
    # ========================================================

    st.divider()

    st.subheader(
        "📅 Available Slots"
    )

    if not available_days:

        st.info(
            f"No available slots found "
            f"within the next {SCAN_DAYS} days."
        )

    else:

        for date_str in sorted(
            unique_days
        ):

            day = unique_days[date_str]

            available = get_available_slots(
                day
            )

            if not available:
                continue

            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            try:

                date_obj = datetime.strptime(
                    date_str,
                    "%Y-%m-%d",
                )

                friendly_date = (
                    date_obj.strftime(
                        "%A, %d %B %Y"
                    )
                )

            except ValueError:

                friendly_date = date_str

            # ------------------------------------------------
            # TIMES
            # ------------------------------------------------

            times = []

            for spot in available:

                local_time = (
                    format_slot_time(
                        spot.get(
                            "start_time"
                        )
                    )
                )

                if local_time is None:
                    continue

                formatted = (
                    local_time
                    .strftime("%I:%M %p")
                    .lstrip("0")
                )

                times.append(
                    formatted
                )

            # Remove duplicate times
            times = list(
                dict.fromkeys(times)
            )

            # ------------------------------------------------
            # PRICES
            # ------------------------------------------------

            prices = {
                spot.get("price")
                for spot in available
                if spot.get("price")
                is not None
            }

            price_text = None

            if prices:

                price = next(
                    iter(prices)
                )

                price_text = format_price(
                    price
                )

            # ------------------------------------------------
            # DISPLAY CARD
            # ------------------------------------------------

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### 📅 {friendly_date}"
                )

                if times:

                    st.write(
                        "🕐 **"
                        + "   •   ".join(times)
                        + "**"
                    )

                if price_text:

                    st.write(
                        f"💷 **{price_text}**"
                    )

                slot_word = (
                    "slot"
                    if len(available) == 1
                    else "slots"
                )

                st.caption(
                    f"{len(available)} "
                    f"{slot_word} available"
                )

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
