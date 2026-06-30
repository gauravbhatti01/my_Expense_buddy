"""
parser.py — turns a plain-English Telegram message into a transaction dict.

    parse_message("spent 500 on ola") ->
        {"amount": 500.0, "category": "travel", "note": "ola", "type": "expense"}

Everything that's likely to need tweaking (keyword lists, filler words,
amount suffixes) lives in plain Python data structures at the top of the
file so it's easy to edit without touching the parsing logic itself.
"""

import re

# ---------------------------------------------------------------------------
# 1. CATEGORY KEYWORDS — edit these freely. Order matters: first match wins,
#    so put more specific keywords above more generic ones if they overlap.
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "rent": [
        "rent", "landlord", "lease", "maintenance charge", "society maintenance",
    ],
    "food": [
        "swiggy", "zomato", "chai", "coffee", "restaurant", "dinner",
        "lunch", "breakfast", "starbucks", "dominos", "pizza", "burger",
        "cafe", "tea", "snack", "food", "eat", "biryani", "ccd",
    ],
    "groceries": [
        "blinkit", "zepto", "bigbasket", "grocery", "groceries", "dmart",
        "vegetables", "veggies", "milk", "kirana", "instamart",
    ],
    "travel": [
        "ola", "uber", "rapido", "metro", "auto", "cab", "taxi", "petrol",
        "diesel", "fuel", "flight", "irctc", "train", "bus", "fastag",
        "parking", "toll",
    ],
    "bills": [
        "electricity", "wifi", "broadband", "recharge", "mobile bill",
        "water bill", "gas bill", "dth", "jio", "airtel", "vi ", "bill",
    ],
    "emis": [
        "emi", "emis", "loan", "hdfc", "bike",
    ],
    "insurance": [
        "insurance", "lic", "insurance premium",
    ],
    "investments": [
        "sip", "etf", "stocks", "stock", "mutual fund", "mf", "zerodha",
        "groww", "invest", "investment", "ppf", "nps", "gold", "crypto",
        "bitcoin",
    ],
    "emergency": [
        "emergency", "emergency fund", "medical reserve", "saving buffer",
    ],
    "clothes": [
        "myntra", "ajio", "shirt", "tshirt", "t-shirt", "jeans", "shoes",
        "footwear", "clothes", "clothing", "dress", "kurta", "h&m",
        "zara", "nike", "adidas",
    ],
    "luxuries": [
        "netflix", "prime video", "hotstar", "spotify", "gym", "movie",
        "pvr", "inox", "bookmyshow", "subscription", "ott", "party",
        "alcohol", "beer", "wine", "cigarette", "shopping spree",
    ],
    "health": [
        "doctor", "hospital", "medicine", "pharmacy", "medical", "clinic",
        "apollo", "pathology", "dentist", "checkup", "health",
    ],
    "education": [
        "course", "udemy", "coursera", "book", "books", "tuition", "fees",
        "fee", "exam", "certification", "class",
    ],
}

DEFAULT_CATEGORY = "other"

# ---------------------------------------------------------------------------
# 2. INCOME KEYWORDS — if any of these appear, the txn is type="income"
#    instead of "expense".
# ---------------------------------------------------------------------------
INCOME_KEYWORDS = [
    "salary", "refund", "cashback", "received", "credited", "credit",
    "income", "bonus", "freelance payment", "got paid", "payout",
    "reimbursement", "interest credited", "dividend",
]

# ---------------------------------------------------------------------------
# 3. FILLER WORDS stripped out of the message to build the "note" field.
#    Amount tokens, currency symbols and these words are removed; whatever
#    remains becomes the note (category keyword usually remains, which is
#    fine — it doubles as a description, e.g. "ola", "swiggy dinner").
# ---------------------------------------------------------------------------
FILLER_WORDS = {
    "spent", "spend", "on", "for", "rs", "rs.", "inr", "the", "a", "an",
    "of", "paid", "pay", "got", "received", "credited", "credit", "to",
    "at", "via", "using", "with", "today", "yesterday", "from",
}

# ---------------------------------------------------------------------------
# AMOUNT PARSING
# ---------------------------------------------------------------------------
# Matches things like: 500  1,250  1.5k  2l  rs 500  ₹500  500rs  2.5L
_AMOUNT_RE = re.compile(
    r"""
    (?:rs\.?\s*|inr\s*|₹\s*)?          # optional leading currency marker
    (?P<num>\d[\d,]*\.?\d*)            # the numeric part (commas allowed)
    \s*
    (?P<suffix>k|l|lakh|lakhs)?        # optional magnitude suffix
    \s*(?:rs\.?|inr|₹)?                # optional trailing currency marker
    """,
    re.IGNORECASE | re.VERBOSE,
)

_SUFFIX_MULTIPLIER = {
    "k": 1_000,
    "l": 100_000,
    "lakh": 100_000,
    "lakhs": 100_000,
}


def _find_amount(text: str):
    """Find the first plausible amount in the text. Returns (value, matched_span)."""
    best = None
    for m in _AMOUNT_RE.finditer(text):
        num_str = m.group("num")
        if not num_str:
            continue
        # Skip standalone bare numbers with no currency context only if there
        # are multiple candidates later — for now accept the first numeric
        # token found since most messages contain exactly one amount.
        try:
            value = float(num_str.replace(",", ""))
        except ValueError:
            continue
        suffix = (m.group("suffix") or "").lower()
        if suffix in _SUFFIX_MULTIPLIER:
            value *= _SUFFIX_MULTIPLIER[suffix]
        best = (value, m.span())
        break  # first match wins
    return best


def _strip_filler(text: str, amount_span) -> str:
    """Remove the amount substring, currency symbols, and filler words."""
    if amount_span:
        start, end = amount_span
        text = text[:start] + " " + text[end:]

    text = text.replace("₹", " ")
    tokens = re.findall(r"[A-Za-z]+", text)
    kept = [t for t in tokens if t.lower() not in FILLER_WORDS]
    note = " ".join(kept).strip()
    return note


def _detect_category(lowered_text: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered_text:
                return category
    return DEFAULT_CATEGORY


def _detect_type(lowered_text: str) -> str:
    for kw in INCOME_KEYWORDS:
        if kw in lowered_text:
            return "income"
    return "expense"


def parse_message(message: str):
    """
    Parse a free-text message into a transaction dict, or return None if no
    amount could be found (caller should ask the user to clarify).

    Returns:
        {
            "amount": float,
            "category": str,
            "note": str,
            "type": "expense" | "income",
        }
    """
    if not message or not message.strip():
        return None

    text = message.strip()
    lowered = text.lower()

    found = _find_amount(text)
    if not found:
        return None
    amount, span = found
    if amount <= 0:
        return None

    txn_type = _detect_type(lowered)
    category = "income" if txn_type == "income" else _detect_category(lowered)
    note = _strip_filler(text, span)

    if not note:
        note = category

    return {
        "amount": round(amount, 2),
        "category": category,
        "note": note,
        "type": txn_type,
    }


if __name__ == "__main__":
    samples = [
        "spent 500 on ola",
        "swiggy 420 dinner",
        "1.5k myntra shirt",
        "got salary 75000",
        "rs 1,250 electricity bill",
        "2l invested in mutual fund",
        "₹300 chai with friends",
        "blinkit 650 groceries",
        "netflix 199",
        "gym membership 1500",
        "received cashback 50",
        "paid rent 15000",
        "doctor visit 800",
        "udemy course 499",
        "500rs uber",
    ]
    for s in samples:
        print(f"{s!r:40} -> {parse_message(s)}")
