
import streamlit as st
import requests
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


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fairchildes Paw Park",
    page_icon="🐾",
    layout="wide",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0;
        }

        .subtitle {
            font-size: 1.2rem;
            opacity: 0.75;
            margin-top: 0;
        }

        .slot-card {
            padding: 18px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 12px;
            margin-bottom: 14px;
        }

        .date-title {
            font-size: 1.15rem;
            font-weight: 700;
        }

        .times {
            font-size: 1rem;
            margin-top: 8px;
        }

        .price {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 8px;
        }

        .summary-card {
            padding: 18px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 12px;
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "days" not in st.session_state:
    st.session_state.days = []

if "failed_blocks" not in st.session_state:
    st.session_state.failed_blocks = 0

if "scanned" not in st.session_state:
    st.session_state.scanned = False


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🐾 Fairchildes Paw Park</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">Availability Scanner</div>',
    unsafe_allow_html=True,
)

st.write(
    f"Scanning the next **{SCAN_DAYS} days** · "
    f"Timezone: **{TIMEZONE}**"
)

st.divider()


# ============================================================
# SCAN FUNCTION
# ============================================================

def scan_availability(progress_bar, status_text):
    """
    Scan the Appointo availability API in blocks and return
    all days returned by the API.
    """

    all_days = []
    failed_blocks = 0

    total_blocks = (
        SCAN_DAYS + BLOCK_SIZE - 1
    ) // BLOCK_SIZE

    for block_number, i in enumerate(
        range(0, SCAN_DAYS, BLOCK_SIZE),
        start=1,
    ):

        start = datetime.now(
            ZoneInfo(TIMEZONE)
        ) + timedelta(days=i)

        end = datetime.now(
            ZoneInfo(TIMEZONE)
        ) + timedelta(days=i + BLOCK_SIZE)

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
            f"Scanning block **{block_number}/{total_blocks}**  "
            f"({start_date} → {end_date})"
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

            all_days.extend(days)

        except requests.RequestException:
            failed_blocks += 1

        # Small delay to avoid hammering the API
        import time as time_module
        time_module.sleep(0.05)

    return all_days, failed_blocks


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_days(days):
    """
    Remove duplicate dates returned by the API.
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
    Return only slots that are actually available.
    """

    if not isinstance(day, dict):
        return []

    spots = day.get("spots", [])

    return [
        spot
        for spot in spots
        if isinstance(spot, dict)
        and spot.get("status") == "available"
        and spot.get("is_available") is True
    ]


# ============================================================
# FORMAT TIME
# ============================================================

def format_slot_time(start_time):
    """
    Convert API start_time into London time and display it
    as 6:00 AM / 6:30 PM etc.
    """

    if not start_time:
        return None

    try:

        # Handle both ISO strings with and without Z
        dt = datetime.fromisoformat(
            start_time.replace("Z", "+00:00")
        )

        london_time = dt.astimezone(
            ZoneInfo(TIMEZONE)
        )

        return london_time

    except (ValueError, TypeError):
        return None


# ============================================================
# FIND SLOTS AT SPECIFIC TIME
# ============================================================

def find_slots_at_time(unique_days, selected_time):
    """
    Find available slots matching the selected London time.
    """

    matches = []

    target_time = selected_time.strftime("%H:%M")

    for day in unique_days.values():

        slots = get_available_slots(day)

        for slot in slots:

            start_time = slot.get("start_time")

            local_time = format_slot_time(start_time)

            if local_time is None:
                continue

            if local_time.strftime("%H:%M") == target_time:
                matches.append(
                    (local_time, slot)
                )

    # Remove duplicate slots
    seen = set()
    unique_matches = []

    for local_time, slot in matches:

        key = local_time.isoformat()

        if key not in seen:

            seen.add(key)

            unique_matches.append(
                (local_time, slot)
            )

    unique_matches.sort(
        key=lambda x: x[0]
    )

    return unique_matches


# ============================================================
# SCAN BUTTON
# ============================================================

st.subheader("🔍 Availability Scan")

if st.button(
    "Scan Availability",
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

    unique_days = remove_duplicate_days(days)

    st.session_state.days = unique_days
    st.session_state.failed_blocks = failed_blocks
    st.session_state.scanned = True

    progress_bar.progress(1.0)

    status_text.success(
        f"Scan complete. Found {len(unique_days)} dates."
    )


# ============================================================
# RESULTS
# ============================================================

if st.session_state.scanned:

    unique_days = st.session_state.days

    failed_blocks = (
        st.session_state.failed_blocks
    )

    # --------------------------------------------------------
    # CALCULATE SUMMARY
    # --------------------------------------------------------

    available_days = 0
    total_slots = 0

    for date_str in sorted(unique_days):

        day = unique_days[date_str]

        available = get_available_slots(day)

        if available:
            available_days += 1
            total_slots += len(available)

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SPECIFIC TIME SEARCH
    # --------------------------------------------------------

    st.divider()

    st.subheader("🕐 Check a Specific Time")

    time_col, button_col = st.columns(
        [3, 1]
    )

    with time_col:

        selected_time = st.time_input(
            "Choose a time",
            value=time(6, 0),
            step=timedelta(minutes=30),
        )

    with button_col:

        st.write("")

        check_clicked = st.button(
            "🔎 Check Time",
            use_container_width=True,
        )

    if check_clicked:

        matches = find_slots_at_time(
            unique_days,
            selected_time,
        )

        st.session_state.time_matches = matches

    # --------------------------------------------------------
    # TIME SEARCH RESULTS
    # --------------------------------------------------------

    if "time_matches" in st.session_state:

        matches = st.session_state.time_matches

        st.markdown(
            f"### Time Search: "
            f"{selected_time.strftime('%I:%M %p').lstrip('0')}"
        )

        if not matches:

            st.warning(
                "No availability found at this time."
            )

        else:

            st.success(
                f"Found {len(matches)} matching slot(s)."
            )

            for local_time, slot in matches:

                date_text = local_time.strftime(
                    "%A, %d %B %Y"
                )

                time_text = local_time.strftime(
                    "%I:%M %p"
                ).lstrip("0")

                price = slot.get(
                    "price",
                    "N/A",
                )

                try:
                    price_text = (
                        f"£{float(price):.2f}"
                    )
                except (
                    ValueError,
                    TypeError,
                ):
                    price_text = f"£{price}"

                st.markdown(
                    f"""
                    <div class="slot-card">
                        <div class="date-title">
                            📅 {date_text}
                        </div>

                        <div class="times">
                            🕐 <strong>{time_text}</strong>
                        </div>

                        <div class="price">
                            💷 {price_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # --------------------------------------------------------
    # ALL AVAILABLE SLOTS
    # --------------------------------------------------------

    st.divider()

    st.subheader("📅 Available Slots")

    if not available_days:

        st.info(
            f"No available slots found within "
            f"the next {SCAN_DAYS} days."
        )

    else:

        for date_str in sorted(unique_days):

            day = unique_days[date_str]

            available = get_available_slots(day)

            if not available:
                continue

            # Date
            try:
                date_obj = datetime.strptime(
                    date_str,
                    "%Y-%m-%d",
                )

                friendly_date = date_obj.strftime(
                    "%A, %d %B %Y"
                )

            except ValueError:

                friendly_date = date_str

            # Times
            times = []

            for spot in available:

                local_time = format_slot_time(
                    spot.get("start_time")
                )

                if local_time is None:
                    continue

                formatted = local_time.strftime(
                    "%I:%M %p"
                ).lstrip("0")

                times.append(formatted)

            # Remove duplicates while preserving order
            times = list(
                dict.fromkeys(times)
            )

            # Prices
            prices = {
                spot.get("price")
                for spot in available
                if spot.get("price") is not None
            }

            price_text = None

            if prices:

                price = next(iter(prices))

                try:
                    price_text = (
                        f"£{float(price):.2f}"
                    )
                except (
                    ValueError,
                    TypeError,
                ):
                    price_text = f"£{price}"

            # Display card
            st.markdown(
                f"""
                <div class="slot-card">

                    <div class="date-title">
                        📅 {friendly_date}
                    </div>

                    <div class="times">
                        🕐
                        {" • ".join(times)}
                    </div>

                    {
                        f'<div class="price">💷 {price_text}</div>'
                        if price_text
                        else ""
                    }

                    <div style="opacity: 0.65; margin-top: 8px;">
                        {len(available)}
                        {"slot" if len(available) == 1 else "slots"}
                        available
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------
    # BOOKING
    # --------------------------------------------------------

    st.divider()

    st.subheader("🔗 Booking")

    st.link_button(
        "Book at Fairchildes Paw Park",
        BOOKING_URL,
        use_container_width=True,
    )
```
