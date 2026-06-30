# ledger — a Telegram-controlled expense tracker (100% offline)

Text a Telegram bot what you spent in plain English. It parses the amount and
category, saves it to a local SQLite file, and regenerates an offline HTML
dashboard you can open by double-clicking — no server, no cloud, nothing
leaves your machine.

```
┌─────────────────────────────┐        ┌────────────────────┐
│ you, on Telegram             │  ───►  │ bot.py              │
│ "swiggy 420 dinner"          │        │ parses + saves      │
└─────────────────────────────┘        └─────────┬───────────┘
                                                   │
                                          expenses.db (SQLite)
                                                   │
                                                   ▼
                                          export.py writes data.js
                                                   │
                                                   ▼
                                          dashboard.html (open in browser)
```

## Setup — 5 steps

**1. Get a Telegram bot token from BotFather**
Open Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`,
and follow the prompts. It'll give you a token that looks like
`123456789:AAExampleTokenStringGoesHere`.

**2. Add the token to `config.json`**
Open `config.json` and replace `PUT_YOUR_BOTFATHER_TOKEN_HERE` with your real
token. While you're there, set `monthlyBudget` and the per-category `budgets`
to whatever makes sense for you — these are read fresh every time you message
the bot, so you can edit them any time without restarting anything except the
bot process itself.

**3. Install the one dependency**
```
pip install python-telegram-bot
```
(If `pip` complains about an "externally managed environment", use
`pip install python-telegram-bot --break-system-packages`, or set up a venv.)

**4. Run the bot**
```
python bot.py
```
Leave this running in a terminal (or a `tmux`/`screen` session, or as a
background service) — it needs to stay up to receive your Telegram messages.
On first run it creates `expenses.db` and `data.js` automatically.

**5. Open the dashboard**
Double-click `dashboard.html`, or open it directly in any browser. It reads
`data.js` (sitting next to it) and re-renders every time you refresh the page
— so after logging a new expense on Telegram, just refresh the dashboard tab.

That's it. Everything — the database, the config, the dashboard — lives in
this one folder. Nothing is uploaded anywhere.

## How to log spending

Just message the bot naturally. A few examples it understands:

| You type                          | Parsed as                              |
|------------------------------------|-----------------------------------------|
| `spent 500 on ola`                | travel · ₹500 · "ola"                   |
| `swiggy 420 dinner`               | food · ₹420 · "swiggy dinner"           |
| `1.5k myntra shirt`               | clothes · ₹1,500 · "myntra shirt"       |
| `2l invested in mutual fund`      | investments · ₹2,00,000                 |
| `rs 1,250 electricity bill`       | bills · ₹1,250 · "electricity bill"     |
| `got salary 75000`                | income · ₹75,000 · "salary"             |
| `received cashback 50`            | income · ₹50 · "cashback"               |

Amount formats understood: `500`, `1,250`, `1.5k` (=1500), `2l` (=200000),
`rs 500`, `₹500`, `500rs`.

## Bot commands

- `/start` — quick intro
- `/help` — usage examples
- `/total` — this month's spend vs budget, with a progress bar
- `/undo` — delete the most recent entry you logged (per-chat)
- `/budget` — show your per-category caps and what you've spent against each

## Editing categories or keywords

Open `parser.py` — the `CATEGORY_KEYWORDS` dict near the top lists every
category and the words that trigger it. Add, remove, or move keywords freely;
the first matching category wins, so put more specific words above broader
ones if they could overlap. `INCOME_KEYWORDS` works the same way for
detecting income vs. expense.

If you add a brand-new category, also add it to the `ALL_CATEGORIES` list in
`export.py` and give it a budget cap in `config.json` so it shows up
correctly on the dashboard.

## Changing currency

`config.json`'s `"currency"` field controls the symbol shown everywhere. The
dashboard's Indian-style digit grouping (`₹12,34,567`) is specific to this
build — if you switch currencies, you may also want to swap `fmtINR` in
`dashboard.html` for a plain `toLocaleString()` call.

## Files in this project

| File             | Purpose                                                        |
|-------------------|-----------------------------------------------------------------|
| `parser.py`       | Turns a text message into `{amount, category, note, type}`     |
| `db.py`           | SQLite storage — add / undo / totals                            |
| `export.py`       | Reads the DB + config, writes `data.js` for the dashboard       |
| `bot.py`          | Telegram bot — wires parser + db + export together              |
| `config.json`     | Your bot token, currency, and budgets                           |
| `dashboard.html`  | The offline dashboard — open this file directly in a browser    |
| `data.js`         | Auto-generated by `export.py` — don't edit by hand               |
| `expenses.db`     | Auto-created SQLite database — your actual data lives here       |

## Privacy

`expenses.db` is the only place your transaction history is stored. `data.js`
mirrors it for the dashboard but never contains your bot token. Nothing in
this project makes a network call other than the bot's own connection to
Telegram's servers to receive your messages.
