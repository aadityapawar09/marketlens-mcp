# MarketLens MCP

MarketLens is a small MCP server that helps a user understand daily stock-price changes and keep track of their own reasons for following a stock. It is built with Python, `uv`, and the MCP Python SDK.

It is designed as a learning project, not a trading bot. It does not place orders, predict prices, or tell anyone what to buy or sell.

## What makes it different?

Instead of only returning a stock quote, MarketLens combines three things:

- A short historical price and volume summary.
- A simple check for unusually large daily moves compared with the stock's own recent history.
- A local **thesis note**: the user's reason for following a stock and a price level at which they want to review that reasoning.

This is a focused design choice, not a claim that nobody else has built anything similar.

## Features

### 4 tools

| Tool | Purpose |
|---|---|
| `get_stock_snapshot` | Shows the latest available daily close, recent returns, trading date, and any saved thesis check. |
| `compare_stocks` | Compares the price returns of up to five stocks over `5d`, `1mo`, `3mo`, `6mo`, or `1y`. |
| `analyze_price_move` | Checks whether the latest daily move or volume looks unusual versus recent sessions. |
| `save_stock_thesis` | Saves a user's own reasoning, entry reference price, and invalidation level in a local JSON file. |

### 3 resources

| Resource URI | Purpose |
|---|---|
| `marketlens://guide` | Explains the data source, calculations, and limitations. |
| `watchlist://theses` | Reads the locally saved stock theses. |
| `stock://{symbol}/summary` | Provides a recent price summary for a selected symbol. |

### 4 prompts

- `morning_market_brief` — summarize a list of stocks using measured data.
- `explain_price_move` — explain the observed price and volume changes in plain English.
- `review_my_thesis` — compare a saved thesis with recent data and highlight assumptions to review.
- `weekly_watchlist_review` — compare short and medium-term returns and suggest research questions.



## Example tool calls

### Get a stock snapshot

```text
get_stock_snapshot(symbol="RELIANCE")
```

### Compare a few stocks

```text
compare_stocks(symbols="RELIANCE,TCS,INFY", period="1mo")
```

### Check an unusual move

```text
analyze_price_move(symbol="HDFCBANK")
```

### Save your own research note

```text
save_stock_thesis(
    symbol="TCS",
    thesis="I am following revenue growth and cloud services demand.",
    entry_price=3500,
    invalidation_price=3200
)
```

The prices above are example inputs only, not current prices or recommendations. A saved thesis can be reviewed by calling `get_stock_snapshot` or `analyze_price_move` for that symbol.


- This project is for education and personal research, not financial advice.
