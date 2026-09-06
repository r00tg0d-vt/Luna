import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import sys
import re
import time

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
# COMMAND LINE SEARCH
# ============================================================

check_time = None

if len(sys.argv) >= 3 and sys.argv[1].lower() == "!check":

    raw_time = " ".join(sys.argv[2:]).strip().lower()

    # Accept:
    # 6am
    # 6 am
    # 6:00am
    # 6:00 am
    # 06:00
    match = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        raw_time
    )

    if not match:
        print()
        print("❌ Invalid time.")
        print()
        print("Examples:")
        print("   python dogg.py !check 6am")
        print("   python dogg.py !check 6:30pm")
        print("   python dogg.py !check 14:00")
        print()
        sys.exit(1)

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)

    if meridiem:

        if hour < 1 or hour > 12 or minute > 59:
            print("❌ Invalid time.")
            sys.exit(1)

        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12

    else:

        if hour > 23 or minute > 59:
            print("❌ Invalid time.")
            sys.exit(1)

    check_time = f"{hour:02d}:{minute:02d}"

# ============================================================
# TERMINAL STYLING
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"
MAGENTA = "\033[95m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def line(char="─", length=68):
    return char * length


def box_top():
    print(f"{GRAY}╭{line('─')}╮{RESET}")


def box_bottom():
    print(f"{GRAY}╰{line('─')}╯{RESET}")


def box_line(text=""):
    print(f"{GRAY}│{RESET} {text}")


# ============================================================
# HEADER
# ============================================================

clear_screen()

print()
box_top()

box_line(
    f"{GREEN}{BOLD}🐾  FAIRCHILDES PAW PARK{RESET}"
)

box_line(
    f"{CYAN}{BOLD}    AVAILABILITY SCANNER{RESET}"
)

box_line()

box_line(
    f"{DIM}    Scanning the next {SCAN_DAYS} days{RESET}"
)

box_line(
    f"{DIM}    Location: Europe/London{RESET}"
)

box_bottom()

print()


# ============================================================
# SCAN
# ============================================================

all_days = []
failed_blocks = 0

total_blocks = (SCAN_DAYS + BLOCK_SIZE - 1) // BLOCK_SIZE

print(f"{GRAY}{line()}{RESET}")
print(
    f"{BOLD}{WHITE}  SCANNING AVAILABILITY{RESET}"
)
print(f"{GRAY}{line()}{RESET}")
print()

for block_number, i in enumerate(
    range(0, SCAN_DAYS, BLOCK_SIZE), start=1
):

    start = datetime.now() + timedelta(days=i)
    end = datetime.now() + timedelta(days=i + BLOCK_SIZE)

    start_date = start.strftime("%Y-%m-%d")
    end_date = end.strftime("%Y-%m-%d")

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "shop": SHOP,
        "duration_uuid": UUID,
        "timezone": TIMEZONE,
    }

    # Progress bar
    bar_width = 28
    progress = block_number / total_blocks
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)

    print(
        f"  {CYAN}[{bar}]{RESET} "
        f"{block_number}/{total_blocks}  "
        f"{GRAY}{start_date} → {end_date}{RESET}",
        end="\r",
        flush=True
    )

    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        days = data.get(
            "calendly_events", {}
        ).get("days", [])

        all_days.extend(days)

    except requests.RequestException as e:
        failed_blocks += 1

        print(
            f"\n  {RED}✕ Block {block_number} failed:"
            f" {e}{RESET}"
        )

    time.sleep(0.05)


print("\n")
print(f"{GREEN}✓ Scan complete{RESET}")
print()


# ============================================================
# REMOVE DUPLICATES
# ============================================================

unique_days = {}

for day in all_days:
    date = day.get("date")

    if date:
        unique_days[date] = day

# ============================================================
# TIME SEARCH
# ============================================================
if len(sys.argv) >= 3 and sys.argv[1].lower() == "!check":

    raw_time = " ".join(sys.argv[2:]).strip().lower()

    # Accept: 6am, 6 am, 6:00am, 6:00 am, 06:00
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", raw_time)

    if not match:
        print("\nInvalid time format. Example: python .\\dogg.py !check 6am")
        sys.exit(1)

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3)

    if ampm:
        if hour < 1 or hour > 12:
            print("\nInvalid hour.")
            sys.exit(1)

        if ampm == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12

    if hour > 23 or minute > 59:
        print("\nInvalid time.")
        sys.exit(1)

    check_time = f"{hour:02d}:{minute:02d}"

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║  TIME SEARCH: {raw_time.upper():<42}║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    matches = []

    # Search the actual slot dictionaries collected from the API
    for day in unique_days.values():

        # Handle the structure used by the scanner
        if isinstance(day, dict):
            slots = day.get("spots", [])
        elif isinstance(day, list):
            slots = day
        else:
            continue

        for slot in slots:

            if not isinstance(slot, dict):
                continue

            if slot.get("status") != "available":
                continue

            if slot.get("is_available") is not True:
                continue

            start_time = slot.get("start_time")

            if not start_time:
                continue

            dt = datetime.fromisoformat(
                start_time.replace("Z", "+00:00")
            )

            local_time = dt.astimezone(ZoneInfo(TIMEZONE))

            if local_time.strftime("%H:%M") == check_time:
                matches.append((local_time, slot))

    if not matches:
        print(f"  No availability found at {raw_time.upper()}.")
    else:
        # Remove duplicate slots
        seen = set()
        unique_matches = []

        for local_time, slot in matches:
            key = local_time.isoformat()

            if key not in seen:
                seen.add(key)
                unique_matches.append((local_time, slot))

        print(f"  Found {len(unique_matches)} matching slot(s):\n")

        for local_time, slot in unique_matches:
            price = slot.get("price", "N/A")

            print(
                f"  {local_time.strftime('%A %d %B %Y'):<25}"
                f"{local_time.strftime('%I:%M %p').lstrip('0'):<10}"
                f"£{price}"
            )

    print()
    sys.exit(0)
# ============================================================
# DISPLAY RESULTS
# ============================================================

available_days = 0
total_slots = 0

print(f"{GRAY}{line()}{RESET}")
print(
    f"{BOLD}{WHITE}  AVAILABLE SLOTS{RESET}"
)
print(f"{GRAY}{line()}{RESET}")
print()

for date_str in sorted(unique_days):

    day = unique_days[date_str]

    if (
        day.get("status") == "unavailable"
        and day.get("day_available") is False
    ):
        continue

    spots = day.get("spots", [])

    available = [
        spot
        for spot in spots
        if spot.get("status") == "available"
        and spot.get("is_available") is True
    ]

    if not available:
        continue

    available_days += 1
    total_slots += len(available)

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_obj = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    )

    friendly_date = date_obj.strftime(
        "%A, %d %B %Y"
    )

    print(
        f"{CYAN}{BOLD}📅  {friendly_date}{RESET}"
    )

    # --------------------------------------------------------
    # TIME CONVERSION
    # --------------------------------------------------------

    times = []

    for spot in available:

        start_time = spot.get("start_time")

        if not start_time:
            continue

        try:
            dt = datetime.fromisoformat(start_time)

            london_time = dt.astimezone(
                ZoneInfo(TIMEZONE)
            )

            formatted = london_time.strftime(
                "%I:%M %p"
            ).lstrip("0")

            times.append(formatted)

        except (ValueError, TypeError):
            continue

    # Remove duplicates while preserving order
    times = list(dict.fromkeys(times))

    # --------------------------------------------------------
    # TIME DISPLAY
    # --------------------------------------------------------

    if times:

        print(
            f"    {WHITE}🕐  "
            f"{'   •   '.join(times)}{RESET}"
        )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    prices = {
        spot.get("price")
        for spot in available
        if spot.get("price") is not None
    }

    if prices:

        price = next(iter(prices))

        try:
            price = f"£{float(price):.2f}"
        except (ValueError, TypeError):
            price = f"£{price}"

        print(
            f"    {GREEN}💷  {price}{RESET}"
        )

    # --------------------------------------------------------
    # SLOT COUNT
    # --------------------------------------------------------

    print(
        f"    {DIM}{len(available)} "
        f"{'slot' if len(available) == 1 else 'slots'} available{RESET}"
    )

    print()


# ============================================================
# SUMMARY
# ============================================================

print(f"{GRAY}{line()}{RESET}")
print(
    f"{BOLD}{WHITE}  SCAN SUMMARY{RESET}"
)
print(f"{GRAY}{line()}{RESET}")
print()

if available_days:

    print(
        f"  {GREEN}●{RESET} "
        f"{BOLD}{available_days}{RESET} "
        f"{'day' if available_days == 1 else 'days'} "
        f"with availability"
    )

    print(
        f"  {GREEN}●{RESET} "
        f"{BOLD}{total_slots}{RESET} "
        f"total available slots"
    )

else:

    print(
        f"  {YELLOW}●  No available slots found "
        f"within the scan period.{RESET}"
    )

if failed_blocks:

    print(
        f"  {YELLOW}⚠  {failed_blocks} scan "
        f"{'block' if failed_blocks == 1 else 'blocks'} "
        f"failed.{RESET}"
    )

print()

if available_days:

    print(f"  {GREEN}{BOLD}🔗 BOOKING{RESET}")
    print(f"  {CYAN}{BOOKING_URL}{RESET}")

print()
box_bottom()
print()