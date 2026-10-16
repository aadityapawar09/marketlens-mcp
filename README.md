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

## Data source and symbols

Market data is fetched from Yahoo Finance through the `yfinance` Python package. It uses daily historical bars, **not guaranteed real-time quotes**. A bare Indian stock symbol defaults to NSE; for example, `RELIANCE` becomes `RELIANCE.NS`. An explicit suffix such as `TCS.BO` is preserved. Use `^NSEI` for the Nifty 50 index.

No API key is needed for the basic version. Yahoo Finance access can change or be rate-limited, so a data request may occasionally fail.

## Requirements

- Windows, macOS, or Linux
- Python 3.11 or newer
- `uv`
- Internet access for stock data

## Setup on Windows

Open PowerShell in the folder where you want the project.

1. Install `uv` if you do not already have it. Official instructions: <https://docs.astral.sh/uv/getting-started/installation/>.
2. Download or clone this repository, then enter its folder.
3. Install dependencies:

   ```powershell
   uv sync
   ```

4. Run the server directly:

   ```powershell
   uv run python -m marketlens_mcp.server
   ```

   The server uses standard input/output transport, so it may wait quietly when started directly. That is normal when an MCP client is expected to connect to it.

5. To test the tools interactively with MCP Inspector:

   ```powershell
   uv run mcp dev marketlens_mcp/server.py
   ```

   The Inspector opens in your browser. Select each tool and try the examples below.

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

## Connect it to Claude Desktop on Windows

This is a **local MCP server**. It runs from the folder on your computer; GitHub is where you store and share the code. This configuration is for the **Claude Desktop app**, not the Claude website in a browser.

### 1. Put the folder in a simple location

Extract this project to:

`C:\Users\HP\Documents\marketlens-mcp`

If your Windows account is not `HP`, or you choose another folder, use your actual folder path in the config below.

### 2. Install the project dependencies

Open PowerShell in the `marketlens-mcp` folder and run:

```powershell
uv sync
```

Confirm that `uv` is available:

```powershell
uv --version
```

### 3. Open Claude Desktop's config file

In Claude Desktop, open **Settings → Developer → Edit Config**. On Windows the file is usually `%APPDATA%\Claude\claude_desktop_config.json`.

Add the `marketlens` entry inside the existing `mcpServers` object. **Keep your other MCP entries**, such as `learning-log`, exactly as they are. Do not replace the whole file with this small example.

```json
{
  "mcpServers": {
    "marketlens": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\HP\\Documents\\marketlens-mcp",
        "run",
        "python",
        "-m",
        "marketlens_mcp.server"
      ]
    }
  }
}
```

This is an example of the full file for a new setup. If you already have `mcpServers`, merge only the `marketlens` object into it, adding a comma after the preceding server object when needed.

If Claude reports that it cannot find `uv` (for example, `spawn uv ENOENT`), find the actual executable path in PowerShell:

```powershell
(Get-Command uv).Source
```

Copy that path into the JSON `command` value, escaping each backslash as `\\`. For example, `C:\Users\HP\.local\bin\uv.exe` must be written as `C:\\Users\\HP\\.local\\bin\\uv.exe` in JSON.

### 4. Restart and test

Fully quit Claude Desktop, then open it again. In a new chat, open the **+** menu and look under **Connectors** for MarketLens and its tools. You can also check **Settings → Developer** for connection status or MCP logs.

Try asking Claude:

- `Use MarketLens to get the latest available daily snapshot for RELIANCE.`
- `Use MarketLens to compare RELIANCE, TCS, and INFY over one month.`
- `Help me save a research thesis for TCS with an entry reference price and an invalidation level.`

The tool returns daily historical data from Yahoo Finance, not a guaranteed live quote. The first run may take a little longer while `uv` sets up the environment.

## Run the tests

The tests only cover small helper functions, so they do not need to call Yahoo Finance:

```powershell
uv run python -m unittest discover -s tests
```

## Where the saved notes go

The server stores thesis notes in `data/theses.json` inside the project folder. That file is in `.gitignore`, so your personal notes should not be pushed to GitHub. The `data/.gitkeep` file only keeps the empty folder in the repository.

## How to explain it in a tutor demo

- **Tool:** a callable action, such as comparing three stock returns.
- **Resource:** read-only context, such as the usage guide or saved theses.
- **Prompt:** a reusable instruction template for common jobs, such as a weekly review.
- **UV:** manages the Python project and installs dependencies from `pyproject.toml`.
- **Thesis tracking:** stores the user's own note and warns when the last available daily close is at or below the saved invalidation level. It does not decide whether the stock is a good investment.

## Limitations

- Daily data can be delayed, missing, adjusted, or unavailable.
- The move checker uses simple historical rules, not news or company fundamentals.
- A large price or volume change does not explain its cause.
- Historical returns do not predict future returns.
- This project is for education and personal research, not financial advice.
