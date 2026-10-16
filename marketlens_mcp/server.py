"""MarketLens: a small MCP server for stock context and thesis tracking."""

import json
import math
import re
from datetime import datetime
from pathlib import Path

import yfinance as yf
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MarketLens")

DATA_FOLDER = Path(__file__).resolve().parent.parent / "data"
THESIS_FILE = DATA_FOLDER / "theses.json"

ALLOWED_PERIODS = {"5d", "1mo", "3mo", "6mo", "1y"}


def normalize_symbol(symbol: str) -> str:
    """Use NSE symbols by default, while allowing explicit exchange suffixes."""
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("Please enter a stock symbol, such as RELIANCE or TCS.")

    if not re.fullmatch(r"[A-Z0-9^._-]{1,20}", symbol):
        raise ValueError("The symbol contains characters that are not supported.")

    # Bare symbols are treated as NSE-listed Indian stocks.
    if "." not in symbol and not symbol.startswith("^"):
        symbol = symbol + ".NS"

    return symbol


def percent_change(old_price: float, new_price: float) -> float:
    """Return the percentage change from one price to another."""
    if old_price == 0:
        return 0.0
    return ((new_price - old_price) / old_price) * 100


def load_theses() -> dict:
    """Read saved stock notes from the local JSON file."""
    if not THESIS_FILE.exists():
        return {}

    try:
        with THESIS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        return {}

    return {}


def save_theses(theses: dict) -> None:
    """Save stock notes locally as readable JSON."""
    DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    with THESIS_FILE.open("w", encoding="utf-8") as file:
        json.dump(theses, file, indent=2, ensure_ascii=False)


def get_history(symbol: str, period: str = "3mo"):
    """Download daily price history from Yahoo Finance through yfinance."""
    clean_symbol = normalize_symbol(symbol)

    if period not in ALLOWED_PERIODS:
        raise ValueError(
            "Unsupported period. Choose one of: 5d, 1mo, 3mo, 6mo, or 1y."
        )

    try:
        history = yf.Ticker(clean_symbol).history(
            period=period,
            interval="1d",
            auto_adjust=True,
        )
    except Exception as error:
        raise ValueError(
            f"Market data could not be downloaded for {clean_symbol}. "
            "Please try again later."
        ) from error

    if history.empty:
        raise ValueError(
            f"No price history was returned for {clean_symbol}. "
            "Check the ticker symbol and try again."
        )

    history = history.dropna(subset=["Close"])
    if history.empty:
        raise ValueError(f"No closing prices are available for {clean_symbol}.")

    return clean_symbol, history


def build_snapshot(symbol: str) -> dict:
    """Create a short summary using the last available daily closing prices."""
    clean_symbol, history = get_history(symbol, "1mo")
    prices = [float(price) for price in history["Close"].tolist()]
    dates = list(history.index)
    volumes = [float(value) if not math.isnan(float(value)) else 0 for value in history["Volume"].tolist()]

    latest_price = prices[-1]
    previous_price = prices[-2] if len(prices) > 1 else latest_price
    first_price = prices[0]
    five_day_start = prices[-6] if len(prices) >= 6 else first_price
    date_label = dates[-1].strftime("%Y-%m-%d")

    result = {
        "symbol": clean_symbol,
        "last_available_trading_date": date_label,
        "latest_daily_close": round(latest_price, 2),
        "previous_close": round(previous_price, 2),
        "latest_session_change_percent": round(
            percent_change(previous_price, latest_price), 2
        ),
        "return_over_available_month_percent": round(
            percent_change(first_price, latest_price), 2
        ),
        "return_over_about_five_sessions_percent": round(
            percent_change(five_day_start, latest_price), 2
        ),
        "latest_reported_volume": int(volumes[-1]),
        "data_note": (
            "This is the latest daily bar returned by Yahoo Finance, not a guaranteed "
            "real-time quote. A market holiday or data-provider delay can make the date older."
        ),
    }

    thesis = load_theses().get(clean_symbol)
    if thesis:
        invalidation_price = float(thesis["invalidation_price"])
        result["saved_thesis"] = thesis["thesis"]
        result["thesis_entry_price"] = thesis["entry_price"]
        result["thesis_invalidation_price"] = invalidation_price
        result["thesis_check"] = (
            "Price is at or below the invalidation level. Review the original thesis."
            if latest_price <= invalidation_price
            else "Price is above the saved invalidation level. This alone does not confirm the thesis."
        )

    return result


@mcp.tool()
def get_stock_snapshot(symbol: str) -> dict:
    """Get the latest available daily close and short-term returns for a stock."""
    return build_snapshot(symbol)


@mcp.tool()
def compare_stocks(symbols: str, period: str = "1mo") -> dict:
    """Compare the historical price return of up to five comma-separated symbols."""
    if period not in ALLOWED_PERIODS:
        raise ValueError("Choose a period of 5d, 1mo, 3mo, 6mo, or 1y.")

    entered_symbols = [item.strip() for item in symbols.split(",") if item.strip()]
    if not entered_symbols:
        raise ValueError("Enter at least one symbol, separated by commas.")
    if len(entered_symbols) > 5:
        raise ValueError("Please compare no more than five symbols at a time.")

    comparisons = []
    for entered_symbol in entered_symbols:
        try:
            clean_symbol, history = get_history(entered_symbol, period)
            prices = [float(price) for price in history["Close"].tolist()]
            if len(prices) < 2:
                comparisons.append({
                    "symbol": clean_symbol,
                    "error": "Not enough daily data to calculate a return.",
                })
                continue

            comparisons.append({
                "symbol": clean_symbol,
                "first_available_date": history.index[0].strftime("%Y-%m-%d"),
                "last_available_date": history.index[-1].strftime("%Y-%m-%d"),
                "first_close": round(prices[0], 2),
                "last_close": round(prices[-1], 2),
                "period_return_percent": round(percent_change(prices[0], prices[-1]), 2),
            })
        except ValueError as error:
            comparisons.append({
                "symbol": entered_symbol.upper(),
                "error": str(error),
            })

    return {
        "period": period,
        "results": comparisons,
        "note": "Historical return is not a prediction of future performance.",
    }


@mcp.tool()
def analyze_price_move(symbol: str) -> dict:
    """Check for an unusually large daily move or volume compared with recent history."""
    clean_symbol, history = get_history(symbol, "3mo")
    prices = [float(price) for price in history["Close"].tolist()]
    volumes = [float(value) if not math.isnan(float(value)) else 0 for value in history["Volume"].tolist()]
    dates = list(history.index)

    if len(prices) < 2:
        raise ValueError(f"Not enough daily data to analyse {clean_symbol}.")

    daily_changes = []
    for index in range(1, len(prices)):
        daily_changes.append(percent_change(prices[index - 1], prices[index]))

    latest_change = daily_changes[-1]
    recent_changes = daily_changes[-20:]
    average_daily_move = sum(abs(change) for change in recent_changes) / len(recent_changes)

    if len(prices) >= 6:
        five_session_return = percent_change(prices[-6], prices[-1])
    else:
        five_session_return = percent_change(prices[0], prices[-1])

    if len(prices) >= 21:
        twenty_session_return = percent_change(prices[-21], prices[-1])
    else:
        twenty_session_return = percent_change(prices[0], prices[-1])

    observations = []
    unusually_large_move = abs(latest_change) > max(average_daily_move * 1.8, 1.0)
    if unusually_large_move:
        observations.append(
            "The latest daily move is larger than the recent average absolute daily move."
        )
    else:
        observations.append(
            "The latest daily move is not unusually large under this simple rule."
        )

    previous_volumes = volumes[-21:-1] if len(volumes) > 1 else []
    average_volume = (
        sum(previous_volumes) / len(previous_volumes) if previous_volumes else 0
    )
    latest_volume = volumes[-1]
    volume_ratio = latest_volume / average_volume if average_volume > 0 else None

    if volume_ratio is not None and volume_ratio >= 1.5:
        observations.append("Reported volume is at least 1.5 times its recent average.")
    elif volume_ratio is not None:
        observations.append("Reported volume is below 1.5 times its recent average.")
    else:
        observations.append("A useful recent average volume was not available.")

    thesis = load_theses().get(clean_symbol)
    thesis_check = "No saved thesis for this symbol."
    if thesis:
        thesis_check = (
            "Price is at or below your saved invalidation level; review your original reasoning."
            if prices[-1] <= float(thesis["invalidation_price"])
            else "Price is above your saved invalidation level; keep reviewing the evidence."
        )

    return {
        "symbol": clean_symbol,
        "last_available_trading_date": dates[-1].strftime("%Y-%m-%d"),
        "latest_daily_change_percent": round(latest_change, 2),
        "average_absolute_daily_move_percent_recent_sessions": round(average_daily_move, 2),
        "return_over_about_five_sessions_percent": round(five_session_return, 2),
        "return_over_about_twenty_sessions_percent": round(twenty_session_return, 2),
        "latest_volume": int(latest_volume),
        "average_volume_previous_sessions": int(average_volume),
        "volume_vs_average": round(volume_ratio, 2) if volume_ratio is not None else None,
        "observations": observations,
        "saved_thesis_check": thesis_check,
        "important_note": (
            "These are simple historical signals, not an explanation of the cause. "
            "No news is checked, and the results are not a buy or sell recommendation."
        ),
    }


@mcp.tool()
def save_stock_thesis(
    symbol: str,
    thesis: str,
    entry_price: float,
    invalidation_price: float,
) -> dict:
    """Save your own reason for following a stock and the price level to review it."""
    clean_symbol = normalize_symbol(symbol)

    if not thesis.strip():
        raise ValueError("Please write a short reason for following this stock.")
    if entry_price <= 0 or invalidation_price <= 0:
        raise ValueError("Entry price and invalidation price must both be above zero.")

    all_theses = load_theses()
    all_theses[clean_symbol] = {
        "symbol": clean_symbol,
        "thesis": thesis.strip(),
        "entry_price": round(float(entry_price), 2),
        "invalidation_price": round(float(invalidation_price), 2),
        "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    save_theses(all_theses)

    return {
        "saved": True,
        "stock": clean_symbol,
        "message": "Your note was saved locally. It can be reviewed with the snapshot and price-move tools.",
        "note": "This is your own tracking rule, not a recommendation to buy or sell.",
    }


@mcp.resource("marketlens://guide")
def marketlens_guide() -> str:
    """Explain what this server measures and its limitations."""
    return (
        "MarketLens guide\n\n"
        "MarketLens is a learning and watchlist helper for Indian stocks. A bare ticker such as "
        "RELIANCE is treated as an NSE ticker (RELIANCE.NS). You can pass an explicit .BO suffix "
        "for a BSE symbol. Prices come from Yahoo Finance through yfinance and use daily historical "
        "bars, so they are not guaranteed real-time prices. The move checker compares the last "
        "daily return and volume with recent history. It does not read news, know why a price moved, "
        "or predict future prices. Saved thesis notes live in data/theses.json on this computer. "
        "Nothing here is a buy or sell recommendation."
    )


@mcp.resource("watchlist://theses")
def saved_theses_resource() -> str:
    """Read the locally saved stock theses as JSON."""
    theses = load_theses()
    return json.dumps(theses, indent=2, ensure_ascii=False) if theses else "No stock theses have been saved yet."


@mcp.resource("stock://{symbol}/summary")
def stock_summary_resource(symbol: str) -> str:
    """Read a recent daily-price summary for one stock."""
    return json.dumps(build_snapshot(symbol), indent=2, ensure_ascii=False)


@mcp.prompt()
def morning_market_brief(symbols: str) -> str:
    """Create a careful morning brief for a comma-separated list of stocks."""
    return (
        f"Prepare a concise market brief for these symbols: {symbols}. "
        "Use compare_stocks with the 1mo period and get_stock_snapshot for each stock. "
        "Separate measured facts from interpretation, include the data dates, and explain that "
        "daily data may be delayed. Do not invent news or give buy/sell instructions."
    )


@mcp.prompt()
def explain_price_move(symbol: str) -> str:
    """Ask for a plain-English explanation of the measured price and volume changes."""
    return (
        f"Review the latest available daily data for {symbol}. Call analyze_price_move first. "
        "Explain each metric in plain English, separate what the data shows from possible causes, "
        "and explicitly say that this server does not check news or establish causation."
    )


@mcp.prompt()
def review_my_thesis(symbol: str) -> str:
    """Compare the saved tracking thesis with recent price data without making a trade call."""
    return (
        f"Review my saved thesis for {symbol}. Read watchlist://theses, then call "
        "get_stock_snapshot and analyze_price_move. Tell me whether the saved invalidation level "
        "has been reached, what evidence is missing, and which assumptions I should review. "
        "Do not tell me to buy or sell."
    )


@mcp.prompt()
def weekly_watchlist_review(symbols: str) -> str:
    """Review weekly changes and identify which stocks deserve closer research."""
    return (
        f"Review this watchlist: {symbols}. Compare each symbol over 1mo and 3mo, then use "
        "analyze_price_move for unusual daily moves or volume. Summarize what changed, list "
        "questions for further research, and note where data is missing. Do not present past returns "
        "as predictions or issue buy/sell recommendations."
    )


if __name__ == "__main__":
    mcp.run()
