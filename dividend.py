import os
import requests

from datetime import datetime, timedelta
from statistics import median


# ============================================================
# API KEY
# ============================================================

# GitHub Actions will get this from GitHub Secrets.
# Do NOT put your real API key directly in this file.

API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")


# ============================================================
# MOVE WEEKENDS TO MONDAY
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

    # Look at up to the most recent 8 dividends
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

    # Median helps prevent one unusual dividend
    # from messing up the frequency calculation.
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
# GET DIVIDEND INFORMATION
# ============================================================

def get_dividend(ticker):

    ticker = ticker.strip().upper()

    print("\n")
    print("=" * 65)
    print(f"TICKER: {ticker}")
    print("=" * 65)

    # Make sure API key exists
    if not API_KEY:

        print("ERROR: Alpha Vantage API key was not found.")
        print(
            "Add ALPHA_VANTAGE_API_KEY to GitHub Actions Secrets."
        )

        return

    url = "https://www.alphavantage.co/query"

    params = {
        "function": "DIVIDENDS",
        "symbol": ticker,
        "apikey": API_KEY
    }

    # ========================================================
    # CONNECT TO ALPHA VANTAGE
    # ========================================================

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

    except Exception as e:

        print("Connection error:")
        print(e)

        return


    # ========================================================
    # CHECK API RESPONSE
    # ========================================================

    if "data" not in data:

        print("Could not find dividend data.")

        if "Information" in data:

            print(data["Information"])

        elif "Note" in data:

            print(data["Note"])

        elif "Error Message" in data:

            print(data["Error Message"])

        return


    # ========================================================
    # PROCESS DIVIDENDS
    # ========================================================

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

        except ValueError:

            continue


    # Sort oldest -> newest

    dividends.sort(
        key=lambda x: x["ex_date"]
    )


    if not dividends:

        print(
            f"No dividend history found for {ticker}."
        )

        return


    # ========================================================
    # DETECT FREQUENCY
    # ========================================================

    frequency, typical_days = detect_frequency(
        dividends
    )


    print()
    print(f"Dividend Frequency: {frequency}")

    if typical_days:

        print(
            f"Typical Interval:   ~{typical_days} days"
        )


    # ========================================================
    # SEPARATE PAST / TODAY / FUTURE
    # ========================================================

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


    # ========================================================
    # EX-DIVIDEND TODAY
    # ========================================================

    if today_dividends:

        dividend_today = today_dividends[0]

        print()
        print("*********************************")
        print("      EX-DIVIDEND TODAY")
        print("*********************************")

        print(
            "Ex-dividend date:",
            dividend_today["ex_date"]
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


    # ========================================================
    # LAST KNOWN DIVIDEND
    # ========================================================

    elif past:

        latest = past[-1]

        print()
        print("LAST KNOWN DIVIDEND")

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


    # ========================================================
    # OFFICIAL FUTURE DIVIDEND
    # ========================================================

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


    # ========================================================
    # ESTIMATE NEXT DIVIDEND
    # ========================================================

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

            # Move weekend estimates to Monday
            estimated_date = next_weekday(
                estimated_date
            )

            days_until = (
                estimated_date
                - today
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
                "Status:          ESTIMATED"
            )


            print()
            print("NOTICE:")

            print(
                "This date is an estimate based on "
                "historical dividend timing."
            )

            print(
                "It is NOT an officially declared date."
            )


        else:

            print(
                "Not enough dividend history "
                "to estimate the next date."
            )


    print()
    print("=" * 65)


# ============================================================
# GET TICKERS
# ============================================================

# GitHub Actions will supply TICKERS automatically.
# If running locally, it will ask you to enter them.

ticker_input = os.environ.get("TICKERS")


if not ticker_input:

    ticker_input = input(
        "\nEnter tickers separated by commas "
        "(example: JEPI, JEPQ, SCHD, VOO): "
    )


# ============================================================
# CONVERT INPUT TO LIST
# ============================================================

tickers = [

    ticker.strip().upper()

    for ticker in ticker_input.split(",")

    if ticker.strip()
]


# Remove duplicate tickers

tickers = list(
    dict.fromkeys(tickers)
)


# ============================================================
# RUN
# ============================================================

print()
print(
    f"Looking up {len(tickers)} ticker(s)..."
)


for ticker in tickers:

    get_dividend(ticker)
