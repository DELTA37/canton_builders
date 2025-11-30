import asyncio
import os
import sys
import traceback
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from python_client.client import DEFAULT_LEDGER_HOST, DEFAULT_LEDGER_PORT, RealEstateHandler

# Page configuration
st.set_page_config(
    page_title="Canton Real Estate Trading Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for trading platform
_TRADING_CSS = """
<style>
    /* Global styles */
    .main { padding-top: 1rem; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #0e1117;
        border-radius: 4px 4px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f2937;
    }

    /* Trading platform specific styles */
    .trading-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        text-align: center;
    }
    .trading-title {
        font-size: 32px;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .trading-subtitle {
        font-size: 16px;
        opacity: 0.9;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #10b981;
    }
    .metric-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-change {
        font-size: 14px;
        margin-top: 4px;
    }
    .metric-change.positive { color: #10b981; }
    .metric-change.negative { color: #ef4444; }

    /* Property cards */
    .property-card {
        background: #1e293b;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        transition: all 0.2s;
    }
    .property-card:hover {
        border-color: #6366f1;
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15);
    }
    .property-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .property-id {
        font-size: 18px;
        font-weight: 600;
        color: #f8fafc;
    }
    .property-price {
        font-size: 20px;
        font-weight: 700;
        color: #10b981;
    }
    .property-details {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 12px 0;
    }
    .property-detail {
        font-size: 14px;
        color: #cbd5e1;
    }
    .property-label {
        color: #94a3b8;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    .status-listed {
        background-color: #059669;
        color: white;
    }
    .status-unlisted {
        background-color: #6b7280;
        color: white;
    }
    .status-owned {
        background-color: #7c3aed;
        color: white;
    }

    /* Wallet styles */
    .wallet-card {
        background: #0f172a;
        border: 2px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }
    .wallet-balance {
        font-size: 32px;
        font-weight: 700;
        color: #fbbf24;
    }
    .wallet-currency {
        font-size: 14px;
        color: #94a3b8;
    }

    /* Action buttons */
    .action-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 8px;
        color: white;
        padding: 8px 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    .action-button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .danger-button {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }
    .success-button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }

    /* Search and filter styles */
    .search-container {
        background: #1e293b;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 16px;
    }

    /* Chart container */
    .chart-container {
        background: #1e293b;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }
</style>
"""

st.markdown(_TRADING_CSS, unsafe_allow_html=True)

# Initialize session state
if "current_party" not in st.session_state:
    st.session_state["current_party"] = os.getenv("LEDGER_PARTY", "Trader1")
if "role" not in st.session_state:
    st.session_state["role"] = "Trader"
if "selected_property" not in st.session_state:
    st.session_state["selected_property"] = None

def set_current_party(value: str) -> None:
    st.session_state["current_party"] = value.strip() or st.session_state["current_party"]

def current_party() -> str:
    return st.session_state["current_party"]

def run_with_handler(party_hint: str, action):
    """Execute an action with a RealEstateHandler"""
    async def _run():
        async with RealEstateHandler(host=host, port=int(port), party=party_hint) as handler:
            return await action(handler)
    return asyncio.run(_run())

@st.cache_data(ttl=30)
def load_properties(view_party: str, _host: str, _port: int) -> List[Dict[str, Any]]:
    """Load properties with caching"""
    try:
        return run_with_handler(view_party, lambda h: h.list_properties_async())
    except Exception as ex:
        st.error(f"Failed to load properties: {ex}")
        return []

@st.cache_data(ttl=60)
def load_parties(view_party: str, _host: str, _port: int) -> List[Dict[str, str]]:
    """Load parties with caching"""
    try:
        return run_with_handler(view_party, lambda h: h.list_parties_async())
    except Exception as ex:
        st.error(f"Failed to load parties: {ex}")
        return []

@st.cache_data(ttl=30)
def load_cash(view_party: str, _host: str, _port: int) -> List[Dict[str, Any]]:
    """Load cash with caching"""
    try:
        return run_with_handler(view_party, lambda h: h.list_cash_async())
    except Exception as ex:
        st.error(f"Failed to load wallet: {ex}")
        return []

def format_price(price: Any, currency: str) -> str:
    """Format price with currency"""
    if price is None:
        return "-"
    try:
        return f"${float(price):,.2f} {currency}"
    except (ValueError, TypeError):
        return f"{price} {currency}"

def calculate_market_stats(properties: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate market statistics"""
    if not properties:
        return {
            "total_properties": 0,
            "listed_properties": 0,
            "avg_price": 0,
            "total_volume": 0,
            "currencies": set()
        }

    listed_props = [p for p in properties if p.get("payload", {}).get("listed")]
    prices = []
    currencies = set()

    for prop in listed_props:
        payload = prop.get("payload", {})
        price = payload.get("price")
        currency = payload.get("currency", "USD")
        if price is not None:
            try:
                prices.append(float(price))
                currencies.add(currency)
            except (ValueError, TypeError):
                pass

    return {
        "total_properties": len(properties),
        "listed_properties": len(listed_props),
        "avg_price": sum(prices) / len(prices) if prices else 0,
        "total_volume": sum(prices) if prices else 0,
        "currencies": currencies
    }

def create_price_distribution_chart(properties: List[Dict[str, Any]]) -> go.Figure:
    """Create price distribution chart"""
    listed_props = [p for p in properties if p.get("payload", {}).get("listed")]
    if not listed_props:
        return go.Figure().add_annotation(text="No listed properties", showarrow=False)

    prices = []
    for prop in listed_props:
        price = prop.get("payload", {}).get("price")
        if price is not None:
            try:
                prices.append(float(price))
            except (ValueError, TypeError):
                pass

    if not prices:
        return go.Figure().add_annotation(text="No valid price data", showarrow=False)

    fig = px.histogram(
        x=prices,
        nbins=10,
        title="Price Distribution",
        labels={"x": "Price (USD)", "y": "Number of Properties"}
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white"
    )
    return fig

def create_property_type_chart(properties: List[Dict[str, Any]]) -> go.Figure:
    """Create property type distribution chart"""
    prop_types = {}
    for prop in properties:
        prop_type = prop.get("payload", {}).get("propertyType", "Unknown")
        prop_types[prop_type] = prop_types.get(prop_type, 0) + 1

    if not prop_types:
        return go.Figure().add_annotation(text="No property data", showarrow=False)

    fig = px.pie(
        values=list(prop_types.values()),
        names=list(prop_types.keys()),
        title="Property Types"
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="white"
    )
    return fig

# Sidebar configuration
with st.sidebar:
    st.markdown("### 🏢 Trading Platform Settings")

    # Connection settings
    st.markdown("**Ledger Connection**")
    host = st.text_input("Host", value=os.getenv("LEDGER_HOST", DEFAULT_LEDGER_HOST))
    port = st.number_input("Port", value=int(os.getenv("LEDGER_PORT", str(DEFAULT_LEDGER_PORT))), step=1)

    # Party management
    st.markdown("**Party Management**")
    known_parties = load_parties("Registrar", host, port)
    known_party_ids = [p["id"] for p in known_parties]

    if known_party_ids:
        selected_party = st.selectbox("Active Party", options=known_party_ids,
                                    index=known_party_ids.index(current_party()) if current_party() in known_party_ids else 0)
        set_current_party(selected_party)
    else:
        manual_party = st.text_input("Party ID", value=current_party())
        set_current_party(manual_party)

    # Market view settings
    st.markdown("**Market View**")
    market_party = st.selectbox("View As", options=known_party_ids if known_party_ids else [current_party()],
                               index=0)

    # Quick actions
    st.markdown("**Quick Actions**")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Header
st.markdown("""
<div class="trading-header">
    <div class="trading-title">🏢 Canton Real Estate Exchange</div>
    <div class="trading-subtitle">Professional Trading Platform for Digital Real Estate Assets</div>
</div>
""", unsafe_allow_html=True)

# Load data
properties = load_properties(market_party, host, port)
user_cash = load_cash(current_party(), host, port)
market_stats = calculate_market_stats(properties)

# Main navigation tabs
tab_dashboard, tab_marketplace, tab_portfolio, tab_wallet, tab_admin = st.tabs([
    "📊 Dashboard", "🏪 Marketplace", "📁 Portfolio", "💰 Wallet", "⚙️ Admin"
])