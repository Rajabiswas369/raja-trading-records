"""
cloud_data.py — Google Sheets backend for persistent cloud storage.
All trades and capital are stored in a Google Sheet, accessible from any device.
Falls back to in-memory storage if Google Sheets is not configured yet.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ── Column schema ─────────────────────────────────────────────────────────────
TRADE_COLUMNS = [
    "Trade #", "Date", "Time", "Symbol", "Option Type", "Strike", "Expiry",
    "Entry Price", "Exit Price", "Lots", "Lot Size", "Capital Used",
    "Gross P&L", "Brokerage", "STT", "Other Charges", "Net P&L", "Result",
    "Hold Time", "Entry RSI", "Entry ADX", "Supertrend", "Dashboard Said",
    "Lessons Learned", "Notes",
]

CAPITAL_COLUMNS = ["Date", "Balance", "Note"]

DEFAULT_BROKERAGE = 40.0
DEFAULT_STT_PCT   = 0.05
DEFAULT_OTHER     = 15.0


# ── Google Sheets connection ───────────────────────────────────────────────────

def _get_gc():
    """Return authenticated gspread client using Streamlit secrets."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def _get_sheet(tab_name: str):
    """Return a gspread worksheet by tab name."""
    gc        = _get_gc()
    sheet_url = st.secrets["sheet_url"]
    sh        = gc.open_by_url(sheet_url)
    try:
        return sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=30)
        return ws


def _is_cloud() -> bool:
    """True if Google Sheets secrets are configured."""
    try:
        return "gcp_service_account" in st.secrets and "sheet_url" in st.secrets
    except Exception:
        return False


# ── Trades ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_trades() -> pd.DataFrame:
    """Load all trades from Google Sheets (or empty DataFrame)."""
    if not _is_cloud():
        # local fallback — session state only
        if "trades_df" not in st.session_state:
            st.session_state.trades_df = pd.DataFrame(columns=TRADE_COLUMNS)
        return st.session_state.trades_df.copy()
    try:
        ws   = _get_sheet("Trades")
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=TRADE_COLUMNS)
        df = pd.DataFrame(data)
        for col in TRADE_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[TRADE_COLUMNS]
    except Exception as e:
        st.warning("Could not load trades: {}".format(e))
        return pd.DataFrame(columns=TRADE_COLUMNS)


def _save_trades(df: pd.DataFrame) -> None:
    """Save full trades DataFrame back to Google Sheets."""
    load_trades.clear()
    if not _is_cloud():
        st.session_state.trades_df = df.copy()
        return
    try:
        ws = _get_sheet("Trades")
        ws.clear()
        ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())
    except Exception as e:
        st.error("Could not save trade: {}".format(e))


def add_trade(
    symbol: str, option_type: str, strike: int, expiry: str,
    entry_price: float, exit_price: float, lots: int, lot_size: int,
    entry_rsi: float = 0.0, entry_adx: float = 0.0,
    supertrend: str = "", dashboard_said: str = "",
    hold_time: str = "", lessons: str = "", notes: str = "",
    brokerage: float = DEFAULT_BROKERAGE,
) -> dict:
    now      = datetime.now()
    capital  = round(entry_price * lots * lot_size, 2)
    gross    = round((exit_price - entry_price) * lots * lot_size, 2) if exit_price > 0 else 0.0
    stt      = round(exit_price * lots * lot_size * DEFAULT_STT_PCT / 100, 2) if exit_price > 0 else 0.0
    other    = DEFAULT_OTHER if exit_price > 0 else 0.0
    net      = round(gross - brokerage - stt - other, 2) if exit_price > 0 else 0.0
    result   = "OPEN" if exit_price <= 0 else ("WIN" if net >= 0 else "LOSS")
    df       = load_trades()
    trade_num = 1 if df.empty else (pd.to_numeric(df["Trade #"], errors="coerce").max() + 1)

    row = {
        "Trade #":         int(trade_num),
        "Date":            now.strftime("%Y-%m-%d"),
        "Time":            now.strftime("%H:%M"),
        "Symbol":          symbol,
        "Option Type":     option_type,
        "Strike":          strike,
        "Expiry":          expiry,
        "Entry Price":     entry_price,
        "Exit Price":      exit_price if exit_price > 0 else "",
        "Lots":            lots,
        "Lot Size":        lot_size,
        "Capital Used":    capital,
        "Gross P&L":       gross      if exit_price > 0 else "",
        "Brokerage":       brokerage  if exit_price > 0 else "",
        "STT":             stt        if exit_price > 0 else "",
        "Other Charges":   other      if exit_price > 0 else "",
        "Net P&L":         net        if exit_price > 0 else "",
        "Result":          result,
        "Hold Time":       hold_time,
        "Entry RSI":       round(entry_rsi, 1) if entry_rsi else "",
        "Entry ADX":       round(entry_adx, 1) if entry_adx else "",
        "Supertrend":      supertrend,
        "Dashboard Said":  dashboard_said,
        "Lessons Learned": lessons,
        "Notes":           notes,
    }
    new_df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    _save_trades(new_df)
    return row


# ── Capital ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def load_capital_history() -> pd.DataFrame:
    """Load capital history from Google Sheets."""
    if not _is_cloud():
        if "capital_df" not in st.session_state:
            st.session_state.capital_df = pd.DataFrame([
                {"Date": "2026-10-01", "Balance": 40000.0, "Note": "Initial capital"},
                {"Date": "2026-10-01", "Balance": 32660.0, "Note": "After Trade #1 loss"},
            ])
        return st.session_state.capital_df.copy()
    try:
        ws   = _get_sheet("Capital")
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=CAPITAL_COLUMNS)
        return pd.DataFrame(data)[CAPITAL_COLUMNS]
    except Exception as e:
        st.warning("Could not load capital: {}".format(e))
        return pd.DataFrame(columns=CAPITAL_COLUMNS)


def _save_capital(df: pd.DataFrame) -> None:
    load_capital_history.clear()
    if not _is_cloud():
        st.session_state.capital_df = df.copy()
        return
    try:
        ws = _get_sheet("Capital")
        ws.clear()
        ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())
    except Exception as e:
        st.error("Could not save capital: {}".format(e))


def update_capital(new_balance: float, note: str = "") -> None:
    df  = load_capital_history()
    row = pd.DataFrame([{
        "Date":    datetime.now().strftime("%Y-%m-%d"),
        "Balance": round(new_balance, 2),
        "Note":    note or "Manual update",
    }])
    _save_capital(pd.concat([df, row], ignore_index=True))


def get_capital_stats() -> dict:
    df = load_capital_history()
    if df.empty:
        return {"initial": 40000.0, "current": 40000.0, "pnl": 0.0,
                "pnl_pct": 0.0, "days": 0, "history": []}
    df["Balance"] = pd.to_numeric(df["Balance"], errors="coerce")
    initial = float(df["Balance"].iloc[0])
    current = float(df["Balance"].iloc[-1])
    pnl     = round(current - initial, 2)
    pct     = round((pnl / initial) * 100, 2) if initial else 0.0
    try:
        start = datetime.strptime(str(df["Date"].iloc[0]), "%Y-%m-%d")
        days  = (datetime.now() - start).days
    except Exception:
        days = 0
    return {
        "initial": initial, "current": current,
        "pnl": pnl, "pnl_pct": pct, "days": days,
        "history": df.to_dict("records"),
    }


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_stats(df: pd.DataFrame = None) -> dict:
    if df is None:
        df = load_trades()
    closed = df[df["Result"].isin(["WIN", "LOSS"])].copy()
    empty  = {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
              "total_pnl": 0.0, "best_trade": 0.0, "worst_trade": 0.0,
              "avg_win": 0.0, "avg_loss": 0.0, "reward_risk": 0.0,
              "max_drawdown": 0.0, "total_invested": 0.0,
              "total_brokerage": 0.0, "total_charges": 0.0}
    if closed.empty:
        return empty
    pnl   = pd.to_numeric(closed["Net P&L"],      errors="coerce").fillna(0)
    brok  = pd.to_numeric(closed["Brokerage"],     errors="coerce").fillna(0)
    stt   = pd.to_numeric(closed["STT"],           errors="coerce").fillna(0)
    other = pd.to_numeric(closed["Other Charges"], errors="coerce").fillna(0)
    cap   = pd.to_numeric(closed["Capital Used"],  errors="coerce").fillna(0)
    wins  = closed[closed["Result"] == "WIN"]
    losses= closed[closed["Result"] == "LOSS"]
    equity= pnl.cumsum(); dd = (equity - equity.cummax()).min()
    aw = pd.to_numeric(wins["Net P&L"],   errors="coerce").mean() if not wins.empty   else 0.0
    al = pd.to_numeric(losses["Net P&L"], errors="coerce").mean() if not losses.empty else 0.0
    rr = round(aw / abs(al), 2) if al and al != 0 else 0.0
    return {
        "total_trades":    len(closed),
        "wins":            len(wins),
        "losses":          len(losses),
        "win_rate":        round(len(wins) / len(closed) * 100, 1),
        "total_pnl":       round(pnl.sum(), 2),
        "best_trade":      round(pnl.max(), 2),
        "worst_trade":     round(pnl.min(), 2),
        "avg_win":         round(aw, 2),
        "avg_loss":        round(al, 2),
        "reward_risk":     rr,
        "max_drawdown":    round(dd, 2),
        "total_invested":  round(cap.sum(), 2),
        "total_brokerage": round(brok.sum(), 2),
        "total_charges":   round((brok + stt + other).sum(), 2),
    }


# ── Excel export (in-memory, for download button) ─────────────────────────────

def build_excel_report(df: pd.DataFrame) -> bytes:
    from io import BytesIO
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Trades", index=False)
        # Monthly summary
        closed = df[df["Result"].isin(["WIN", "LOSS"])].copy()
        if not closed.empty:
            closed["Month"] = pd.to_datetime(closed["Date"], errors="coerce").dt.strftime("%b %Y")
            monthly = closed.groupby("Month").agg(
                Trades=("Net P&L", "count"),
                Wins=("Result", lambda x: (x == "WIN").sum()),
                Net_PnL=("Net P&L", lambda x: pd.to_numeric(x, errors="coerce").sum()),
            ).reset_index().rename(columns={"Net_PnL": "Net P&L"})
            monthly["Win Rate %"] = round(monthly["Wins"] / monthly["Trades"] * 100, 1)
            monthly.to_excel(writer, sheet_name="Monthly Summary", index=False)
        # Performance
        stats = get_stats(df)
        perf  = pd.DataFrame([{"Metric": k, "Value": v} for k, v in stats.items()])
        perf.to_excel(writer, sheet_name="Performance", index=False)
    return buf.getvalue()
