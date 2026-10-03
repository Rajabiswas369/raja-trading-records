"""
Raja's Trading Records â€” Cloud App
Accessible from any device, anywhere.
Data stored in Google Sheets â€” persistent forever.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO

from cloud_data import (
    load_trades, add_trade, delete_trade, get_stats,
    load_capital_history, update_capital, get_capital_stats,
    build_excel_report, _is_cloud,
    DEFAULT_BROKERAGE, DEFAULT_OTHER,
)
from angel_sync import render_angel_sync_panel, is_angel_configured

st.set_page_config(
    page_title="Raja's Trading Records",
    page_icon="ðŸ“’",
    layout="wide",
    initial_sidebar_state="expanded",
)

# â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.sidebar.title("ðŸ“’ Raja's Trading Records")
st.sidebar.markdown("---")

# Cloud status indicator
if _is_cloud():
    st.sidebar.success("â˜ï¸ Connected to Google Sheets")
else:
    st.sidebar.warning("ðŸ’» Running locally â€” data in memory only")

page = st.sidebar.radio("Go to", [
    "ðŸ“Š Dashboard",
    "ðŸ’° My Capital",
    "ðŸ““ Log Trade",
    "ðŸ”„ Angel One Sync",
    "ðŸ“‹ All Trades",
    "ðŸ“… Monthly Report",
    "ðŸ“ˆ Performance",
    "â¬‡ï¸ Export",
])
st.sidebar.markdown("---")
st.sidebar.caption("Data syncs to Google Sheets automatically.\nOpen from any device, anywhere.")

# â”€â”€ Load data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
df        = load_trades()
stats     = get_stats(df)
cap_stats = get_capital_stats()
closed_df = df[df["Result"].isin(["WIN", "LOSS"])].copy() if not df.empty else pd.DataFrame()


def pnl_color(val):
    d  = ("â–² Rs {:,.0f}".format(val) if val >= 0 else "â–¼ Rs {:,.0f}".format(abs(val)))
    dc = "normal" if val >= 0 else "inverse"
    return d, dc


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 1 â€” DASHBOARD
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if page == "ðŸ“Š Dashboard":
    st.title("ðŸ“Š My Trading Dashboard")
    st.markdown("---")

    # Capital health bar
    rem_pct = (cap_stats["current"] / cap_stats["initial"] * 100) if cap_stats["initial"] else 0
    cap_d, cap_dc = pnl_color(cap_stats["pnl"])
    cc1, cc2, cc3, cc4, cc5 = st.columns(5)
    cc1.metric("ðŸ’° Initial Capital",  "Rs {:,.0f}".format(cap_stats["initial"]))
    cc2.metric("ðŸ’µ Current Balance",  "Rs {:,.0f}".format(cap_stats["current"]), cap_d, delta_color=cap_dc)
    cc3.metric("ðŸ“‰ P&L",              "Rs {:,.0f}".format(cap_stats["pnl"]),
               "{:.1f}%".format(cap_stats["pnl_pct"]),
               delta_color="normal" if cap_stats["pnl"] >= 0 else "inverse")
    cc4.metric("ðŸ“… Days Trading",     "{} days".format(cap_stats["days"]))
    cc5.metric("ðŸ¦ Capital Left",     "{:.1f}%".format(rem_pct),
               delta_color="normal" if rem_pct >= 80 else "inverse")

    prog = "ðŸŸ¢" if rem_pct >= 80 else ("ðŸŸ¡" if rem_pct >= 60 else "ðŸ”´")
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
                              title="ðŸ“ˆ Equity Curve",
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
                              title="ðŸ† Win/Loss", showlegend=False,
                              margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(pie, use_container_width=True)

        # Recent trades
        st.markdown("#### ðŸ• Last 5 Trades")
        show_cols = ["Trade #","Date","Symbol","Option Type","Strike",
                     "Entry Price","Exit Price","Net P&L","Result"]
        st.dataframe(df[show_cols].tail(5).sort_index(ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet. Go to **ðŸ““ Log Trade** to record your first trade!")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 2 â€” MY CAPITAL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ’° My Capital":
    st.title("ðŸ’° My Capital Tracker")
    st.caption("Track your investment from any device. Updates saved to Google Sheets instantly.")
    st.markdown("---")

    rem_pct = (cap_stats["current"] / cap_stats["initial"] * 100) if cap_stats["initial"] else 0
    cap_d, cap_dc = pnl_color(cap_stats["pnl"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("ðŸ’° Initial",        "Rs {:,.0f}".format(cap_stats["initial"]))
    c2.metric("ðŸ’µ Current Balance","Rs {:,.0f}".format(cap_stats["current"]), cap_d, delta_color=cap_dc)
    c3.metric("ðŸ“Š Total P&L",      "Rs {:,.0f}".format(cap_stats["pnl"]),
              "{:.2f}%".format(cap_stats["pnl_pct"]),
              delta_color="normal" if cap_stats["pnl"] >= 0 else "inverse")
    c4.metric("ðŸ“… Days Trading",   "{} days".format(cap_stats["days"]))
    c5.metric("ðŸ¦ Capital Left",   "{:.1f}%".format(rem_pct),
              delta_color="normal" if rem_pct >= 80 else "inverse")

    prog = "ðŸŸ¢" if rem_pct >= 80 else ("ðŸŸ¡" if rem_pct >= 60 else "ðŸ”´")
    st.progress(min(int(rem_pct), 100),
                text="{} Rs {:,.0f} of Rs {:,.0f} remaining ({:.1f}%)".format(
                    prog, cap_stats["current"], cap_stats["initial"], rem_pct))

    st.markdown("---")

    # Update balance form
    with st.expander("âš™ï¸ Update My Balance", expanded=False):
        with st.form("cap_form"):
            uf1, uf2 = st.columns(2)
            new_bal  = uf1.number_input("New Balance (Rs)", value=float(cap_stats["current"]),
                                         step=100.0, format="%.0f")
            note_txt = uf2.text_input("Reason", placeholder="e.g. After today's trade")
            if st.form_submit_button("ðŸ’¾ Update Balance"):
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
                           title="ðŸ’µ Capital Balance Over Time",
                           xaxis_title="Date", yaxis_title="Rs",
                           margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("ðŸ“‹ Balance History")
        st.dataframe(hdf[["Date","Balance","Note"]].sort_values("Date", ascending=False),
                     use_container_width=True, hide_index=True)

    # 30-day projection
    st.markdown("---")
    st.subheader("ðŸ”® 30-Day Projection")
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
        st.caption("âš ï¸ Based on {} trade(s) only. More trades = more accurate.".format(stats["total_trades"]))
    else:
        st.info("Log trades to see your 30-day projection.")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 3 â€” LOG TRADE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ““ Log Trade":
    st.title("ðŸ““ Log a Trade")
    st.caption("Saved instantly to Google Sheets. Visible on all your devices.")
    st.markdown("---")

    # â”€â”€ Enter-key â†’ move to next field (prevents form submission on Enter) â”€â”€â”€â”€
    st.markdown("""
<script>
(function() {
    function attachEnterNav() {
        var inputs = Array.from(document.querySelectorAll(
            'input[type="number"], input[type="text"]'
        )).filter(function(el) {
            return el.closest('[data-testid="stNumberInput"], [data-testid="stTextInput"]');
        });
        inputs.forEach(function(el, idx) {
            el.removeAttribute('data-enter-nav');
            el.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    e.stopPropagation();
                    var next = inputs[idx + 1];
                    if (next) { next.focus(); next.select(); }
                }
            });
            el.setAttribute('data-enter-nav', '1');
        });
    }
    // Run once on load and again after Streamlit re-renders
    setTimeout(attachEnterNav, 800);
    var observer = new MutationObserver(function() { setTimeout(attachEnterNav, 300); });
    observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
""", unsafe_allow_html=True)


    st.subheader("Trade Details")
    c1, c2, c3, c4 = st.columns(4)
    f_sym    = c1.text_input("Symbol",      value="NIFTY50", key="cr_sym")
    f_type   = c2.selectbox("PUT / CALL",   ["PUT", "CALL"], key="cr_type")
    f_strike = c3.number_input("Strike",    value=22500, step=50, key="cr_strike")
    f_expiry = c4.text_input("Expiry",      placeholder="e.g. 06 Oct 2026", key="cr_expiry")

    c5, c6, c7, c8, c9 = st.columns([2, 2, 1, 1, 1])
    f_entry  = c5.number_input("Entry Price (Rs)", value=0.0, step=0.05, format="%.2f", min_value=0.0, key="cr_entry")
    f_exit   = c6.number_input("Exit Price (Rs) â€” 0 if open", value=0.0, step=0.05, format="%.2f", min_value=0.0, key="cr_exit")
    f_lots   = c7.number_input("Lots",      value=1, step=1, min_value=1, key="cr_lots")
    f_lsize  = c8.number_input("Lot Size",  value=75, step=1, min_value=1, key="cr_lsize")
    calc_qty = int(f_lots * f_lsize)
    c9.metric("Total Qty", f"{calc_qty:,}")

    st.subheader("Market Conditions")
    m1, m2, m3, m4 = st.columns(4)
    f_rsi    = m1.number_input("RSI",       value=50.0, step=0.1, format="%.1f", min_value=0.0, max_value=100.0, key="cr_rsi")
    f_adx    = m2.number_input("ADX",       value=25.0, step=0.1, format="%.1f", min_value=0.0, max_value=100.0, key="cr_adx")
    f_st     = m3.selectbox("Supertrend",   ["BEARISH", "BULLISH"], key="cr_st")
    f_dsaid  = m4.selectbox("Dashboard Said",["WAIT", "PUT", "CALL"], key="cr_dsaid")

    n1, n2 = st.columns(2)
    f_hold   = n1.text_input("Hold Time",   placeholder="e.g. 45 min", key="cr_hold")
    f_lesson = n2.text_input("Lesson Learned", placeholder="e.g. Don't enter when RSI < 35", key="cr_lesson")

    st.markdown("**ðŸ“ Trade Notes / Observations (Saved to Records):**")
    f_notes  = st.text_area("Notes",        height=90,
                             placeholder="What did you observe? Why did you enter?", key="cr_notes", label_visibility="collapsed")

    ch1, ch2 = st.columns(2)
    f_brok   = ch1.number_input("Brokerage (Rs)", value=DEFAULT_BROKERAGE, step=1.0, min_value=0.0, key="cr_brok")

    st.markdown("---")
    cap_preview = round(f_entry * f_lots * f_lsize, 2)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Symbol / Strike", f"{f_sym} {int(f_strike)} {f_type}")
    p2.metric("Total Quantity", f"{calc_qty:,} ({f_lots} lots)")
    p3.metric("Entry Price", f"Rs {f_entry:,.2f}")
    p4.metric("Capital Required", f"Rs {cap_preview:,.2f}")

    if f_entry <= 0:
        st.warning("âš ï¸ Please fill in an **Entry Price > 0** before clicking save.")

    if st.button("ðŸ’¾ Save Trade to Cloud Records", use_container_width=True, type="primary"):
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
            em = "âœ… WIN" if saved["Result"]=="WIN" else ("âŒ LOSS" if saved["Result"]=="LOSS" else "ðŸ“‚ OPEN")
            new_bal_msg = ""
            if saved["Result"] in ("WIN", "LOSS"):
                try:
                    net_val = float(saved.get("Net P&L") or 0)
                    new_bal_msg = " | New Balance: Rs {:,.0f}".format(cap_stats["current"] + net_val)
                except Exception:
                    pass
            st.success("Trade #{} saved! {}{}".format(
                saved["Trade #"], em, new_bal_msg))
            st.rerun()

    # â”€â”€ Recent Trades Log + Delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("---")
    st.subheader("ðŸ“‹ Recent Trades Log")
    fresh_df = load_trades()
    if fresh_df.empty:
        st.info("No trades logged yet.")
    else:
        show_cols = ["Trade #", "Date", "Symbol", "Option Type", "Strike",
                     "Entry Price", "Exit Price", "Lots", "Net P&L", "Result"]
        recent = fresh_df[show_cols].sort_values("Trade #", ascending=False).head(20)
        st.dataframe(recent, use_container_width=True, hide_index=True)

        st.markdown("#### ðŸ—‘ï¸ Delete a Trade")
        st.caption("âš ï¸ Deleting a closed trade will also reverse its impact on your capital balance.")
        del_col1, del_col2 = st.columns([2, 1])
        trade_options = fresh_df.sort_values("Trade #", ascending=False)["Trade #"].tolist()
        trade_labels  = [
            "#{} â€” {} {} {} | {}".format(
                int(r["Trade #"]), r["Date"], r["Symbol"],
                r["Option Type"],  r["Result"])
            for _, r in fresh_df.sort_values("Trade #", ascending=False).iterrows()
        ]
        sel_label = del_col1.selectbox("Select trade to delete", trade_labels, key="cr_del_sel")
        sel_num   = int(sel_label.split(" â€” ")[0].replace("#", "").strip())

        if del_col2.button("ðŸ—‘ï¸ Delete Selected Trade", type="secondary", use_container_width=True, key="cr_del_btn"):
            status = delete_trade(sel_num)
            if status == "deleted_with_capital":
                st.success("âœ… Trade #{} deleted and capital balance reversed.".format(sel_num))
            elif status == "deleted":
                st.success("âœ… Trade #{} deleted (OPEN trade â€” no capital change).".format(sel_num))
            else:
                st.error(status)
            st.rerun()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 4 â€” ALL TRADES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ“‹ All Trades":
    st.title("ðŸ“‹ All Trades")
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 5 â€” MONTHLY REPORT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ“… Monthly Report":
    st.title("ðŸ“… Monthly P&L Report")
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

        st.subheader("ðŸ“„ P&L Statement â€” {}".format(sel))
        st.markdown("""
<div style="background:#1e2130;border-radius:10px;padding:20px 28px;font-family:monospace;font-size:15px;line-height:2.2">
<span style="color:#3498db;font-size:16px;font-weight:bold">TRADING P&L STATEMENT â€” {title}</span><br>
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 6 â€” PERFORMANCE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ“ˆ Performance":
    st.title("ðŸ“ˆ Performance Analysis")
    st.markdown("---")
    if closed_df.empty:
        st.info("No closed trades yet.")
    else:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Win Rate",     "{:.1f}%".format(stats["win_rate"]))
        r2.metric("Reward:Risk",  "{:.2f}x".format(stats["reward_risk"]),
                  "Good âœ…" if stats["reward_risk"] >= 1.5 else "Needs work âš ï¸")
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PAGE 7 â€” EXPORT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
elif page == "ðŸ”„ Angel One Sync":
    st.title("ðŸ”„ Angel One Auto-Sync")
    st.caption("Automatically fetch your executed trades from Angel One â€” no manual entry needed!")
    st.markdown("---")
    render_angel_sync_panel()

elif page == "â¬‡ï¸ Export":
    st.title("â¬‡ï¸ Export Your Records")
    st.markdown("---")
    if df.empty:
        st.info("No trades to export yet.")
    else:
        st.subheader("ðŸ“Š Download Full Excel Report")
        excel_bytes = build_excel_report(df)
        today = datetime.now().strftime("%Y%m%d")
        st.download_button(
            label="â¬‡ï¸ Download Excel Report (3 sheets)",
            data=excel_bytes,
            file_name="Raja_Trading_Report_{}.xlsx".format(today),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.markdown("---")
        st.subheader("ðŸ“‹ Download CSV")
        st.download_button(
            label="â¬‡ï¸ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="Raja_Trades_{}.csv".format(today),
            mime="text/csv",
            use_container_width=True,
        )

st.markdown("---")
st.caption("ðŸ“’ Raja's Personal Trading Records | Data stored securely in Google Sheets | Not financial advice")
