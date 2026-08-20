import os
import time
import requests

from datetime import datetime, timedelta
from statistics import median


# ============================================================
# SETTINGS
# ============================================================

# API key comes from:
# GitHub -> Settings -> Secrets and variables -> Actions
#
# Secret name must be:
# ALPHA_VANTAGE_API_KEY

API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")

# Wait between API calls to reduce rate-limit problems
WAIT_BETWEEN_REQUESTS = 15


# ============================================================
# MOVE WEEKEND ESTIMATES TO MONDAY
# ============================================================

def next_weekday(date):

    # Saturday -> Monday
    if date.weekday() == 5:
        return date + timedelta(days=2)

    # Sunday -> Monday
    if date.weekday() == 6:
        return date + timedelta(days=1)

    return date


# ============================================================
# DETECT DIVIDEND FREQUENCY
# ============================================================

def detect_frequency(dividends):

    if len(dividends) < 2:
        return "Unknown", None

    # Use up to the most recent 8 dividends
    recent = dividends[-8:]

    intervals = []

    for i in range(1, len(recent)):

        days = (
            recent[i]["ex_date"]
            - recent[i - 1]["ex_date"]
        ).days

        if days > 0:
            intervals.append(days)

    if not intervals:
        return "Unknown", None

    # Median is less affected by unusual distributions
    typical_days = round(median(intervals))

    if 5 <= typical_days <= 9:
        frequency = "Weekly"

    elif 20 <= typical_days <= 40:
        frequency = "Monthly"

    elif 70 <= typical_days <= 110:
        frequency = "Quarterly"

    elif 150 <= typical_days <= 210:
        frequency = "Semi-Annual"

    elif 300 <= typical_days <= 430:
        frequency = "Yearly"

    else:
        frequency = "Irregular"

    return frequency, typical_days


# ============================================================
# DISPLAY API ERROR
# ============================================================

def show_api_error(ticker, data):

    print()
    print("=" * 65)
    print(f"TICKER: {ticker}")
    print("=" * 65)

    print("ALPHA VANTAGE DID NOT RETURN DIVIDEND DATA.")
    print()

    if "Information" in data:
        print("API MESSAGE:")
        print(data["Information"])

    elif "Note" in data:
        print("API MESSAGE:")
        print(data["Note"])

    elif "Error Message" in data:
        print("API ERROR:")
        print(data["Error Message"])

    else:
        print("RAW API RESPONSE:")
        print(data)

    print("=" * 65)


# ============================================================
# GET DIVIDEND INFORMATION
# ============================================================

def get_dividend(ticker):

    ticker = ticker.strip().upper()

    print()
    print()
    print("=" * 65)
    print(f"TICKER: {ticker}")
    print("=" * 65)

    # --------------------------------------------------------
    # CHECK API KEY
    # --------------------------------------------------------

    if not API_KEY:

        print("ERROR: Alpha Vantage API key was not found.")
        print()
        print(
            "Add ALPHA_VANTAGE_API_KEY to "
            "GitHub Actions repository secrets."
        )

        return

    # --------------------------------------------------------
    # API REQUEST
    # --------------------------------------------------------

    url = "https://www.alphavantage.co/query"

    params = {
        "function": "DIVIDENDS",
        "symbol": ticker,
        "apikey": API_KEY
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.RequestException as e:

        print("CONNECTION ERROR:")
        print(e)

        return

    except ValueError:

        print("ERROR:")
        print("Alpha Vantage returned invalid JSON.")

        return

    # --------------------------------------------------------
    # CHECK RESPONSE
    # --------------------------------------------------------

    if "data" not in data:

        show_api_error(
            ticker,
            data
        )

        return

    # --------------------------------------------------------
    # PROCESS DATA
    # --------------------------------------------------------

    today = datetime.today().date()

    dividends = []

    for d in data["data"]:

        ex_date = d.get("ex_dividend_date")

        if not ex_date:
            continue

        try:

            ex_date = datetime.strptime(
                ex_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            continue

        dividends.append({

            "ex_date":
                ex_date,

            "payment_date":
                d.get("payment_date"),

            "record_date":
                d.get("record_date"),

            "declaration_date":
                d.get("declaration_date"),

            "amount":
                d.get("amount")
        })

    # Sort oldest -> newest
    dividends.sort(
        key=lambda x: x["ex_date"]
    )

    if not dividends:

        print(
            f"No dividend history was found for {ticker}."
        )

        return

    # --------------------------------------------------------
    # DETECT FREQUENCY
    # --------------------------------------------------------

    frequency, typical_days = detect_frequency(
        dividends
    )

    print()
    print(f"DIVIDEND FREQUENCY: {frequency}")

    if typical_days is not None:

        print(
            f"TYPICAL INTERVAL:   ~{typical_days} days"
        )

    # --------------------------------------------------------
    # SPLIT DATES
    # --------------------------------------------------------

    past = [
        d for d in dividends
        if d["ex_date"] < today
    ]

    today_dividends = [
        d for d in dividends
        if d["ex_date"] == today
    ]

    future = [
        d for d in dividends
        if d["ex_date"] > today
    ]

    # --------------------------------------------------------
    # EX-DIVIDEND TODAY
    # --------------------------------------------------------

    if today_dividends:

        dividend_today = today_dividends[0]

        print()
        print("*********************************")
        print("       EX-DIVIDEND TODAY")
        print("*********************************")

        print(
            "Ex-dividend date:",
            dividend_today["ex_date"]
        )

        print(
            "Record date:     ",
            dividend_today["record_date"]
        )

        print(
            "Payment date:    ",
            dividend_today["payment_date"]
        )

        print(
            "Amount:           $",
            dividend_today["amount"]
        )

        print(
            "Status:           TODAY"
        )

    # --------------------------------------------------------
    # LAST KNOWN DIVIDEND
    # --------------------------------------------------------

    elif past:

        latest = past[-1]

        print()
        print("---------------------------------")
        print("LAST KNOWN DIVIDEND")
        print("---------------------------------")

        print(
            "Ex-dividend date:",
            latest["ex_date"]
        )

        print(
            "Payment date:    ",
            latest["payment_date"]
        )

        print(
            "Amount:           $",
            latest["amount"]
        )

    # --------------------------------------------------------
    # NEXT OFFICIAL DIVIDEND
    # --------------------------------------------------------

    if future:

        next_dividend = future[0]

        days_until = (
            next_dividend["ex_date"]
            - today
        ).days

        print()
        print("---------------------------------")
        print("NEXT OFFICIAL DIVIDEND")
        print("---------------------------------")

        print(
            "Ex-dividend date:",
            next_dividend["ex_date"]
        )

        print(
            "Declaration date:",
            next_dividend["declaration_date"]
        )

        print(
            "Record date:     ",
            next_dividend["record_date"]
        )

        print(
            "Payment date:    ",
            next_dividend["payment_date"]
        )

        print(
            "Amount:           $",
            next_dividend["amount"]
        )

        print(
            "Days from today: ",
            days_until
        )

        print(
            "Status:           OFFICIAL"
        )

    # --------------------------------------------------------
    # ESTIMATE NEXT DIVIDEND
    # --------------------------------------------------------

    elif not today_dividends:

        print()
        print(
            "NO OFFICIAL FUTURE DIVIDEND "
            "HAS BEEN DECLARED."
        )

        if typical_days is not None:

            last_ex_date = dividends[-1][
                "ex_date"
            ]

            estimated_date = (
                last_ex_date
                + timedelta(days=typical_days)
            )

            # Move weekend estimate to Monday
            estimated_date = next_weekday(
                estimated_date
            )

            days_until = (
                estimated_date - today
            ).days

            print()
            print("---------------------------------")
            print("ESTIMATED NEXT EX-DIVIDEND DATE")
            print("---------------------------------")

            print(
                "Estimated date: ",
                estimated_date
            )

            print(
                "Days from today:",
                days_until
            )

            print(
                "Frequency:      ",
                frequency
            )

            print(
                "Typical gap:    ",
                f"~{typical_days} days"
            )

            print(
                "Status:          ESTIMATED"
            )

            print()
            print("NOTICE:")

            print(
                "This date is estimated from historical "
                "ex-dividend dates."
            )

            print(
                "It is NOT an officially declared date."
            )

        else:

            print()
            print(
                "Not enough dividend history exists "
                "to estimate the next date."
            )

    print()
    print("=" * 65)


# ============================================================
# GET TICKERS FROM GITHUB ACTIONS
# ============================================================

ticker_input = os.environ.get("TICKERS")


# ============================================================
# IF RUNNING LOCALLY
# ============================================================

if not ticker_input:

    ticker_input = input(
        "\nEnter tickers separated by commas "
        "(example: JEPI, JEPQ, SCHD, VOO): "
    )


# ============================================================
# CREATE TICKER LIST
# ============================================================

tickers = [

    ticker.strip().upper()

    for ticker in ticker_input.split(",")

    if ticker.strip()
]


# Remove duplicates while preserving order

tickers = list(
    dict.fromkeys(tickers)
)


# ============================================================
# CHECK INPUT
# ============================================================

if not tickers:

    print("No tickers were entered.")

    raise SystemExit(1)


# ============================================================
# START
# ============================================================

print()
print("=" * 65)
print("DIVIDEND FINDER")
print("=" * 65)

print(
    f"Looking up {len(tickers)} ticker(s): "
    + ", ".join(tickers)
)

print("=" * 65)


# ============================================================
# LOOK UP EVERY TICKER
# ============================================================

for index, ticker in enumerate(tickers):

    get_dividend(ticker)

    # Wait between API requests
    if index < len(tickers) - 1:

        next_ticker = tickers[index + 1]

        print()
        print(
            f"Waiting {WAIT_BETWEEN_REQUESTS} seconds "
            f"before looking up {next_ticker}..."
        )

        time.sleep(
            WAIT_BETWEEN_REQUESTS
        )


# ============================================================
# FINISHED
# ============================================================

print()
print("=" * 65)
print("ALL TICKERS FINISHED")
print("=" * 65)
