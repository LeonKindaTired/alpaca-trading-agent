# Competition window research

Source notes compiled 28 Aug 2026. Re-check lablab.ai / Alpaca official terms before lock-in.

## Dates

- Hackathon: **28 August – 4 September 2026** (online, lablab.ai + Alpaca).
- Today is day 1.

## US equity/options hours (ET)

- Regular session: 09:30–16:00.
- Options: Alpaca documents cutoff around 15:15 ET (15:30 ET for broad ETFs like SPY/QQQ) on expiration days.
- **Mon 1 Sep 2026 is Labor Day — US markets closed.**
- Weekend 29–30 Aug: closed.

Effective cash-session days in-window after kickoff: Fri 28 Aug, Tue 2 Sep, Wed 3 Sep, Thu 4 Sep (plus whatever remains of day 1). Overnight/weekend the agent should idle, not force trades.

## Scoring / constraints (from public posts; confirm on lablab)

- Dedicated paper account, **$100,000** starting balance.
- Strategies **must include options**.
- Judging mentioned: P&L, technology, creativity, presentation.
- Use Alpaca Trading API **and** MCP server or CLI.

## Instruments

Start with liquid ETF options: SPY, QQQ, IWM. Avoid earnings-specific names unless an event falls in this short window.

## Strategy implication

Need frequent, liquid opportunities with defined exits. Weekend + Labor Day shrinks live validation time. Paper-cycle reliability beats exotic structure.
