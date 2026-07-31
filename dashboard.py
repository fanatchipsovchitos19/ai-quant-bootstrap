"""
AI Quant Bootstrap — Dashboard
Streamlit dashboard with per-bot tabs.
Run: streamlit run dashboard.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from lib.config import load_config
from lib.journal import get_all_trades, get_pnl_summary


st.set_page_config(
    page_title="AI Quant Bootstrap",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Sidebar
# ============================================================
st.sidebar.title("🤖 AI Quant Bootstrap")
st.sidebar.caption("v1.0 — Personal Quant Trader")

try:
    config = load_config("config.yaml")
    exchange = config.general.primary_exchange.upper()
    testnet = "🧪 Testnet" if config.api_keys.binance_testnet else "💰 LIVE"
    st.sidebar.info(f"Exchange: {exchange} ({testnet})")
except Exception:
    config = None
    st.sidebar.warning("⚠️ config.yaml not loaded")

st.sidebar.divider()

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

st.sidebar.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

# ============================================================
# Load Data
# ============================================================
trades = get_all_trades()
df = pd.DataFrame(trades) if trades else pd.DataFrame()

if not df.empty:
    df["pnl"] = pd.to_numeric(df["pnl"])
    df["amount_usdt"] = pd.to_numeric(df["amount_usdt"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["price"] = pd.to_numeric(df["price"])
    df["quantity"] = pd.to_numeric(df["quantity"])

# ============================================================
# Bot Definitions
# ============================================================
BOTS = {
    "🐦 Sentiment Sniper": {
        "key": "SentimentSniper",
        "emoji": "🐦",
        "desc": "Мониторит Twitter, AI анализирует тональность, входит в лонг на 15 минут.",
        "color": "#1DA1F2",
    },
    "📊 Arbitrage Scanner": {
        "key": "ArbitrageScanner",
        "emoji": "📊",
        "desc": "Сканирует Binance/Bybit/OKX, находит спреды > 0.4%.",
        "color": "#F3BA2F",
    },
    "🤖 DCA + AI": {
        "key": "DCA_Bot",
        "emoji": "🤖",
        "desc": "Усредняет вход. AI проверяет новости перед каждой докупкой.",
        "color": "#10B981",
    },
    "🧠 Grid ML": {
        "key": "GridML",
        "emoji": "🧠",
        "desc": "Торгует в боковике. ML предсказывает диапазон на завтра.",
        "color": "#8B5CF6",
    },
    "🎯 DEX Sniper": {
        "key": "DexSniper",
        "emoji": "🎯",
        "desc": "Снайпит новые пары на PancakeSwap. AI фильтрует скамы.",
        "color": "#EF4444",
    },
}

# ============================================================
# Main
# ============================================================
st.title("📊 AI Quant Trading Dashboard")

# --- KPIs Row ---
col1, col2, col3, col4, col5 = st.columns(5)

if not df.empty:
    total_pnl = df["pnl"].sum()
    sell_trades = df[df["action"] == "SELL"]
    total_trades = len(sell_trades)
    wins = len(sell_trades[sell_trades["pnl"] > 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    total_volume = df[df["action"].isin(["BUY", "SELL"])]["amount_usdt"].sum()
    symbols_traded = df["symbol"].nunique()
else:
    total_pnl = 0
    total_trades = 0
    win_rate = 0
    total_volume = 0
    symbols_traded = 0

with col1:
    st.metric("Total PnL", f"${total_pnl:,.2f}")
with col2:
    st.metric("Closed Trades", total_trades)
with col3:
    st.metric("Win Rate", f"{win_rate:.1f}%")
with col4:
    st.metric("Volume", f"${total_volume:,.0f}")
with col5:
    st.metric("Symbols", symbols_traded)

st.divider()

# ============================================================
# Overall PnL Chart
# ============================================================
st.subheader("📈 Cumulative PnL")
if not df.empty:
    sell_df = df[df["action"] == "SELL"].sort_values("timestamp")
    if not sell_df.empty:
        sell_df["cum_pnl"] = sell_df["pnl"].cumsum()
        fig = px.line(sell_df, x="timestamp", y="cum_pnl", height=200)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_title=None, yaxis_title="USDT")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No closed trades yet.")
else:
    st.info("No data. Start the bots to see PnL chart.")

st.divider()

# ============================================================
# Per-Bot Tabs
# ============================================================
st.subheader("🤖 Bot Details")

tabs = st.tabs(list(BOTS.keys()))

for tab, (bot_name, bot_info) in zip(tabs, BOTS.items()):
    with tab:
        bot_key = bot_info["key"]
        bot_df = df[df["bot_name"] == bot_key] if not df.empty else pd.DataFrame()
        
        # Description
        st.caption(bot_info["desc"])
        
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        
        if not bot_df.empty:
            bot_sells = bot_df[bot_df["action"] == "SELL"]
            bot_pnl = bot_sells["pnl"].sum()
            bot_trades = len(bot_sells)
            bot_wins = len(bot_sells[bot_sells["pnl"] > 0])
            bot_wr = (bot_wins / bot_trades * 100) if bot_trades > 0 else 0
            bot_buys = len(bot_df[bot_df["action"] == "BUY"])
            bot_volume = bot_df[bot_df["action"].isin(["BUY", "SELL"])]["amount_usdt"].sum()
        else:
            bot_pnl = 0
            bot_trades = 0
            bot_wr = 0
            bot_buys = 0
            bot_volume = 0
        
        with m1:
            st.metric("PnL", f"${bot_pnl:,.2f}")
        with m2:
            st.metric("Trades", bot_trades)
        with m3:
            st.metric("Win Rate", f"{bot_wr:.1f}%")
        with m4:
            st.metric("Volume", f"${bot_volume:,.0f}")
        
        # Chart + Recent trades
        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.caption("PnL over time")
            if not bot_df.empty:
                bot_sells_df = bot_df[bot_df["action"] == "SELL"].sort_values("timestamp")
                if not bot_sells_df.empty:
                    bot_sells_df["cum_pnl"] = bot_sells_df["pnl"].cumsum()
                    fig = px.line(bot_sells_df, x="timestamp", y="cum_pnl", height=250)
                    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No closed trades.")
            else:
                st.info("No data.")
        
        with c2:
            st.caption("Recent activity")
            if not bot_df.empty:
                recent = bot_df.tail(10).sort_values("timestamp", ascending=False)
                recent_display = recent[["timestamp", "action", "symbol", "amount_usdt", "pnl", "reasoning"]].copy()
                recent_display["timestamp"] = recent_display["timestamp"].dt.strftime("%H:%M:%S")
                recent_display.columns = ["Time", "Action", "Symbol", "Amount", "PnL", "Reasoning"]
                st.dataframe(recent_display, use_container_width=True, hide_index=True)
            else:
                st.info("No trades recorded yet.")

# ============================================================
# All Trades Table (collapsible)
# ============================================================
st.divider()
with st.expander("📋 All Trades (CSV)"):
    if not df.empty:
        all_display = df.sort_values("timestamp", ascending=False).copy()
        all_display["timestamp"] = all_display["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(all_display, use_container_width=True, hide_index=True)
        
        csv_path = Path("data/trades.csv")
        if csv_path.exists():
            st.download_button(
                "📥 Download CSV",
                data=csv_path.read_bytes(),
                file_name="trades.csv",
                mime="text/csv"
            )
    else:
        st.info("No trades recorded.")

# --- Footer ---
st.divider()
st.caption("🤖 AI Quant Bootstrap v1.0 | Paper trades unless API keys set | Made with ❤️")