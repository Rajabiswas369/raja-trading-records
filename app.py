"""
Nifty F&O Trading Records & Management
=======================================
  📊 My Records Dashboard     — Capital growth, win/loss stats, equity curve
  💰 My Capital               — Capital tracker, reset starting balance, deposits, withdrawals
  📓 Log Trade                — Manual trade entry + live journal table + instant delete option
  🔄 Angel One Sync           — Auto-fetch executed trades from Angel One
  📋 All Trades               — View, filter, and inspect all trades
  📅 Monthly Report           — Monthly P&L calendar & breakdowns
  📈 Performance              — Win rate by symbol, option type, RSI zone
  💸 Expenses                 — Brokerage, STT, and charges breakdown
  ⬇️ Export                   — Download Excel & CSV reports

Data stored permanently in Supabase Cloud.
For live signals and indicators, use the Signal Dashboard app.
"""

import pandas as pd
from datetime import datetime
from io import BytesIO

import streamlit as st
import plotly.graph_objects as go
import pytz

from cloud_data import (
    load_trades, add_trade, delete_trade, get_stats,
    load_capital_history, update_capital, add_capital_deposit, withdraw_capital, reset_capital, get_capital_stats,
    build_excel_report, _is_cloud,
    DEFAULT_BROKERAGE, DEFAULT_OTHER, DEFAULT_STT_PCT,
    TRADE_COLUMNS,
)
from angel_sync import render_angel_sync_panel, is_angel_configured

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty F&O Trading Records",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═════════════════════════════════════════════════════════════════════════════
NSE_SYMBOLS = {
    "NIFTY50":    "^NSEI",
    "BANKNIFTY":  "^NSEBANK",
    "FINNIFTY":   "NIFTY_FIN_SERVICE.NS",
    "RELIANCE":   "RELIANCE.NS",
    "TCS":        "TCS.NS",
    "INFY":       "INFY.NS",
    "HDFCBANK":   "HDFCBANK.NS",
    "ICICIBANK":  "ICICIBANK.NS",
    "SBIN":       "SBIN.NS",
    "AXISBANK":   "AXISBANK.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "WIPRO":      "WIPRO.NS",
    "ADANIENT":   "ADANIENT.NS",
    "MARUTI":     "MARUTI.NS",
}

IST = pytz.timezone("Asia/Kolkata")

# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═════════════════════════════════════════════════════════════════════════════
st.sidebar.image("https://img.icons8.com/color/96/combo-chart.png", width=56)
st.sidebar.title("Nifty F&O Records")
st.sidebar.markdown("---")

if _is_cloud():
    st.sidebar.success("☁️ Storage: **Supabase Cloud (Live)**")
else:
    st.sidebar.warning("💻 Running locally — memory only")

angel_ok = is_angel_configured()
if angel_ok:
    st.sidebar.success("✅ Angel One **Configured**")
else:
    st.sidebar.info("ℹ️ Angel One not configured")

st.sidebar.markdown("---")
st.sidebar.info("📈 **For live signals & indicators**, use the Signal Dashboard app.")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "📂 Navigate",
    [
        "📊 My Records Dashboard",
        "💰 My Capital",
        "📓 Log Trade",
        "🔄 Angel One Sync",
        "📋 All Trades",
        "📅 Monthly Report",
        "📈 Performance",
        "💸 Expenses",
        "⬇️ Export",
    ],
    index=0,
)
st.sidebar.markdown("---")

# ── Load persistent data ──────────────────────────────────────────────────────
df        = load_trades()
stats     = get_stats(df)
cap_df    = load_capital_history()
cap_stats = get_capital_stats()
closed_df = df[df["Result"].isin(["WIN", "LOSS"])].copy() if not df.empty else pd.DataFrame()


def pnl_delta(val):
    d  = ("▲ Rs {:,.0f}".format(val) if val >= 0 else "▼ Rs {:,.0f}".format(abs(val)))
    dc = "normal" if val >= 0 else "inverse"
    return d, dc


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📊 MY RECORDS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 My Records Dashboard":
    st.title("📊 My Trading Dashboard")
    st.markdown("---")

    rem_pct = (cap_stats["current"] / cap_stats["initial"] * 100) if cap_stats["initial"] else 0
    rem_pct_safe = max(0, min(int(rem_pct), 100))
    cap_d, cap_dc = pnl_delta(cap_stats["pnl"])
    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    cc1.metric("💰 Initial Capital",  "Rs {:,.0f}".format(cap_stats["initial"]))
    cc2.metric("💵 Current Balance",  "Rs {:,.0f}".format(cap_stats["current"]), cap_d, delta_color=cap_dc)
    cc3.metric("📉 P&L",              "Rs {:,.0f}".format(cap_stats["pnl"]),
               "{:.1f}%".format(cap_stats["pnl_pct"]),
               delta_color="normal" if cap_stats["pnl"] >= 0 else "inverse")
    cc4.metric("📅 Days Trading",     "{} days".format(cap_stats["days"]))
    cc5.metric("🏦 Capital Left",     "{:.1f}%".format(rem_pct),
               delta_color="normal" if rem_pct >= 80 else "inverse")

    prog = "🟢" if rem_pct >= 80 else ("🟡" if rem_pct >= 60 else "🔴")
    st.progress(rem_pct_safe,
                text="{} Rs {:,.0f} of Rs {:,.0f} remaining ({:.1f}%)".format(
                    prog, cap_stats["current"], cap_stats["initial"], rem_pct))

    with st.expander("✏️ Edit / Fix Capital", expanded=False):
        edit_tab1, edit_tab2 = st.tabs(["🔧 Set / Fix Initial Capital", "➕ Add Capital Deposit"])
        with edit_tab1:
            st.caption("⚠️ Use this to correct the Initial Capital shown above (currently Rs {:,.0f}).".format(cap_stats["initial"]))
            with st.form("dash_reset_cap_form"):
                dr1, dr2 = st.columns(2)
                new_init = dr1.number_input("Correct Initial Capital (Rs)",
                    value=float(cap_stats["initial"]) if cap_stats["initial"] else 40000.0,
                    step=1000.0, format="%.0f")
                new_start_date = dr2.date_input("Trading Start Date", value=datetime.today())
                if st.form_submit_button("⚠️ Reset & Set Initial Capital to Rs {:,.0f}".format(new_init), type="primary"):
                    reset_capital(new_init, new_start_date.strftime("%Y-%m-%d"))
                    st.success("✅ Initial capital reset to Rs {:,.0f}".format(new_init))
                    st.rerun()
        with edit_tab2:
            st.caption("Added more money to your trading account? Enter how much you deposited.")
            with st.form("dash_deposit_form"):
                dd1, dd2 = st.columns(2)
                deposit_amt  = dd1.number_input("Amount Deposited (Rs)", value=0.0, min_value=0.0, step=1000.0, format="%.0f")
                deposit_note = dd2.text_input("Note", placeholder="e.g. Added funds from bank")
                if st.form_submit_button("➕ Add Rs {:,.0f} to Capital".format(deposit_amt), type="primary"):
                    if deposit_amt <= 0:
                        st.error("Enter an amount greater than 0.")
                    else:
                        new_b = add_capital_deposit(deposit_amt, deposit_note)
                        st.success("✅ Rs {:,.0f} added — New balance: Rs {:,.0f}".format(deposit_amt, new_b))
                        st.rerun()

    st.markdown("---")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Trades", stats["total_trades"])
    k2.metric("Win Rate",     "{:.1f}%".format(stats["win_rate"]))
    d, dc = pnl_delta(stats["total_pnl"])
    k3.metric("Net P&L",      "Rs {:,.0f}".format(stats["total_pnl"]), d, delta_color=dc)
    k4.metric("Reward:Risk",  "{:.2f}x".format(stats["reward_risk"]))

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Wins",        stats["wins"])
    k6.metric("Losses",      stats["losses"])
    k7.metric("Best Trade",  "Rs {:,.0f}".format(stats["best_trade"]))
    k8.metric("Worst Trade", "Rs {:,.0f}".format(stats["worst_trade"]))

    st.markdown("---")

    if not closed_df.empty:
        pnl_s = pd.to_numeric(closed_df["Net P&L"], errors="coerce").fillna(0)
        left, right = st.columns([3, 2])
        with left:
            st.subheader("📈 Cumulative P&L Growth")
            cum = pnl_s.cumsum()
            fig_pnl = go.Figure()
            fig_pnl.add_trace(go.Scatter(
                x=list(range(1, len(cum) + 1)), y=cum,
                mode="lines+markers",
                line=dict(color="#26a69a" if cum.iloc[-1] >= 0 else "#ef5350", width=2.5),
                fill="tozeroy",
                fillcolor="rgba(38,166,154,0.1)" if cum.iloc[-1] >= 0 else "rgba(239,83,80,0.1)",
                name="Cumulative P&L",
            ))
            fig_pnl.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
            fig_pnl.update_layout(xaxis_title="Trade Number", yaxis_title="Net P&L (Rs)",
                                  template="plotly_dark", height=320, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_pnl, use_container_width=True)
        with right:
            st.subheader("🎯 Win / Loss Ratio")
            fig_pie = go.Figure(go.Pie(
                labels=["Wins", "Losses"], values=[stats["wins"], stats["losses"]],
                hole=0.55, marker=dict(colors=["#26a69a", "#ef5350"]),
            ))
            fig_pie.update_layout(template="plotly_dark", height=320,
                                  margin=dict(l=0, r=0, t=20, b=0), showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📋 Recent 5 Trades")
        rc = ["Trade #", "Date", "Symbol", "Option Type", "Strike",
              "Entry Price", "Exit Price", "Lots", "Net P&L", "Result"]
        st.dataframe(closed_df[rc].tail(5).sort_index(ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No closed trades yet. Go to **📓 Log Trade** to record your first trade!")


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 💰 MY CAPITAL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💰 My Capital":
    st.title("💰 Capital Tracker & Balance History")
    st.caption("Auto-updated on every closed trade. Deposit or withdraw funds anytime.")
    st.markdown("---")

    rem_pct = (cap_stats["current"] / cap_stats["initial"] * 100) if cap_stats["initial"] else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Initial Capital",  "Rs {:,.0f}".format(cap_stats["initial"]))
    d, dc = pnl_delta(cap_stats["pnl"])
    c2.metric("Current Balance",  "Rs {:,.0f}".format(cap_stats["current"]), d, delta_color=dc)
    c3.metric("Growth %",         "{:+.1f}%".format(cap_stats["pnl_pct"]),
              delta_color="normal" if cap_stats["pnl"] >= 0 else "inverse")
    c4.metric("Days Active",      "{} days".format(cap_stats["days"]))

    st.markdown("---")

    tab_dep, tab_wd, tab_set, tab_hist = st.tabs([
        "➕ Add Deposit", "➖ Withdraw Funds", "🔧 Set / Fix Initial Capital", "📜 Full History"
    ])
    with tab_dep:
        st.subheader("Add Funds to Trading Account")
        with st.form("deposit_form"):
            dep_amt  = st.number_input("Deposit Amount (Rs)", min_value=100.0, value=5000.0, step=500.0)
            dep_note = st.text_input("Note", placeholder="e.g. Added funds from salary")
            if st.form_submit_button("➕ Add Deposit", type="primary"):
                new_bal = add_capital_deposit(dep_amt, dep_note)
                st.success("✅ Deposit of Rs {:,.0f} saved! New balance: Rs {:,.0f}".format(dep_amt, new_bal))
                st.rerun()
    with tab_wd:
        st.subheader("Withdraw Funds from Trading Account")
        with st.form("withdraw_form"):
            wd_amt  = st.number_input("Withdrawal Amount (Rs)", min_value=100.0, value=2000.0, step=500.0)
            wd_note = st.text_input("Note", placeholder="e.g. Profit payout to bank")
            if st.form_submit_button("➖ Record Withdrawal", type="secondary"):
                new_bal = withdraw_capital(wd_amt, wd_note)
                st.success("✅ Withdrawal of Rs {:,.0f} recorded! New balance: Rs {:,.0f}".format(wd_amt, new_bal))
                st.rerun()
    with tab_set:
        st.subheader("Reset / Fix Starting Capital")
        st.caption("Use this if your starting capital was recorded incorrectly.")
        with st.form("reset_form"):
            r_cap  = st.number_input("Starting Capital (Rs)", min_value=1000.0, value=40000.0, step=1000.0)
            r_date = st.date_input("Start Date", value=datetime.today())
            if st.form_submit_button("⚠️ Reset Starting Capital", type="primary"):
                reset_capital(r_cap, r_date.strftime("%Y-%m-%d"))
                st.success("✅ Capital reset to Rs {:,.0f} as of {}".format(r_cap, r_date))
                st.rerun()
    with tab_hist:
        st.subheader("Capital Log")
        if not cap_df.empty:
            st.dataframe(cap_df.sort_index(ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No capital history found.")


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📓 LOG TRADE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📓 Log Trade":
    st.title("📓 Manual Trade Entry")
    st.caption("Record your trade with full risk analytics & lessons learned.")
    st.markdown("---")

    if "save_trade_msg" in st.session_state:
        msg = st.session_state.pop("save_trade_msg")
        if msg.get("type") == "success":
            st.success(msg["text"])
        else:
            st.error(msg["text"])

    with st.form("log_trade_form", clear_on_submit=True):
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        f_symbol = r1c1.selectbox("Symbol", list(NSE_SYMBOLS.keys()), index=0, key="lt_sym")
        f_type   = r1c2.selectbox("Option Type", ["PUT", "CALL"], key="lt_type")
        f_strike = r1c3.number_input("Strike Price", value=24000, step=50, key="lt_strike")
        f_expiry = r1c4.text_input("Expiry Date", value=datetime.today().strftime("%Y-%m-%d"), key="lt_exp")

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        f_entry = r2c1.number_input("Entry Price (Rs)", value=100.0, step=0.5, format="%.2f", key="lt_entry")
        f_exit  = r2c2.number_input("Exit Price (Rs, 0 if OPEN)", value=0.0, step=0.5, format="%.2f", key="lt_exit")
        f_lots  = r2c3.number_input("Lots", min_value=1, value=1, step=1, key="lt_lots")
        f_size  = r2c4.number_input("Lot Size", min_value=1, value=75, step=1, key="lt_size")

        st.markdown("**Technical Indicators at Entry**")
        m1, m2, m3, m4 = st.columns(4)
        f_rsi   = m1.number_input("RSI at Entry", value=50.0, step=0.1, format="%.1f", min_value=0.0, max_value=100.0, key="lt_rsi")
        f_adx   = m2.number_input("ADX at Entry", value=25.0, step=0.1, format="%.1f", min_value=0.0, max_value=100.0, key="lt_adx")
        f_st    = m3.selectbox("Supertrend", ["BEARISH", "BULLISH"], key="lt_st")
        f_dsaid = m4.selectbox("Dashboard Said", ["PUT", "CALL", "WAIT"], key="lt_dsaid")

        st.markdown("**Reflection & Notes**")
        n1, n2, n3 = st.columns(3)
        f_hold    = n1.text_input("Hold Time", placeholder="e.g. 25 mins", key="lt_hold")
        f_lessons = n2.text_input("Lessons Learned", placeholder="e.g. Never enter RSI < 35", key="lt_lessons")
        f_notes   = n3.text_input("Notes", placeholder="e.g. Clean bounce from VWAP", key="lt_notes")

        sub = st.form_submit_button("💾 Save Trade", type="primary", use_container_width=True)
        if sub:
            saved = add_trade(
                symbol=f_symbol, option_type=f_type, strike=f_strike, expiry=f_expiry,
                entry_price=f_entry, exit_price=f_exit, lots=f_lots, lot_size=f_size,
                entry_rsi=f_rsi, entry_adx=f_adx, supertrend=f_st,
                dashboard_said=f_dsaid, hold_time=f_hold, lessons=f_lessons, notes=f_notes,
            )
            em = "✅ WIN" if saved["Result"] == "WIN" else ("❌ LOSS" if saved["Result"] == "LOSS" else "📂 OPEN")
            st.session_state["save_trade_msg"] = {
                "type": "success",
                "text": "Trade #{} saved! {} | Net P&L: {}".format(
                    saved["Trade #"], em,
                    "Rs {:,.0f}".format(saved["Net P&L"]) if f_exit > 0 else "Open position"),
            }
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Recent Trades Log")
    fresh_df = load_trades()
    if fresh_df.empty:
        st.info("No trades logged yet in the database.")
    else:
        show_cols = ["Trade #", "Date", "Symbol", "Option Type", "Strike",
                     "Entry Price", "Exit Price", "Lots", "Net P&L", "Result"]
        st.dataframe(fresh_df[show_cols].sort_values("Trade #", ascending=False).head(20),
                     use_container_width=True, hide_index=True)

    st.markdown("#### 🗑️ Delete a Trade")
    st.caption("⚠️ Deleting a closed trade will also reverse its impact on your capital balance.")

    if "del_trade_msg" in st.session_state:
        msg = st.session_state.pop("del_trade_msg")
        if msg.get("type") == "success":
            st.success(msg["text"])
        else:
            st.error(msg["text"])

    if fresh_df.empty:
        st.caption("No trades available to delete.")
    else:
        del_col1, del_col2 = st.columns([2, 1])
        trade_labels = [
            "#{} — {} {} {} | {}".format(int(r["Trade #"]), r["Date"], r["Symbol"], r["Option Type"], r["Result"])
            for _, r in fresh_df.sort_values("Trade #", ascending=False).iterrows()
        ]
        sel_label = del_col1.selectbox("Select trade to delete", trade_labels, key="lt_del_sel")
        sel_num   = int(sel_label.split(" — ")[0].replace("#", "").strip())
        if del_col2.button("🗑️ Delete Selected Trade", type="secondary", use_container_width=True, key="lt_del_btn"):
            status = delete_trade(sel_num)
            if status == "deleted_with_capital":
                st.session_state["del_trade_msg"] = {"type": "success",
                    "text": "✅ Trade #{} deleted and capital balance reversed.".format(sel_num)}
            elif status == "deleted":
                st.session_state["del_trade_msg"] = {"type": "success",
                    "text": "✅ Trade #{} deleted (OPEN trade — no capital change).".format(sel_num)}
            else:
                st.session_state["del_trade_msg"] = {"type": "error", "text": str(status)}
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 🔄 ANGEL ONE SYNC
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔄 Angel One Sync":
    st.title("🔄 Angel One Auto-Sync")
    st.caption("Automatically fetch your executed trades from Angel One — no manual entry needed!")
    st.markdown("---")
    render_angel_sync_panel()


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📋 ALL TRADES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 All Trades":
    st.title("📋 All Trades")
    if df.empty:
        st.info("No trades yet. Log your first trade from **📓 Log Trade**.")
    else:
        fc1, fc2, fc3 = st.columns(3)
        syms     = ["All"] + sorted(df["Symbol"].dropna().unique().tolist())
        filt_sym = fc1.selectbox("Symbol",      syms)
        filt_typ = fc2.selectbox("Option Type", ["All", "PUT", "CALL"])
        filt_res = fc3.selectbox("Result",      ["All", "WIN", "LOSS", "OPEN"])
        view = df.copy()
        if filt_sym != "All": view = view[view["Symbol"] == filt_sym]
        if filt_typ != "All": view = view[view["Option Type"] == filt_typ]
        if filt_res != "All": view = view[view["Result"] == filt_res]
        st.caption("{} trades shown".format(len(view)))
        st.dataframe(view.sort_values("Trade #", ascending=False), use_container_width=True, hide_index=True)
        if not view.empty:
            pnl_tot = pd.to_numeric(view["Net P&L"], errors="coerce").sum()
            d, dc   = pnl_delta(pnl_tot)
            t1, t2  = st.columns(2)
            t1.metric("Net P&L (filtered)", "Rs {:,.0f}".format(pnl_tot), d, delta_color=dc)
            t2.metric("Capital Used", "Rs {:,.0f}".format(pd.to_numeric(view["Capital Used"], errors="coerce").sum()))


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📅 MONTHLY REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Monthly Report":
    st.title("📅 Monthly P&L Report")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        mdf = closed_df.copy()
        mdf["Month"] = pd.to_datetime(mdf["Date"], errors="coerce").dt.strftime("%Y-%m")
        grouped = mdf.groupby("Month").apply(lambda g: pd.Series({
            "Trades":     len(g),
            "Wins":       (g["Result"] == "WIN").sum(),
            "Losses":     (g["Result"] == "LOSS").sum(),
            "Win Rate %": round((g["Result"] == "WIN").sum() / len(g) * 100, 1),
            "Gross P&L":  pd.to_numeric(g["Gross P&L"], errors="coerce").sum().round(2),
            "Charges":    (pd.to_numeric(g["Brokerage"], errors="coerce").sum() +
                           pd.to_numeric(g["STT"], errors="coerce").sum() +
                           pd.to_numeric(g["Other Charges"], errors="coerce").sum()).round(2),
            "Net P&L":    pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
        })).reset_index()
        st.dataframe(grouped, use_container_width=True, hide_index=True)
        fig_m = go.Figure()
        colors = ["#26a69a" if v >= 0 else "#ef5350" for v in grouped["Net P&L"]]
        fig_m.add_trace(go.Bar(x=grouped["Month"], y=grouped["Net P&L"], marker_color=colors))
        fig_m.update_layout(template="plotly_dark", height=300, yaxis_title="Net P&L (Rs)")
        st.plotly_chart(fig_m, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 📈 PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Performance":
    st.title("📈 Performance Analysis")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        t1, t2, t3 = st.tabs(["By Symbol", "PUT vs CALL", "Dashboard Accuracy"])
        with t1:
            sg = closed_df.groupby("Symbol").apply(lambda g: pd.Series({
                "Trades":     len(g),
                "Wins":       (g["Result"] == "WIN").sum(),
                "Net P&L":    pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
                "Win Rate %": round((g["Result"] == "WIN").sum() / len(g) * 100, 1),
            })).reset_index()
            st.dataframe(sg, use_container_width=True, hide_index=True)
        with t2:
            og = closed_df.groupby("Option Type").apply(lambda g: pd.Series({
                "Trades":     len(g),
                "Wins":       (g["Result"] == "WIN").sum(),
                "Net P&L":    pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
                "Win Rate %": round((g["Result"] == "WIN").sum() / len(g) * 100, 1),
            })).reset_index()
            st.dataframe(og, use_container_width=True, hide_index=True)
        with t3:
            dg = closed_df.groupby("Dashboard Said").apply(lambda g: pd.Series({
                "Trades":     len(g),
                "Wins":       (g["Result"] == "WIN").sum(),
                "Net P&L":    pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
                "Win Rate %": round((g["Result"] == "WIN").sum() / len(g) * 100, 1),
            })).reset_index()
            st.dataframe(dg, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: 💸 EXPENSES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💸 Expenses":
    st.title("💸 Brokerage & Taxes Breakdown")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        brok_tot  = pd.to_numeric(closed_df["Brokerage"], errors="coerce").sum()
        stt_tot   = pd.to_numeric(closed_df["STT"], errors="coerce").sum()
        other_tot = pd.to_numeric(closed_df["Other Charges"], errors="coerce").sum()
        grand_tot = brok_tot + stt_tot + other_tot
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Total Charges", "Rs {:,.0f}".format(grand_tot))
        e2.metric("Brokerage",     "Rs {:,.0f}".format(brok_tot))
        e3.metric("STT (Govt)",    "Rs {:,.0f}".format(stt_tot))
        e4.metric("Other Charges", "Rs {:,.0f}".format(other_tot))


# ══════════════════════════════════════════════════════════════════════════════
# ██  PAGE: ⬇️ EXPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⬇️ Export":
    st.title("⬇️ Export Your Records")
    st.markdown("---")
    if df.empty:
        st.info("No trades to export yet.")
    else:
        st.subheader("📊 Download Full Excel Report")
        excel_bytes = build_excel_report(df)
        today = datetime.now().strftime("%Y%m%d")
        st.download_button(
            label="⬇️ Download Excel Report",
            data=excel_bytes,
            file_name="Raja_Trading_Report_{}.xlsx".format(today),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.markdown("---")
        st.subheader("📋 Download CSV")
        st.download_button(
            label="⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="Raja_Trades_{}.csv".format(today),
            mime="text/csv",
            use_container_width=True,
        )

st.markdown("---")
st.caption("💼 Nifty F&O Trading Records | Powered by Supabase Cloud | Educational & personal tracking only")
