"""
Raja's Trading Records — Cloud App
Accessible from any device, anywhere.
Data stored in Google Sheets — persistent forever.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO

from cloud_data import (
    load_trades, add_trade, get_stats,
    load_capital_history, update_capital, get_capital_stats,
    build_excel_report, _is_cloud,
    DEFAULT_BROKERAGE, DEFAULT_OTHER,
)

st.set_page_config(
    page_title="Raja's Trading Records",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("📒 Raja's Trading Records")
st.sidebar.markdown("---")

# Cloud status indicator
if _is_cloud():
    st.sidebar.success("☁️ Connected to Google Sheets")
else:
    st.sidebar.warning("💻 Running locally — data in memory only")

page = st.sidebar.radio("Go to", [
    "📊 Dashboard",
    "💰 My Capital",
    "📓 Log Trade",
    "📋 All Trades",
    "📅 Monthly Report",
    "📈 Performance",
    "⬇️ Export",
])
st.sidebar.markdown("---")
st.sidebar.caption("Data syncs to Google Sheets automatically.\nOpen from any device, anywhere.")

# ── Load data ─────────────────────────────────────────────────────────────────
df        = load_trades()
stats     = get_stats(df)
cap_stats = get_capital_stats()
closed_df = df[df["Result"].isin(["WIN", "LOSS"])].copy() if not df.empty else pd.DataFrame()


def pnl_color(val):
    d  = ("▲ Rs {:,.0f}".format(val) if val >= 0 else "▼ Rs {:,.0f}".format(abs(val)))
    dc = "normal" if val >= 0 else "inverse"
    return d, dc


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.title("📊 My Trading Dashboard")
    st.markdown("---")

    # Capital health bar
    rem_pct = (cap_stats["current"] / cap_stats["initial"] * 100) if cap_stats["initial"] else 0
    cap_d, cap_dc = pnl_color(cap_stats["pnl"])
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
    st.progress(min(int(rem_pct), 100),
                text="{} Rs {:,.0f} of Rs {:,.0f} remaining ({:.1f}%)".format(
                    prog, cap_stats["current"], cap_stats["initial"], rem_pct))

    st.markdown("---")

    # Trade KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Trades", stats["total_trades"])
    k2.metric("Win Rate",     "{:.1f}%".format(stats["win_rate"]))
    d, dc = pnl_color(stats["total_pnl"])
    k3.metric("Net P&L",      "Rs {:,.0f}".format(stats["total_pnl"]), d, delta_color=dc)
    k4.metric("Reward:Risk",  "{:.2f}x".format(stats["reward_risk"]))

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Wins",       stats["wins"])
    k6.metric("Losses",     stats["losses"])
    k7.metric("Best Trade", "Rs {:,.0f}".format(stats["best_trade"]))
    k8.metric("Worst Trade","Rs {:,.0f}".format(stats["worst_trade"]))

    st.markdown("---")

    if not closed_df.empty:
        pnl_s = pd.to_numeric(closed_df["Net P&L"], errors="coerce").fillna(0)
        left, right = st.columns([3, 2])

        with left:
            equity = pnl_s.cumsum().reset_index(drop=True)
            colors = ["#26a69a" if v >= 0 else "#ef5350" for v in pnl_s]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(1, len(equity)+1)), y=equity,
                mode="lines+markers",
                line=dict(color="#3498db", width=2.5),
                marker=dict(color=colors, size=9),
                hovertemplate="Trade %{x}<br>Cumulative P&L: Rs %{y:,.0f}<extra></extra>",
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
            fig.update_layout(template="plotly_dark", height=300,
                              title="📈 Equity Curve",
                              xaxis_title="Trade #", yaxis_title="Cumulative P&L (Rs)",
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with right:
            pie = go.Figure(go.Pie(
                labels=["Wins", "Losses"],
                values=[stats["wins"], stats["losses"]],
                marker=dict(colors=["#26a69a", "#ef5350"]),
                hole=0.5, textinfo="label+percent",
            ))
            pie.update_layout(template="plotly_dark", height=300,
                              title="🏆 Win/Loss", showlegend=False,
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(pie, use_container_width=True)

        # Recent trades
        st.markdown("#### 🕐 Last 5 Trades")
        show_cols = ["Trade #","Date","Symbol","Option Type","Strike",
                     "Entry Price","Exit Price","Net P&L","Result"]
        st.dataframe(df[show_cols].tail(5).sort_index(ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet. Go to **📓 Log Trade** to record your first trade!")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 2 — MY CAPITAL
# ═════════════════════════════════════════════════════════════════════════════
elif page == "💰 My Capital":
    st.title("💰 My Capital Tracker")
    st.caption("Track your investment from any device. Updates saved to Google Sheets instantly.")
    st.markdown("---")

    rem_pct = (cap_stats["current"] / cap_stats["initial"] * 100) if cap_stats["initial"] else 0
    cap_d, cap_dc = pnl_color(cap_stats["pnl"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Initial",        "Rs {:,.0f}".format(cap_stats["initial"]))
    c2.metric("💵 Current Balance","Rs {:,.0f}".format(cap_stats["current"]), cap_d, delta_color=cap_dc)
    c3.metric("📊 Total P&L",      "Rs {:,.0f}".format(cap_stats["pnl"]),
              "{:.2f}%".format(cap_stats["pnl_pct"]),
              delta_color="normal" if cap_stats["pnl"] >= 0 else "inverse")
    c4.metric("📅 Days Trading",   "{} days".format(cap_stats["days"]))
    c5.metric("🏦 Capital Left",   "{:.1f}%".format(rem_pct),
              delta_color="normal" if rem_pct >= 80 else "inverse")

    prog = "🟢" if rem_pct >= 80 else ("🟡" if rem_pct >= 60 else "🔴")
    st.progress(min(int(rem_pct), 100),
                text="{} Rs {:,.0f} of Rs {:,.0f} remaining ({:.1f}%)".format(
                    prog, cap_stats["current"], cap_stats["initial"], rem_pct))

    st.markdown("---")

    # Update balance form
    with st.expander("⚙️ Update My Balance", expanded=False):
        with st.form("cap_form"):
            uf1, uf2 = st.columns(2)
            new_bal  = uf1.number_input("New Balance (Rs)", value=float(cap_stats["current"]),
                                         step=100.0, format="%.0f")
            note_txt = uf2.text_input("Reason", placeholder="e.g. After today's trade")
            if st.form_submit_button("💾 Update Balance"):
                update_capital(new_bal, note_txt)
                st.success("Balance updated to Rs {:,.0f}".format(new_bal))
                st.rerun()

    st.markdown("---")

    # Capital history chart
    hist = cap_stats.get("history", [])
    if hist:
        hdf = pd.DataFrame(hist)
        hdf["Date"]    = pd.to_datetime(hdf["Date"], errors="coerce")
        hdf["Balance"] = pd.to_numeric(hdf["Balance"], errors="coerce")
        hdf = hdf.sort_values("Date").reset_index(drop=True)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=hdf["Date"], y=hdf["Balance"],
            mode="lines+markers",
            line=dict(color="#3498db", width=2.5),
            fill="tozeroy", fillcolor="rgba(52,152,219,0.08)",
            marker=dict(size=9, color="#3498db"),
            hovertemplate="%{x|%d %b %Y}<br>Balance: Rs %{y:,.0f}<extra></extra>",
        ))
        fig2.add_hline(y=cap_stats["initial"], line_dash="dash",
                       line_color="rgba(255,255,255,0.4)",
                       annotation_text="Initial: Rs {:,.0f}".format(cap_stats["initial"]),
                       annotation_position="bottom right")
        fig2.update_layout(template="plotly_dark", height=350,
                           title="💵 Capital Balance Over Time",
                           xaxis_title="Date", yaxis_title="Rs",
                           margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📋 Balance History")
        st.dataframe(hdf[["Date","Balance","Note"]].sort_values("Date", ascending=False),
                     use_container_width=True, hide_index=True)

    # 30-day projection
    st.markdown("---")
    st.subheader("🔮 30-Day Projection")
    if stats["total_trades"] > 0:
        avg = stats["total_pnl"] / stats["total_trades"]
        proj_pnl = avg * stats["total_trades"]
        proj_bal = cap_stats["current"] + proj_pnl
        p1, p2, p3 = st.columns(3)
        p1.metric("Avg P&L / Trade",   "Rs {:,.0f}".format(avg))
        p2.metric("Projected 30d P&L", "Rs {:,.0f}".format(proj_pnl),
                  delta_color="normal" if proj_pnl >= 0 else "inverse")
        p3.metric("Projected Balance", "Rs {:,.0f}".format(proj_bal),
                  delta_color="normal" if proj_bal >= cap_stats["initial"] else "inverse")
        st.caption("⚠️ Based on {} trade(s) only. More trades = more accurate.".format(stats["total_trades"]))
    else:
        st.info("Log trades to see your 30-day projection.")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 3 — LOG TRADE
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📓 Log Trade":
    st.title("📓 Log a Trade")
    st.caption("Saved instantly to Google Sheets. Visible on all your devices.")
    st.markdown("---")

    with st.form("trade_form", clear_on_submit=True):
        st.subheader("Trade Details")
        c1, c2, c3, c4 = st.columns(4)
        f_sym    = c1.text_input("Symbol",      value="NIFTY50")
        f_type   = c2.selectbox("PUT / CALL",   ["PUT", "CALL"])
        f_strike = c3.number_input("Strike",    value=22500, step=50)
        f_expiry = c4.text_input("Expiry",      placeholder="e.g. 06 Oct 2026")

        c5, c6, c7, c8 = st.columns(4)
        f_entry  = c5.number_input("Entry Price (Rs)", value=0.0, step=0.5, format="%.2f")
        f_exit   = c6.number_input("Exit Price (Rs) — 0 if open", value=0.0, step=0.5, format="%.2f")
        f_lots   = c7.number_input("Lots",      value=1, step=1, min_value=1)
        f_lsize  = c8.number_input("Lot Size",  value=75, step=1, min_value=1)

        st.subheader("Market Conditions")
        m1, m2, m3, m4 = st.columns(4)
        f_rsi    = m1.number_input("RSI",       value=50.0, step=0.1, format="%.1f")
        f_adx    = m2.number_input("ADX",       value=25.0, step=0.1, format="%.1f")
        f_st     = m3.selectbox("Supertrend",   ["BEARISH", "BULLISH"])
        f_dsaid  = m4.selectbox("Dashboard Said",["WAIT", "PUT", "CALL"])

        n1, n2 = st.columns(2)
        f_hold   = n1.text_input("Hold Time",   placeholder="e.g. 45 min")
        f_lesson = n2.text_input("Lesson Learned", placeholder="e.g. Don't enter when RSI < 35")
        f_notes  = st.text_area("Notes",        height=70,
                                 placeholder="What did you observe? Why did you enter?")

        ch1, ch2 = st.columns(2)
        f_brok   = ch1.number_input("Brokerage (Rs)", value=DEFAULT_BROKERAGE, step=1.0)

        if st.form_submit_button("💾 Save Trade", use_container_width=True):
            if f_entry <= 0:
                st.error("Entry price must be greater than 0.")
            else:
                saved = add_trade(
                    symbol=f_sym, option_type=f_type, strike=int(f_strike),
                    expiry=f_expiry, entry_price=f_entry, exit_price=f_exit,
                    lots=int(f_lots), lot_size=int(f_lsize),
                    entry_rsi=f_rsi, entry_adx=f_adx,
                    supertrend=f_st, dashboard_said=f_dsaid,
                    hold_time=f_hold, lessons=f_lesson, notes=f_notes,
                    brokerage=f_brok,
                )
                em = "✅ WIN" if saved["Result"]=="WIN" else ("❌ LOSS" if saved["Result"]=="LOSS" else "📂 OPEN")
                st.success("Trade #{} saved! {} | Net P&L: {}".format(
                    saved["Trade #"], em,
                    "Rs {:,.0f}".format(saved["Net P&L"]) if saved["Net P&L"] != "" else "Open"))


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ALL TRADES
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📋 All Trades":
    st.title("📋 All Trades")
    if df.empty:
        st.info("No trades yet.")
    else:
        fc1, fc2, fc3 = st.columns(3)
        syms   = ["All"] + sorted(df["Symbol"].dropna().unique().tolist())
        f_sym  = fc1.selectbox("Symbol",      syms)
        f_type = fc2.selectbox("Option Type", ["All","PUT","CALL"])
        f_res  = fc3.selectbox("Result",      ["All","WIN","LOSS","OPEN"])
        view   = df.copy()
        if f_sym  != "All": view = view[view["Symbol"]      == f_sym]
        if f_type != "All": view = view[view["Option Type"] == f_type]
        if f_res  != "All": view = view[view["Result"]      == f_res]
        st.caption("{} trades shown".format(len(view)))
        st.dataframe(view.sort_values("Trade #", ascending=False),
                     use_container_width=True, hide_index=True)
        if not view.empty:
            tot = pd.to_numeric(view["Net P&L"], errors="coerce").sum()
            d, dc = pnl_color(tot)
            st.metric("Net P&L (filtered)", "Rs {:,.0f}".format(tot), d, delta_color=dc)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 5 — MONTHLY REPORT
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📅 Monthly Report":
    st.title("📅 Monthly P&L Report")
    st.markdown("---")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        closed_df["_month"] = pd.to_datetime(closed_df["Date"], errors="coerce").dt.to_period("M")
        months  = sorted(closed_df["_month"].dropna().unique(), reverse=True)
        sel     = st.selectbox("Select Month", [str(m) for m in months] + ["All Time"])
        view    = closed_df if sel == "All Time" else closed_df[closed_df["_month"].astype(str) == sel]
        pnl_s   = pd.to_numeric(view["Net P&L"],       errors="coerce").fillna(0)
        gross_w = pd.to_numeric(view[view["Result"]=="WIN"]["Gross P&L"],  errors="coerce").sum()
        gross_l = pd.to_numeric(view[view["Result"]=="LOSS"]["Gross P&L"], errors="coerce").sum()
        brok    = pd.to_numeric(view["Brokerage"],     errors="coerce").sum()
        stt_tot = pd.to_numeric(view["STT"],           errors="coerce").sum()
        other   = pd.to_numeric(view["Other Charges"], errors="coerce").sum()
        net     = pnl_s.sum()
        cap     = pd.to_numeric(view["Capital Used"],  errors="coerce").sum()
        wins    = (view["Result"] == "WIN").sum()
        total   = len(view)

        st.subheader("📄 P&L Statement — {}".format(sel))
        st.markdown("""
<div style="background:#1e2130;border-radius:10px;padding:20px 28px;font-family:monospace;font-size:15px;line-height:2.2">
<span style="color:#3498db;font-size:16px;font-weight:bold">TRADING P&L STATEMENT — {title}</span><br>
<hr style="border-color:#333;margin:8px 0">
Trades: <b>{total}</b> &nbsp;|&nbsp; Wins: <span style="color:#26a69a"><b>{wins}</b></span> &nbsp;|&nbsp; Losses: <span style="color:#ef5350"><b>{losses}</b></span> &nbsp;|&nbsp; Win Rate: <b>{wr:.1f}%</b>
<hr style="border-color:#333;margin:8px 0">
Gross Revenue &nbsp;&nbsp;: <span style="color:#26a69a">+Rs {gw:,.2f}</span><br>
Gross Loss &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <span style="color:#ef5350"> Rs {gl:,.2f}</span><br>
<hr style="border-color:#333;margin:8px 0">
Brokerage &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <span style="color:#ef5350"> Rs {brok:,.2f}</span><br>
STT &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <span style="color:#ef5350"> Rs {stt:,.2f}</span><br>
Other Charges &nbsp;: <span style="color:#ef5350"> Rs {other:,.2f}</span><br>
<hr style="border-color:#333;margin:8px 0">
<b>NET P&L &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: <span style="color:{cls};font-size:17px">Rs {net:,.2f}</span></b><br>
<hr style="border-color:#333;margin:8px 0">
Capital Used &nbsp;&nbsp;: Rs {cap:,.2f}
</div>
""".format(
            title=sel, total=total, wins=wins, losses=total-wins,
            wr=(wins/total*100) if total else 0,
            gw=gross_w, gl=abs(gross_l), brok=brok, stt=stt_tot, other=other,
            net=net, cap=cap, cls="#26a69a" if net >= 0 else "#ef5350",
        ), unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 6 — PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📈 Performance":
    st.title("📈 Performance Analysis")
    st.markdown("---")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Win Rate",     "{:.1f}%".format(stats["win_rate"]))
        r2.metric("Reward:Risk",  "{:.2f}x".format(stats["reward_risk"]),
                  "Good ✅" if stats["reward_risk"] >= 1.5 else "Needs work ⚠️")
        r3.metric("Avg Win",      "Rs {:,.0f}".format(stats["avg_win"]))
        r4.metric("Avg Loss",     "Rs {:,.0f}".format(abs(stats["avg_loss"])))
        r5, r6, r7, r8 = st.columns(4)
        r5.metric("Best Trade",   "Rs {:,.0f}".format(stats["best_trade"]))
        r6.metric("Worst Trade",  "Rs {:,.0f}".format(stats["worst_trade"]))
        r7.metric("Max Drawdown", "Rs {:,.0f}".format(abs(stats["max_drawdown"])))
        r8.metric("Total Charges","Rs {:,.0f}".format(stats["total_charges"]))

        st.markdown("---")
        t1, t2, t3 = st.tabs(["By Symbol", "PUT vs CALL", "Dashboard Accuracy"])

        with t1:
            sg = closed_df.groupby("Symbol").apply(lambda g: pd.Series({
                "Trades":    len(g),
                "Wins":      (g["Result"]=="WIN").sum(),
                "Net P&L":   pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
                "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100, 1),
            })).reset_index()
            st.dataframe(sg, use_container_width=True, hide_index=True)

        with t2:
            tg = closed_df.groupby("Option Type").apply(lambda g: pd.Series({
                "Trades":    len(g),
                "Wins":      (g["Result"]=="WIN").sum(),
                "Net P&L":   pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
                "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100, 1),
            })).reset_index()
            st.dataframe(tg, use_container_width=True, hide_index=True)

        with t3:
            dg = closed_df.groupby("Dashboard Said").apply(lambda g: pd.Series({
                "Trades":    len(g),
                "Wins":      (g["Result"]=="WIN").sum(),
                "Net P&L":   pd.to_numeric(g["Net P&L"], errors="coerce").sum().round(2),
                "Win Rate %":round((g["Result"]=="WIN").sum()/len(g)*100, 1),
            })).reset_index()
            st.dataframe(dg, use_container_width=True, hide_index=True)
            st.caption("Tracks how accurate the dashboard signals actually are over time.")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE 7 — EXPORT
# ═════════════════════════════════════════════════════════════════════════════
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
            label="⬇️ Download Excel Report (3 sheets)",
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
st.caption("📒 Raja's Personal Trading Records | Data stored securely in Google Sheets | Not financial advice")
