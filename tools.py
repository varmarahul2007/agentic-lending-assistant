"""Deterministic tools the LLM can call while answering.

The model decides WHEN to call these (via each provider's tool-calling
API); this module is what actually runs. Every tool returns a plain-text
result string that is sent back to the model and also written to the chat
log.
"""

PROMO_DATA = {
    "rate_drop_1pct": {
        "title": "1% Rate Drop",
        "rows": [
            ("Type", "Lender-paid 1/0 temporary buydown"),
            ("Applies to", "Purchase loans only — not refinance"),
            ("Duration", "First 12 months only"),
            ("After month 12", "Payment returns to the full note-rate amount"),
        ],
        "note": "The note rate itself never changes — only the subsidized payment does, and only for the first year.",
    },
    "expert_edge": {
        "title": "Expert Edge (Find an Agent)",
        "rows": [
            ("Reward", "30% of gross agent commission (purchase only)"),
            ("Providers", "Clever Real Estate, Inc. and JMG (not Onity affiliates)"),
            ("Excluded states", "AK, IA, KS, LA, MO, MS, OK, OR, TN"),
        ],
        "note": "Onity is a mortgage lender only, not a brokerage; using Expert Edge is optional and never a loan condition. Onity Group does not pay the reward.",
    },
    "loyalty_lock_in": {
        "title": "Loyalty Lock-In",
        "rows": [
            ("Offer", "Meet or beat a competitor's rate by $500 in cost"),
            ("If unmatched", "Gift card covering first P&I payment, up to $2,000"),
            ("Requirement", "Locked competitor Loan Estimate dated within 2 business days of application"),
            ("Excludes", "Builder-preferred lender and credit union offers"),
        ],
        "note": "One comparison per application; not valid for loans already in process.",
    },
    "lock_and_shop": {
        "title": "Lock & Shop",
        "rows": [
            ("Lock period", "Up to 90 days, before a property address is provided"),
            ("Eligibility", "Must be Pre-Approved with Onity first"),
            ("Programs", "Standard Conventional and Government fixed-rate — not Jumbo"),
            ("Excluded states", "MA, OR"),
            ("Float-down", "One-time, needs signed contract, exercised >=10 days before closing, rate must drop >=0.25%"),
        ],
        "note": "Non-transferable to another lock, borrower, property, or program.",
    },
    "close_on_time_guarantee": {
        "title": "Close On-Time Guarantee",
        "rows": [
            ("Credit", "$1,500 toward closing costs"),
            ("Requirement", "Closing date >=25 days after complete application + signed purchase agreement"),
            ("Your part", "Use the digital portal, return requested items within 24 hours"),
        ],
        "note": "Eligibility can be affected by date changes, credit/income/employment changes, or unmet contract terms; must meet investor guidelines.",
    },
    "escrow_transfer": {
        "title": "Escrow Transfer",
        "rows": [
            ("What it does", "Moves escrow balance from your sold home to your new purchase"),
            ("Requirement", "Sold property must be Onity-serviced with a positive escrow balance"),
            ("Timing", "Sale must close within 9 days of the purchase closing"),
        ],
        "note": "Everyone on the current mortgage must remain on the new one; additional limitations may apply.",
    },
    "rate_redo": {
        "title": "Rate Redo",
        "rows": [
            ("Credit", "Up to $1,800 lender credit toward origination fees"),
            ("Window", "Refinance within 12 months of your loan's funding date"),
            ("Deadline", "Application completed before March 31, 2027"),
            ("Excludes", "Texas cash-out refinances, FHA Streamline loans, second liens"),
        ],
        "note": "One Rate Redo per property; refinance still subject to qualification and agency/investor guidelines.",
    },
}

# Tool schemas in Anthropic's format ({name, description, input_schema}).
# providers.py translates these to Gemini/OpenAI formats automatically.
TOOL_SCHEMAS = [
    {
        "name": "calculate_monthly_payment",
        "description": (
            "Calculate an estimated monthly mortgage payment (principal, interest, "
            "plus estimated taxes and insurance) given a home price, down payment "
            "percentage, interest rate, and loan term. Use this any time the user "
            "wants to know what a home would cost per month. If the user doesn't "
            "have a rate in mind, call get_rates_info first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "home_price": {"type": "number", "description": "Total home price in US dollars"},
                "down_payment_percent": {"type": "number", "description": "Down payment as a percent, e.g. 10 for 10%"},
                "interest_rate_percent": {"type": "number", "description": "Annual interest rate as a percent, e.g. 6.5"},
                "loan_term_years": {"type": "number", "description": "Loan term in years, typically 15 or 30"},
            },
            "required": ["home_price", "down_payment_percent", "interest_rate_percent", "loan_term_years"],
        },
    },
    {
        "name": "check_prequalification",
        "description": "Give a rough, non-binding pre-qualification read based on income range, credit score range, and down payment saved.",
        "input_schema": {
            "type": "object",
            "properties": {
                "income_range": {"type": "string", "enum": ["under_60k", "60k_to_120k", "120k_plus"]},
                "credit_score_range": {"type": "string", "enum": ["below_620", "620_to_739", "740_plus"]},
                "down_payment_percent_saved": {"type": "string", "enum": ["under_5", "5_to_20", "20_plus"]},
            },
            "required": ["income_range", "credit_score_range", "down_payment_percent_saved"],
        },
    },
    {
        "name": "get_document_checklist",
        "description": "Return a checklist of documents typically needed for a mortgage application, tailored to employment type.",
        "input_schema": {
            "type": "object",
            "properties": {"employment_type": {"type": "string", "enum": ["w2_employee", "self_employed"]}},
            "required": ["employment_type"],
        },
    },
    {
        "name": "get_rates_info",
        "description": (
            "Point the user to Onity's real, live rates page and calculators instead "
            "of quoting a rate from memory. Always use this rather than stating any "
            "interest rate number yourself."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_promotion_details",
        "description": (
            "Get the exact, current terms and conditions for one of Onity's named "
            "Purchase Promise programs. Always use this before describing dollar "
            "amounts, day counts, or state exclusions for a promotion — don't recite "
            "them from memory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "promotion": {
                    "type": "string",
                    "enum": list(PROMO_DATA.keys()),
                }
            },
            "required": ["promotion"],
        },
    },
    {
        "name": "get_homebuying_steps",
        "description": "Return Onity's 6-step homebuying process as a checklist.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "request_human_handoff",
        "description": (
            "Connect the user with a human at Onity — for hardship situations, payoff "
            "quotes, complex questions, or explicit requests to talk to a person."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string", "description": "Brief reason, e.g. 'hardship', 'payoff quote', 'complex scenario'"}},
            "required": ["reason"],
        },
    },
]


def _monthly_pi(price: float, down_pct: float, rate_pct: float, years: float) -> float:
    principal = price * (1 - down_pct / 100)
    monthly_rate = (rate_pct / 100) / 12
    n = years * 12
    if monthly_rate == 0:
        return principal / n
    return principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)


def _calculate_monthly_payment(args: dict) -> str:
    price = float(args["home_price"])
    down_pct = float(args["down_payment_percent"])
    rate = float(args["interest_rate_percent"])
    years = float(args["loan_term_years"])
    pi = _monthly_pi(price, down_pct, rate, years)
    tax_ins = price * 0.013 / 12
    total = pi + tax_ins
    return (
        f"Home price ${price:,.0f}, {down_pct:g}% down, {rate:g}% for {years:g} years. "
        f"Principal & interest: ${pi:,.0f}/mo. Estimated taxes & insurance: ${tax_ins:,.0f}/mo. "
        f"Estimated total PITI: ${total:,.0f}/mo. Illustrative only — excludes PMI and HOA dues; "
        f"not a commitment to lend."
    )


def _check_prequalification(args: dict) -> str:
    credit = args.get("credit_score_range")
    savings = args.get("down_payment_percent_saved")
    if credit == "740_plus" and savings != "under_5":
        return ("Strong position for conventional financing. Likely qualifies for competitive "
                "conventional rates. This is a rough read, not a credit decision — use Onity's "
                "own Pre-Approval for the real thing.")
    if credit == "620_to_739":
        return ("Good fit — conventional or FHA. Conventional financing is likely available; FHA "
                "is worth comparing if the down payment is under 10%. Rough read only, not a "
                "credit decision.")
    if credit == "below_620":
        return ("FHA is likely the strongest path — FHA loans allow lower credit bands with as "
                "little as 3.5% down. Rough read only, not a credit decision.")
    return ("A full pre-qualification would help. A loan officer can pin down exact numbers "
            "quickly. Rough read only, not a credit decision.")


def _get_document_checklist(args: dict) -> str:
    if args.get("employment_type") == "self_employed":
        docs = ["2 years of personal & business tax returns", "Year-to-date profit & loss statement",
                "1099s if applicable", "60-90 days of bank statements (personal & business)", "Photo ID"]
    else:
        docs = ["Last 2 pay stubs", "W-2s from the past 2 years", "2 years of federal tax returns",
                "60 days of bank statements", "Photo ID"]
    return "Documents to gather: " + "; ".join(docs) + ". Exact requirements vary by loan program."


def _get_rates_info(args: dict) -> str:
    return ("Live rates change daily and are not quoted here. Direct the user to Today's Mortgage "
            "Rates at onitymortgage.com/learn/todays-mortgage-rates and the Affordability "
            "Calculator at onitymortgage.com/calculators/purchase, or call 1-877-319-0577 "
            "(Mon-Fri 8am-9pm ET, Sat 10am-4pm ET) for a live quote.")


def _get_promotion_details(args: dict) -> str:
    promo = PROMO_DATA.get(args.get("promotion", ""))
    if not promo:
        return f"Unknown promotion: {args.get('promotion')}"
    details = "; ".join(f"{k} — {v}" for k, v in promo["rows"])
    return (f"{promo['title']}: {details}. {promo['note']} Terms subject to change — confirm "
            f"current details with a loan officer.")


def _get_homebuying_steps(args: dict) -> str:
    steps = [
        "1) Meet a loan officer and get pre-approved",
        "2) Find a home with your agent (start 3-6 months out)",
        "3) Make an offer and schedule an inspection",
        "4) Apply for the mortgage and lock your rate",
        "5) Underwriting and appraisal",
        "6) Closing — sign, get the keys",
    ]
    return "The 6-step homebuying process: " + "; ".join(steps) + "."


def _request_human_handoff(args: dict) -> str:
    import re
    reason = str(args.get("reason", "general question"))
    hardship = bool(re.search(r"hardship|can.?t pay|forbearance|behind|struggl", reason.lower()))
    extra = (" Ask about Forbearance, Payment Deferral, or Mortgage Keeper — Onity's hardship "
             "assistance options." if hardship else " Or visit onitymortgage.com/support/contact-us.")
    return (f"Connecting for: {reason}. Phone 1-877-319-0577, Mon-Fri 8am-9pm ET, "
            f"Sat 10am-4pm ET.{extra}")


_IMPLEMENTATIONS = {
    "calculate_monthly_payment": _calculate_monthly_payment,
    "check_prequalification": _check_prequalification,
    "get_document_checklist": _get_document_checklist,
    "get_rates_info": _get_rates_info,
    "get_promotion_details": _get_promotion_details,
    "get_homebuying_steps": _get_homebuying_steps,
    "request_human_handoff": _request_human_handoff,
}


def execute_tool(name: str, args: dict) -> str:
    """Run a tool by name and return its plain-text result."""
    impl = _IMPLEMENTATIONS.get(name)
    if impl is None:
        return f"Unknown tool: {name}"
    try:
        return impl(args or {})
    except (KeyError, TypeError, ValueError) as exc:
        return f"Tool {name} failed on input {args!r}: {exc}"
