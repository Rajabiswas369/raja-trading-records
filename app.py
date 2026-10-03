"""
Trading Management System — raja-trading-records
=================================================
Purpose: Manage your trading BUSINESS — not signals.

Pages:
  🏠 Command Centre     — Daily snapshot: target, risk, rules score
  📓 Log Trade          — Record every trade
  🔄 Angel One Sync     — Auto-fetch today's trades
  💰 Capital Manager    — Track capital, deposits, withdrawals
  🎯 Weekly Targets     — Set weekly/monthly profit targets
  📊 Performance Hub    — Win rate, RR, signal accuracy, best days
  📔 Trade Diary        — Emotional journal after every trade
  ✅ Rules Checker      — Did you follow all rules today?
  🏆 Streak Tracker     — Win/loss streaks, consistency score
  📅 Monthly P&L        — Full P&L statement
  💸 Expenses           — Brokerage, STT, charges breakdown
  ⬇️  Export            — Download your data
"""

import json
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Trading Management System",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═════════════════════════════════════════════════════════════════════════════
COLUMNS = [
    "Trade #", "Date", "Time", "Symbol", "Option Type", "Strike", "Expiry",
    "Entry Price", "Exit Price", "Lots", "Lot Size", "Capital Used",
    "Gross P&L", "Brokerage", "STT", "Other Charges", "Net P&L", "Result",
    "Hold Time", "Entry RSI", "Entry ADX", "Supertrend", "Dashboard Said",
    "Lessons Learned", "Notes",
]
DEFAULT_BROKERAGE = 40.0
DEFAULT_STT_PCT   = 0.05
DEFAULT_OTHER     = 15.0

TRADING_RULES = [
    "Checked RSI between 35–65 (not extreme)",
    "ADX > 25 (strong trend confirmed)",
    "Supertrend confirms direction",
    "Price on correct side of VWAP",
    "Set SL order in broker app BEFORE buying",
    "Trading ATM strike (not deep OTM)",
    "Expiry is 3+ days away",
    "No major news/event in next 1 hour",
    "Lot size within my 2% capital risk limit",
    "Traded in Prime window (10:30 AM – 2:30 PM)",
]

# ═════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS HELPERS
# ═════════════════════════════════════════════════════════════════════════════
def _get_conn():
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            from streamlit_gsheets import GSheetsConnection
            return st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        pass
    return None


@st.cache_data(ttl=5, show_spinner=False)
def load_trades() -> pd.DataFrame:
    conn = _get_conn()
    if conn:
        try:
            df = conn.read(worksheet="Trades", ttl="0s")
            if df is not None and not df.empty:
                for col in COLUMNS:
                    if col not in df.columns:
                        df[col] = ""
                return df[COLUMNS]
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNS)


@st.cache_data(ttl=5, show_spinner=False)
def load_capital() -> dict:
    conn = _get_conn()
    if conn:
        try:
            cdf = conn.read(worksheet="Capital", ttl="0s")
            if cdf is not None and not cdf.empty:
                row      = cdf.iloc[0].to_dict()
                hist_raw = row.get("history_json", "[]")
                history  = json.loads(hist_raw) if isinstance(hist_raw, str) else []
                return {
                    "initial_capital": float(row.get("initial_capital", 40000.0)),
                    "current_capital": float(row.get("current_capital", 40000.0)),
                    "start_date":      str(row.get("start_date",      "2025-01-01")),
                    "notes":           str(row.get("notes",           "")),
                    "history":         history,
                    "weekly_target":   float(row.get("weekly_target",  2000.0)),
                    "daily_loss_limit":float(row.get("daily_loss_limit", 1000.0)),
                    "monthly_target":  float(row.get("monthly_target", 8000.0)),
                }
        except Exception:
            pass
    return {
        "initial_capital": 40000.0, "current_capital": 40000.0,
        "start_date": "2025-01-01", "notes": "",
        "history": [{"date":"2025-01-01","balance":40000.0,"note":"Initial capital"}],
        "weekly_target": 2000.0, "daily_loss_limit": 1000.0, "monthly_target": 8000.0,
    }


def save_trades(df: pd.DataFrame):
    conn = _get_conn()
    if conn:
        try:
            conn.update(worksheet="Trades", data=df)
            st.cache_data.clear()
        except Exception as e:
            st.error("Could not save: {}".format(e))


def save_capital(data: dict):
    conn = _get_conn()
    if conn:
        try:
            conn.update(worksheet="Capital", data=pd.DataFrame([{
                "initial_capital":  data.get("initial_capital",  40000.0),
                "current_capital":  data.get("current_capital",  40000.0),
                "start_date":       data.get("start_date",       "2025-01-01"),
                "notes":            data.get("notes",            ""),
                "history_json":     json.dumps(data.get("history", [])),
                "weekly_target":    data.get("weekly_target",    2000.0),
                "daily_loss_limit": data.get("daily_loss_limit", 1000.0),
                "monthly_target":   data.get("monthly_target",   8000.0),
            }]))
            st.cache_data.clear()
        except Exception as e:
            st.error("Could not save capital: {}".format(e))


# ═════════════════════════════════════════════════════════════════════════════
# STATS HELPERS
# ═════════════════════════════════════════════════════════════════════════════
def get_stats(df: pd.DataFrame) -> dict:
    closed = df[df["Result"].isin(["WIN","LOSS"])].copy()
    if closed.empty:
        return {k:0 for k in ["total_trades","wins","losses","win_rate","total_pnl",
                               "best_trade","worst_trade","avg_win","avg_loss",
                               "reward_risk","max_drawdown","total_brokerage","total_charges"]}
    pnl   = pd.to_numeric(closed["Net P&L"],      errors="coerce").fillna(0)
    brok  = pd.to_numeric(closed["Brokerage"],     errors="coerce").fillna(0)
    stt   = pd.to_numeric(closed["STT"],           errors="coerce").fillna(0)
    other = pd.to_numeric(closed["Other Charges"], errors="coerce").fillna(0)
    wins  = closed[closed["Result"]=="WIN"]
    losses= closed[closed["Result"]=="LOSS"]
    eq    = pnl.cumsum(); dd = (eq - eq.cummax()).min()
    aw    = pd.to_numeric(wins["Net P&L"],   errors="coerce").mean() if not wins.empty   else 0.0
    al    = pd.to_numeric(losses["Net P&L"], errors="coerce").mean() if not losses.empty else 0.0
    return {
        "total_trades": len(closed), "wins": len(wins), "losses": len(losses),
        "win_rate":     round(len(wins)/len(closed)*100,1),
        "total_pnl":    round(pnl.sum(),2),
        "best_trade":   round(pnl.max(),2), "worst_trade": round(pnl.min(),2),
        "avg_win":      round(aw,2),        "avg_loss":    round(al,2),
        "reward_risk":  round(aw/abs(al),2) if al and al!=0 else 0.0,
        "max_drawdown": round(dd,2),
        "total_brokerage": round(brok.sum(),2),
        "total_charges":   round((brok+stt+other).sum(),2),
    }


def pnl_delta(val):
    return (("▲ Rs {:,.0f}".format(val) if val>=0 else "▼ Rs {:,.0f}".format(abs(val))),
            ("normal" if val>=0 else "inverse"))


def _next_trade_num(df):
    if df.empty or df["Trade #"].isna().all(): return 1
    return int(pd.to_numeric(df["Trade #"], errors="coerce").max()) + 1


def get_week_pnl(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    try:
        closed = df[df["Result"].isin(["WIN","LOSS"])].copy()
        closed["_d"] = pd.to_datetime(closed["Date"], errors="coerce").dt.date
        week_trades = closed[closed["_d"] >= week_start]
        return round(pd.to_numeric(week_trades["Net P&L"], errors="coerce").sum(), 2)
    except Exception:
        return 0.0


def get_today_pnl(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    today_str = date.today().strftime("%Y-%m-%d")
    try:
        closed = df[df["Result"].isin(["WIN","LOSS"])].copy()
        today_trades = closed[closed["Date"].astype(str) == today_str]
        return round(pd.to_numeric(today_trades["Net P&L"], errors="coerce").sum(), 2)
    except Exception:
        return 0.0


def get_month_pnl(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    try:
        closed = df[df["Result"].isin(["WIN","LOSS"])].copy()
        closed["_m"] = pd.to_datetime(closed["Date"], errors="coerce").dt.to_period("M")
        this_month = str(pd.Timestamp.now().to_period("M"))
        return round(pd.to_numeric(
            closed[closed["_m"].astype(str)==this_month]["Net P&L"],
            errors="coerce").sum(), 2)
    except Exception:
        return 0.0


def get_streak(df: pd.DataFrame) -> dict:
    closed = df[df["Result"].isin(["WIN","LOSS"])].copy()
    if closed.empty: return {"current":0,"type":"—","longest_win":0,"longest_loss":0}
    results = closed.sort_values("Trade #")["Result"].tolist()
    current = 1; ctype = results[-1]
    for i in range(len(results)-2,-1,-1):
        if results[i] == ctype: current += 1
        else: break
    wins=[]; losses=[]; wc=0; lc=0
    for r in results:
        if r=="WIN": wc+=1; lc=0
        else: lc+=1; wc=0
        wins.append(wc); losses.append(lc)
    return {"current":current,"type":ctype,
            "longest_win":max(wins) if wins else 0,
            "longest_loss":max(losses) if losses else 0}


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
st.sidebar.image("https://img.icons8.com/color/96/combo-chart.png", width=56)
st.sidebar.title("Trading Management")
st.sidebar.markdown("---")

page = st.sidebar.radio("📂 Navigate", [
    "🏠 Command Centre",
    "📓 Log Trade",
    "🔄 Angel One Sync",
    "💰 Capital Manager",
    "🎯 Weekly Targets",
    "📊 Performance Hub",
    "📔 Trade Diary",
    "✅ Rules Checker",
    "🏆 Streak Tracker",
    "📅 Monthly P&L",
    "💸 Expenses",
    "⬇️ Export",
])
st.sidebar.markdown("---")

conn_ok = _get_conn() is not None
if conn_ok:
    st.sidebar.success("☁️ Google Sheets **Connected**")
else:
    st.sidebar.warning("⚠️ Sheets not connected — add secrets")

# ═════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═════════════════════════════════════════════════════════════════════════════
df        = load_trades()
cap_data  = load_capital()
stats     = get_stats(df)
closed_df = df[df["Result"].isin(["WIN","LOSS"])].copy() if not df.empty else pd.DataFrame()
today_pnl = get_today_pnl(df)
week_pnl  = get_week_pnl(df)
month_pnl = get_month_pnl(df)
streak    = get_streak(df)
initial   = cap_data.get("initial_capital", 40000.0)
current   = cap_data.get("current_capital", 40000.0)
w_target  = cap_data.get("weekly_target",   2000.0)
d_limit   = cap_data.get("daily_loss_limit",1000.0)
m_target  = cap_data.get("monthly_target",  8000.0)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 🏠 COMMAND CENTRE
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Command Centre":
    st.title("🏠 Trading Command Centre")
    st.caption("Your complete trading business snapshot — updated live.")
    st.markdown("---")

    # ── Risk status banner ────────────────────────────────────────────────────
    if today_pnl <= -d_limit:
        st.error("🚨 **DAILY LOSS LIMIT HIT** — Rs {:,.0f} lost today. STOP TRADING for today.".format(abs(today_pnl)))
    elif week_pnl >= w_target:
        st.success("🎉 **WEEKLY TARGET ACHIEVED!** — Rs {:,.0f} profit this week. Consider stopping or trade very carefully.".format(week_pnl))
    elif today_pnl < 0:
        remaining_limit = d_limit + today_pnl
        st.warning("⚠️ Today: Rs {:,.0f} loss. Rs {:,.0f} remaining before daily limit.".format(abs(today_pnl), remaining_limit))
    else:
        st.success("✅ Trading day looks good. Stay disciplined.")

    # ── Key metrics ───────────────────────────────────────────────────────────
    c1,c2,c3,c4,c5 = st.columns(5)
    td, tdc = pnl_delta(today_pnl)
    wd, wdc = pnl_delta(week_pnl)
    md, mdc = pnl_delta(month_pnl)
    c1.metric("📅 Today P&L",    "Rs {:,.0f}".format(today_pnl),  td, delta_color=tdc)
    c2.metric("📆 This Week",    "Rs {:,.0f}".format(week_pnl),   wd, delta_color=wdc)
    c3.metric("🗓️ This Month",   "Rs {:,.0f}".format(month_pnl),  md, delta_color=mdc)
    c4.metric("💰 Capital",      "Rs {:,.0f}".format(current),
              "{:+.1f}%".format((current-initial)/initial*100) if initial else "0%")
    c5.metric("🏆 Streak",       "{} {}".format(streak["current"], streak["type"]),
              "Current run")
    st.markdown("---")

    # ── Target progress ───────────────────────────────────────────────────────
    st.subheader("🎯 Target Progress This Week")
    w_pct = min(int(week_pnl / w_target * 100), 100) if w_target > 0 else 0
    w_pct = max(w_pct, 0)
    color = "🟢" if w_pct >= 100 else ("🟡" if w_pct >= 50 else "🔴")
    st.progress(w_pct, text="{} Weekly: Rs {:,.0f} / Rs {:,.0f} ({:.0f}%)".format(
        color, week_pnl, w_target, w_pct))

    m_pct = min(int(month_pnl / m_target * 100), 100) if m_target > 0 else 0
    m_pct = max(m_pct, 0)
    color2 = "🟢" if m_pct >= 100 else ("🟡" if m_pct >= 50 else "🔴")
    st.progress(m_pct, text="{} Monthly: Rs {:,.0f} / Rs {:,.0f} ({:.0f}%)".format(
        color2, month_pnl, m_target, m_pct))

    d_used = min(int(abs(today_pnl) / d_limit * 100), 100) if today_pnl < 0 and d_limit > 0 else 0
    d_col  = "🔴" if d_used >= 80 else ("🟡" if d_used >= 50 else "🟢")
    st.progress(d_used, text="{} Daily Risk: Rs {:,.0f} used of Rs {:,.0f} limit ({:.0f}%)".format(
        d_col, abs(min(today_pnl,0)), d_limit, d_used))
    st.markdown("---")

    # ── Quick stats ───────────────────────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total Trades",  stats["total_trades"])
    k2.metric("Win Rate",      "{:.1f}%".format(stats["win_rate"]))
    k3.metric("Reward:Risk",   "{:.2f}x".format(stats["reward_risk"]),
              "Good ✅" if stats["reward_risk"] >= 1.5 else "Improve ⚠️")
    k4.metric("Max Drawdown",  "Rs {:,.0f}".format(abs(stats["max_drawdown"])))
    st.markdown("---")

    # ── Last 5 trades ─────────────────────────────────────────────────────────
    if not closed_df.empty:
        st.subheader("🕐 Last 5 Trades")
        rc = ["Trade #","Date","Symbol","Option Type","Strike","Entry Price","Exit Price","Net P&L","Result"]
        st.dataframe(df[rc].tail(5).sort_index(ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet. Use **📓 Log Trade** to record your first trade.")


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📓 LOG TRADE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📓 Log Trade":
    st.title("📓 Log a Trade")
    st.caption("Every trade saved permanently to Google Sheets ☁️")
    st.markdown("---")
    with st.form("trade_form", clear_on_submit=True):
        st.subheader("Trade Details")
        c1,c2,c3,c4 = st.columns(4)
        f_sym    = c1.text_input("Symbol",    value="NIFTY50")
        f_type   = c2.selectbox("PUT / CALL", ["PUT","CALL"])
        f_strike = c3.number_input("Strike",  value=22500, step=50)
        f_expiry = c4.text_input("Expiry",    placeholder="e.g. 06 Jun 2025")
        c5,c6,c7,c8 = st.columns(4)
        f_entry   = c5.number_input("Entry Price (Rs)",         value=0.0, step=0.5, format="%.2f")
        f_exit    = c6.number_input("Exit Price (Rs) — 0=OPEN", value=0.0, step=0.5, format="%.2f")
        f_lots    = c7.number_input("Lots",    value=1, step=1, min_value=1)
        f_lotsize = c8.number_input("Lot Size",value=75, step=1, min_value=1)
        st.subheader("Market Conditions at Entry")
        m1,m2,m3,m4 = st.columns(4)
        f_rsi   = m1.number_input("RSI at Entry", value=50.0, step=0.1, format="%.1f")
        f_adx   = m2.number_input("ADX at Entry", value=25.0, step=0.1, format="%.1f")
        f_st    = m3.selectbox("Supertrend", ["BEARISH","BULLISH"])
        f_dsaid = m4.selectbox("Dashboard Said", ["WAIT","PUT","CALL"])
        st.subheader("Notes & Learning")
        n1,n2 = st.columns(2)
        f_hold    = n1.text_input("Hold Time",        placeholder="e.g. 45 min")
        f_lessons = n2.text_input("Lessons Learned",  placeholder="e.g. Never enter RSI < 35")
        f_notes   = st.text_area("Additional Notes",  placeholder="What did you observe?", height=60)
        ch1,_,ch3 = st.columns(3)
        f_brok  = ch1.number_input("Brokerage (Rs)",    value=DEFAULT_BROKERAGE, step=1.0)
        f_other = ch3.number_input("Other Charges (Rs)",value=DEFAULT_OTHER, step=1.0)
        submitted = st.form_submit_button("💾 Save Trade to Cloud", use_container_width=True)
    if submitted:
        if f_entry <= 0:
            st.error("Entry Price must be > 0.")
        else:
            now = datetime.now()
            capital = round(f_entry * f_lots * f_lotsize, 2)
            gross   = round((f_exit-f_entry)*f_lots*f_lotsize,2) if f_exit>0 else 0.0
            stt     = round(f_exit*f_lots*f_lotsize*DEFAULT_STT_PCT/100,2) if f_exit>0 else 0.0
            other_c = DEFAULT_OTHER if f_exit>0 else 0.0
            net     = round(gross-f_brok-stt-other_c,2) if f_exit>0 else 0.0
            result  = "OPEN" if f_exit<=0 else ("WIN" if net>=0 else "LOSS")
            row = {
                "Trade #":_next_trade_num(df),"Date":now.strftime("%Y-%m-%d"),
                "Time":now.strftime("%H:%M"),"Symbol":f_sym,"Option Type":f_type,
                "Strike":int(f_strike),"Expiry":f_expiry,"Entry Price":f_entry,
                "Exit Price":f_exit if f_exit>0 else "","Lots":int(f_lots),
                "Lot Size":int(f_lotsize),"Capital Used":capital,
                "Gross P&L":gross if f_exit>0 else "","Brokerage":f_brok if f_exit>0 else "",
                "STT":stt if f_exit>0 else "","Other Charges":other_c if f_exit>0 else "",
                "Net P&L":net if f_exit>0 else "","Result":result,
                "Hold Time":f_hold,"Entry RSI":round(f_rsi,1) if f_rsi else "",
                "Entry ADX":round(f_adx,1) if f_adx else "","Supertrend":f_st,
                "Dashboard Said":f_dsaid,"Lessons Learned":f_lessons,"Notes":f_notes,
            }
            save_trades(pd.concat([df, pd.DataFrame([row])], ignore_index=True))
            emoji = "✅ WIN" if result=="WIN" else ("❌ LOSS" if result=="LOSS" else "📂 OPEN")
            st.success("Trade #{} saved! {} | Net P&L: {}".format(
                row["Trade #"], emoji, "Rs {:,.0f}".format(net) if f_exit>0 else "Open"))
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 🔄 ANGEL ONE SYNC
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔄 Angel One Sync":
    st.title("🔄 Angel One Auto-Sync")
    st.caption("Fetch today's executed trades automatically — no typing needed!")
    st.markdown("---")
    try:
        from angel_sync import render_angel_sync_panel
        render_angel_sync_panel(load_fn=load_trades, save_fn=save_trades, columns=COLUMNS)
    except Exception as e:
        st.error("Angel Sync module error: {}".format(e))


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 💰 CAPITAL MANAGER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💰 Capital Manager":
    st.title("💰 Capital Manager")
    st.caption("Track your trading capital, deposits, withdrawals, and growth.")
    st.markdown("---")
    remaining_pct = (current/initial*100) if initial else 0
    cap_d, cap_dc = pnl_delta(current-initial)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💰 Initial",  "Rs {:,.0f}".format(initial))
    c2.metric("💵 Current",  "Rs {:,.0f}".format(current), cap_d, delta_color=cap_dc)
    c3.metric("📊 Growth",   "{:+.2f}%".format((current-initial)/initial*100) if initial else "0%")
    c4.metric("📅 Days",     "{} days".format((datetime.now()-datetime.strptime(cap_data.get("start_date","2025-01-01"),"%Y-%m-%d")).days))
    prog_c = "🟢" if remaining_pct>=80 else ("🟡" if remaining_pct>=60 else "🔴")
    st.progress(min(int(remaining_pct),100),
                text="{} Rs {:,.0f} of Rs {:,.0f} remaining ({:.1f}%)".format(
                    prog_c, current, initial, remaining_pct))
    st.markdown("---")
    with st.expander("⚙️ Update Capital & Targets", expanded=False):
        with st.form("cap_form"):
            r1c1,r1c2,r1c3 = st.columns(3)
            ni = r1c1.number_input("Initial Capital (Rs)", value=float(initial), step=1000.0, format="%.0f")
            nc = r1c2.number_input("Current Balance (Rs)", value=float(current), step=100.0,  format="%.0f")
            ns = r1c3.text_input("Start Date", value=cap_data.get("start_date","2025-01-01"))
            r2c1,r2c2,r2c3 = st.columns(3)
            wt = r2c1.number_input("Weekly Target (Rs)",    value=float(w_target),  step=500.0,  format="%.0f")
            dl = r2c2.number_input("Daily Loss Limit (Rs)", value=float(d_limit),   step=100.0,  format="%.0f")
            mt = r2c3.number_input("Monthly Target (Rs)",   value=float(m_target),  step=1000.0, format="%.0f")
            nn = st.text_input("Note", placeholder="e.g. Added Rs 10,000 top-up")
            if st.form_submit_button("💾 Save"):
                cap_data.update({"initial_capital":ni,"current_capital":round(nc,2),
                                 "start_date":ns,"weekly_target":wt,
                                 "daily_loss_limit":dl,"monthly_target":mt})
                cap_data.setdefault("history",[]).append({
                    "date":datetime.now().strftime("%Y-%m-%d"),
                    "balance":round(nc,2),
                    "note":nn if nn else "Manual update"})
                save_capital(cap_data)
                st.success("Saved! Balance: Rs {:,.0f}".format(nc))
                st.rerun()
    history = cap_data.get("history",[])
    if history:
        hdf = pd.DataFrame(history)
        hdf["date"]    = pd.to_datetime(hdf["date"],errors="coerce")
        hdf["balance"] = pd.to_numeric(hdf["balance"],errors="coerce")
        hdf = hdf.sort_values("date").reset_index(drop=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hdf["date"],y=hdf["balance"],mode="lines+markers",
                                  line=dict(color="#3498db",width=2.5),fill="tozeroy",
                                  fillcolor="rgba(52,152,219,0.08)",
                                  hovertemplate="%{x|%d %b %Y}<br>Rs %{y:,.0f}<extra></extra>"))
        fig.add_hline(y=initial,line_dash="dash",line_color="rgba(255,255,255,0.4)",
                      annotation_text="Initial: Rs {:,.0f}".format(initial))
        fig.update_layout(template="plotly_dark",height=320,title="💵 Capital Over Time",
                          margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(hdf[["date","balance","note"]].rename(
            columns={"date":"Date","balance":"Balance (Rs)","note":"Note"}
        ).sort_values("Date",ascending=False), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 🎯 WEEKLY TARGETS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Weekly Targets":
    st.title("🎯 Weekly & Monthly Target Tracker")
    st.markdown("---")
    c1,c2,c3 = st.columns(3)
    c1.metric("📆 This Week",   "Rs {:,.0f}".format(week_pnl),
              "Target: Rs {:,.0f}".format(w_target))
    c2.metric("🗓️ This Month",  "Rs {:,.0f}".format(month_pnl),
              "Target: Rs {:,.0f}".format(m_target))
    c3.metric("📅 Today",       "Rs {:,.0f}".format(today_pnl),
              "Limit: Rs {:,.0f}".format(d_limit))
    st.markdown("---")

    # Weekly progress
    w_pct = max(0, min(int(week_pnl/w_target*100) if w_target>0 else 0, 100))
    w_col = "🟢" if w_pct>=100 else ("🟡" if w_pct>=50 else "🔴")
    st.subheader("📆 Weekly Target")
    st.progress(w_pct, text="{} Rs {:,.0f} earned / Rs {:,.0f} target ({:.0f}%)".format(
        w_col, week_pnl, w_target, w_pct))
    if week_pnl >= w_target:
        st.success("🎉 Weekly target achieved! Great discipline — consider stopping or reducing size.")
    elif week_pnl < 0:
        st.error("📉 Negative week so far. Focus on small wins. Don't revenge trade.")
    else:
        st.info("Rs {:,.0f} more needed to hit weekly target.".format(w_target - week_pnl))

    st.markdown("---")

    # Monthly progress
    m_pct = max(0, min(int(month_pnl/m_target*100) if m_target>0 else 0, 100))
    m_col = "🟢" if m_pct>=100 else ("🟡" if m_pct>=50 else "🔴")
    st.subheader("🗓️ Monthly Target")
    st.progress(m_pct, text="{} Rs {:,.0f} earned / Rs {:,.0f} target ({:.0f}%)".format(
        m_col, month_pnl, m_target, m_pct))
    st.markdown("---")

    # Daily loss limit
    d_used_pct = max(0,min(int(abs(today_pnl)/d_limit*100) if today_pnl<0 and d_limit>0 else 0,100))
    d_col2 = "🔴" if d_used_pct>=80 else ("🟡" if d_used_pct>=50 else "🟢")
    st.subheader("🛑 Daily Loss Limit")
    st.progress(d_used_pct, text="{} Rs {:,.0f} lost today / Rs {:,.0f} limit ({:.0f}%)".format(
        d_col2, abs(min(today_pnl,0)), d_limit, d_used_pct))
    if d_used_pct >= 100:
        st.error("🚨 STOP! Daily loss limit hit. No more trades today.")
    elif d_used_pct >= 80:
        st.warning("⚠️ Close to daily limit. One more bad trade = stop for today.")

    # Weekly history chart
    if not closed_df.empty:
        st.markdown("---")
        st.subheader("📊 Weekly P&L History")
        try:
            closed_df["_week"] = pd.to_datetime(closed_df["Date"],errors="coerce").dt.to_period("W")
            weekly = closed_df.groupby("_week")["Net P&L"].apply(
                lambda x: pd.to_numeric(x,errors="coerce").sum()).reset_index()
            weekly["_week"] = weekly["_week"].astype(str)
            bar_colors = ["#26a69a" if v>=0 else "#ef5350" for v in weekly["Net P&L"]]
            fig = go.Figure(go.Bar(x=weekly["_week"],y=weekly["Net P&L"],
                                   marker_color=bar_colors,
                                   text=["Rs {:,.0f}".format(v) for v in weekly["Net P&L"]],
                                   textposition="outside"))
            fig.add_hline(y=w_target,line_dash="dash",line_color="#f39c12",
                          annotation_text="Weekly Target")
            fig.update_layout(template="plotly_dark",height=300,
                               title="Weekly P&L vs Target",margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Not enough data for weekly chart yet.")


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📊 PERFORMANCE HUB
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Performance Hub":
    st.title("📊 Performance Hub")
    st.markdown("---")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        r1,r2,r3,r4 = st.columns(4)
        r1.metric("Win Rate",    "{:.1f}%".format(stats["win_rate"]))
        r2.metric("Reward:Risk", "{:.2f}x".format(stats["reward_risk"]))
        r3.metric("Avg Win",     "Rs {:,.0f}".format(stats["avg_win"]))
        r4.metric("Avg Loss",    "Rs {:,.0f}".format(abs(stats["avg_loss"])))
        st.markdown("---")

        tab1,tab2,tab3,tab4 = st.tabs(["🎯 Signal Accuracy","📅 Best Day","PUT vs CALL","By Symbol"])

        with tab1:
            st.subheader("🎯 Was the Dashboard Right for YOUR Trades?")
            if "Dashboard Said" in closed_df.columns:
                sig = closed_df.groupby("Dashboard Said").apply(lambda g: pd.Series({
                    "Trades":    len(g),
                    "Wins":      (g["Result"]=="WIN").sum(),
                    "Losses":    (g["Result"]=="LOSS").sum(),
                    "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100,1),
                    "Net P&L":   pd.to_numeric(g["Net P&L"],errors="coerce").sum().round(0),
                })).reset_index()
                st.dataframe(sig, use_container_width=True, hide_index=True)
                best = sig.loc[sig["Win Rate %"].idxmax()] if not sig.empty else None
                if best is not None:
                    st.success("✅ Best signal: **{}** — {:.0f}% win rate on {} trades".format(
                        best["Dashboard Said"], best["Win Rate %"], best["Trades"]))
            else:
                st.info("Log trades with 'Dashboard Said' field to see signal accuracy.")

        with tab2:
            st.subheader("📅 Which Day of Week You Perform Best")
            try:
                closed_df["_dow"] = pd.to_datetime(closed_df["Date"],errors="coerce").dt.day_name()
                dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
                dg = closed_df.groupby("_dow").apply(lambda g: pd.Series({
                    "Trades":    len(g),
                    "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100,1),
                    "Net P&L":   pd.to_numeric(g["Net P&L"],errors="coerce").sum().round(0),
                })).reset_index().rename(columns={"_dow":"Day"})
                dg["Day"] = pd.Categorical(dg["Day"],categories=dow_order,ordered=True)
                dg = dg.sort_values("Day")
                bar_colors = ["#26a69a" if v>=0 else "#ef5350" for v in dg["Net P&L"]]
                fig = go.Figure(go.Bar(x=dg["Day"],y=dg["Net P&L"],marker_color=bar_colors,
                                       text=["Rs {:,.0f}".format(v) for v in dg["Net P&L"]],
                                       textposition="outside"))
                fig.update_layout(template="plotly_dark",height=280,
                                   title="P&L by Day of Week",margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(dg, use_container_width=True, hide_index=True)
            except Exception:
                st.info("Not enough data yet.")

        with tab3:
            tg = closed_df.groupby("Option Type").apply(lambda g: pd.Series({
                "Trades":    len(g),
                "Wins":      (g["Result"]=="WIN").sum(),
                "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100,1),
                "Net P&L":   pd.to_numeric(g["Net P&L"],errors="coerce").sum().round(0),
            })).reset_index()
            st.dataframe(tg, use_container_width=True, hide_index=True)

        with tab4:
            sg = closed_df.groupby("Symbol").apply(lambda g: pd.Series({
                "Trades":    len(g),
                "Wins":      (g["Result"]=="WIN").sum(),
                "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100,1),
                "Net P&L":   pd.to_numeric(g["Net P&L"],errors="coerce").sum().round(0),
            })).reset_index()
            st.dataframe(sg, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📔 TRADE DIARY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📔 Trade Diary":
    st.title("📔 Trade Diary")
    st.caption("Write after every trading session. This is where real improvement happens.")
    st.markdown("---")
    st.info("Professional traders review every trade. It takes 5 minutes and is the #1 habit that separates consistent traders from gamblers.")

    with st.form("diary_form", clear_on_submit=True):
        d1,d2 = st.columns(2)
        diary_date   = d1.date_input("Date", value=date.today())
        diary_result = d2.selectbox("Overall Session", ["Profitable","Break-even","Loss","Did not trade"])

        e1,e2,e3 = st.columns(3)
        emotion_before = e1.selectbox("Emotion BEFORE trading",
            ["Calm & focused","Slightly anxious","Greedy (wanted to make money fast)",
             "Fearful (worried about loss)","Overconfident","Tired/distracted"])
        emotion_during = e2.selectbox("Emotion DURING trade",
            ["Calm","Anxious","Excited","Panicked","Disciplined","Impatient"])
        emotion_after  = e3.selectbox("Emotion AFTER trade",
            ["Satisfied","Disappointed","Relieved","Regretful","Neutral","Overjoyed"])

        followed_plan = st.radio("Did you follow your trading plan 100%?",
                                 ["Yes ✅","Mostly — small deviation","No ❌"], horizontal=True)
        best_decision  = st.text_area("Best decision you made today", height=60,
                                       placeholder="e.g. Waited for ADX > 25 before entering")
        worst_decision = st.text_area("Worst decision / mistake today", height=60,
                                       placeholder="e.g. Entered before RSI confirmed")
        lesson         = st.text_area("Key lesson for tomorrow", height=60,
                                       placeholder="e.g. Never trade in first 30 minutes")
        tomorrow_rule  = st.text_input("One rule I will follow tomorrow",
                                        placeholder="e.g. Set SL before entry — no exceptions")

        if st.form_submit_button("💾 Save Diary Entry", use_container_width=True):
            entry = {
                "date":           str(diary_date),
                "result":         diary_result,
                "emotion_before": emotion_before,
                "emotion_during": emotion_during,
                "emotion_after":  emotion_after,
                "followed_plan":  followed_plan,
                "best_decision":  best_decision,
                "worst_decision": worst_decision,
                "lesson":         lesson,
                "tomorrow_rule":  tomorrow_rule,
            }
            diary = json.loads(st.session_state.get("diary_json","[]"))
            diary.append(entry)
            st.session_state["diary_json"] = json.dumps(diary)
            st.success("✅ Diary entry saved for {}!".format(diary_date))

    st.markdown("---")
    st.subheader("📚 Previous Diary Entries")
    diary_entries = json.loads(st.session_state.get("diary_json","[]"))
    if diary_entries:
        for e in reversed(diary_entries[-5:]):
            with st.expander("{} — {}".format(e["date"], e["result"])):
                c1,c2,c3 = st.columns(3)
                c1.write("**Before:** {}".format(e["emotion_before"]))
                c2.write("**During:** {}".format(e["emotion_during"]))
                c3.write("**After:** {}".format(e["emotion_after"]))
                st.write("**Followed plan:** {}".format(e["followed_plan"]))
                st.write("**Best decision:** {}".format(e["best_decision"]))
                st.write("**Mistake:** {}".format(e["worst_decision"]))
                st.write("**Lesson:** {}".format(e["lesson"]))
                st.write("**Tomorrow's rule:** {}".format(e["tomorrow_rule"]))
    else:
        st.info("No diary entries yet. Start writing after your next trading session!")


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: ✅ RULES CHECKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✅ Rules Checker":
    st.title("✅ Rules Checker")
    st.caption("Score yourself before and after every trade. Only trade when score is 8/10 or higher.")
    st.markdown("---")
    st.subheader("Pre-Trade Rules Score")
    st.markdown("Check every rule before entering a trade:")
    scores = []
    for i, rule in enumerate(TRADING_RULES):
        checked = st.checkbox("**Rule {}:** {}".format(i+1, rule), key="rule_{}".format(i))
        scores.append(checked)
    total_score = sum(scores)
    score_pct   = int(total_score / len(TRADING_RULES) * 100)
    st.markdown("---")
    if total_score >= 8:
        st.success("✅ **Score: {}/10 ({:.0f}%)** — You are ready to trade!".format(total_score, score_pct))
    elif total_score >= 6:
        st.warning("⚠️ **Score: {}/10 ({:.0f}%)** — Borderline. Fix the missing rules first.".format(total_score, score_pct))
    else:
        st.error("❌ **Score: {}/10 ({:.0f}%)** — DO NOT TRADE. Too many rules not followed.".format(total_score, score_pct))
    st.progress(score_pct)
    failed = [TRADING_RULES[i] for i,v in enumerate(scores) if not v]
    if failed:
        st.markdown("**Rules not followed:**")
        for r in failed:
            st.markdown("❌ " + r)
    st.markdown("---")
    st.subheader("📊 Why rules matter:")
    st.markdown("""
| Score | Action |
|-------|--------|
| 10/10 | ✅ Trade with full confidence |
| 8–9/10 | ✅ Trade — you are prepared |
| 6–7/10 | ⚠️ Trade with half lot size only |
| 0–5/10 | ❌ Do not trade — wait for better setup |
    """)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 🏆 STREAK TRACKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏆 Streak Tracker":
    st.title("🏆 Streak Tracker")
    st.caption("Consistency is the edge. Track your winning and losing streaks.")
    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    streak_icon = "🔥" if streak["type"]=="WIN" else ("💔" if streak["type"]=="LOSS" else "—")
    c1.metric("Current Streak",  "{} {} {}".format(streak_icon, streak["current"], streak["type"]))
    c2.metric("Longest Win Run",  "{} trades".format(streak["longest_win"]))
    c3.metric("Longest Loss Run", "{} trades".format(streak["longest_loss"]))
    c4.metric("Consistency",
              "{:.0f}%".format(stats["win_rate"]) if stats["total_trades"] > 0 else "—",
              "Win Rate")
    st.markdown("---")
    if streak["type"] == "WIN" and streak["current"] >= 3:
        st.success("🔥 {} win streak! Stay disciplined — don't increase size just because you're winning.".format(streak["current"]))
    elif streak["type"] == "LOSS" and streak["current"] >= 2:
        st.error("💔 {} loss streak. STOP and review. Do not revenge trade. Come back tomorrow fresh.".format(streak["current"]))
    elif streak["type"] == "LOSS" and streak["current"] >= 3:
        st.error("🚨 {} consecutive losses — MANDATORY break. Review your setup completely before next trade.".format(streak["current"]))

    if not closed_df.empty:
        st.subheader("📈 Trade-by-Trade Result History")
        results = closed_df.sort_values("Trade #")["Result"].tolist()
        colors  = ["#26a69a" if r=="WIN" else "#ef5350" for r in results]
        vals    = [1 if r=="WIN" else -1 for r in results]
        fig = go.Figure(go.Bar(
            x=list(range(1,len(vals)+1)), y=vals, marker_color=colors,
            text=results, textposition="outside",
            hovertemplate="Trade %{x}: %{text}<extra></extra>",
        ))
        fig.update_layout(template="plotly_dark",height=250,
                          title="Win / Loss Sequence",yaxis=dict(range=[-1.5,1.5],showticklabels=False),
                          xaxis_title="Trade Number",margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📅 MONTHLY P&L
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Monthly P&L":
    st.title("📅 Monthly P&L Report")
    st.markdown("---")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        closed_df["_month"] = pd.to_datetime(closed_df["Date"],errors="coerce").dt.to_period("M")
        months = sorted(closed_df["_month"].dropna().unique(), reverse=True)
        sel    = st.selectbox("Select Month", [str(m) for m in months]+["All Time"])
        view   = closed_df.copy() if sel=="All Time" else \
                 closed_df[closed_df["_month"].astype(str)==sel].copy()
        pnl_s   = pd.to_numeric(view["Net P&L"],     errors="coerce").fillna(0)
        gross_w = pd.to_numeric(view[view["Result"]=="WIN"]["Gross P&L"],  errors="coerce").sum()
        gross_l = pd.to_numeric(view[view["Result"]=="LOSS"]["Gross P&L"], errors="coerce").sum()
        brok    = pd.to_numeric(view["Brokerage"],    errors="coerce").sum()
        stt_v   = pd.to_numeric(view["STT"],          errors="coerce").sum()
        other_v = pd.to_numeric(view["Other Charges"],errors="coerce").sum()
        net     = pnl_s.sum()
        cap     = pd.to_numeric(view["Capital Used"], errors="coerce").sum()
        wc      = (view["Result"]=="WIN").sum(); lc = (view["Result"]=="LOSS").sum(); tot = len(view)
        cls     = "pnl-pos" if net>=0 else "pnl-neg"
        st.markdown("""
<style>
.pnl-box{{background:#1e2130;border-radius:10px;padding:20px 30px;font-family:monospace;font-size:15px;line-height:2.0}}
.pnl-pos{{color:#26a69a;font-weight:bold}}.pnl-neg{{color:#ef5350;font-weight:bold}}
.pnl-head{{color:#3498db;font-weight:bold;font-size:16px}}.pnl-div{{border-top:1px solid #444;margin:8px 0}}
</style>
<div class="pnl-box">
<span class="pnl-head">P&L STATEMENT — {title}</span><br>
<div class="pnl-div"></div>
Trades: <b>{tot}</b> &nbsp; Wins: <span class="pnl-pos">{wc}</span> &nbsp; Losses: <span class="pnl-neg">{lc}</span> &nbsp; Win Rate: <b>{wr:.1f}%</b>
<div class="pnl-div"></div>
Gross Revenue : <span class="pnl-pos">+Rs {gw:,.2f}</span><br>
Gross Loss    : <span class="pnl-neg"> Rs {gl:,.2f}</span><br>
<div class="pnl-div"></div>
Brokerage     : <span class="pnl-neg"> Rs {brok:,.2f}</span><br>
STT           : <span class="pnl-neg"> Rs {stt:,.2f}</span><br>
Other Charges : <span class="pnl-neg"> Rs {other:,.2f}</span><br>
<div class="pnl-div"></div>
<b>NET PROFIT / LOSS : <span class="{cls}">Rs {net:,.2f}</span></b><br>
<div class="pnl-div"></div>
Capital Used : Rs {cap:,.2f}
</div>""".format(title=sel,tot=tot,wc=wc,lc=lc,wr=(wc/tot*100) if tot else 0,
                 gw=gross_w,gl=abs(gross_l),brok=brok,stt=stt_v,other=other_v,
                 net=net,cap=cap,cls=cls), unsafe_allow_html=True)
        st.markdown("---")
        st.dataframe(view[["Trade #","Date","Symbol","Option Type","Strike",
                            "Entry Price","Exit Price","Lots","Net P&L","Result"]
                    ].sort_values("Trade #",ascending=False), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 💸 EXPENSES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💸 Expenses":
    st.title("💸 Charges & Expenses")
    st.markdown("---")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        e1,e2,e3,e4 = st.columns(4)
        e1.metric("Total Brokerage",    "Rs {:,.2f}".format(stats["total_brokerage"]))
        e2.metric("Total STT",          "Rs {:,.2f}".format(pd.to_numeric(closed_df["STT"],errors="coerce").sum()))
        e3.metric("Other Charges",      "Rs {:,.2f}".format(pd.to_numeric(closed_df["Other Charges"],errors="coerce").sum()))
        e4.metric("Total Charges Paid", "Rs {:,.2f}".format(stats["total_charges"]))
        gross = pd.to_numeric(closed_df["Gross P&L"],errors="coerce").sum()
        fig = go.Figure(go.Bar(
            x=["Gross P&L","Charges","Net P&L"],
            y=[gross,-stats["total_charges"],stats["total_pnl"]],
            marker_color=["#3498db","#e74c3c","#26a69a" if stats["total_pnl"]>=0 else "#ef5350"],
            text=["Rs {:,.0f}".format(v) for v in [gross,stats["total_charges"],stats["total_pnl"]]],
            textposition="outside"))
        fig.update_layout(template="plotly_dark",height=320,title="Gross vs Charges vs Net",
                          margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.info("💡 You are paying Rs {:,.0f} in charges per trade on average. Every rupee saved in charges is direct profit.".format(
            stats["total_charges"] / max(stats["total_trades"],1)))


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: ⬇️ EXPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⬇️ Export":
    st.title("⬇️ Export Reports")
    st.markdown("---")
    if df.empty:
        st.info("No trades yet to export.")
    else:
        today = datetime.now().strftime("%Y%m%d")
        st.download_button("⬇️ Download All Trades (CSV)",
                           data=df.to_csv(index=False).encode("utf-8"),
                           file_name="My_Trades_{}.csv".format(today),
                           mime="text/csv", use_container_width=True)
        st.info("Your data is safely in Google Sheets ☁️ — this is just a backup copy.")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("📒 Trading Management System | Cloud Edition | Not financial advice")
