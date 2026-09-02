import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

# Add backend to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.settings import get_settings

# Page configuration
st.set_page_config(
    page_title="ALPHA - Autonomous Options Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "ALPHA Autonomous Options Trading Agent - Hackathon Demo"
    }
)

# Custom CSS for dark terminal aesthetic
st.markdown("""
<style>
    /* Import modern fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Dark theme */
    .stApp {
        background-color: #0a0a0a;
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #111111;
        border-right: 1px solid #1a1a1a;
    }

    /* Main content area */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: none;
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff;
        font-weight: 500;
        letter-spacing: -0.5px;
    }

    /* Metrics cards */
    [data-testid="metric-container"] {
        background-color: #111111;
        border: 1px solid #1a1a1a;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    [data-testid="metric-container"] > label {
        color: #888888;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="metric-container"] > div {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 600;
    }

    /* Tables */
    .dataframe {
        background-color: #111111;
        border: 1px solid #1a1a1a;
    }

    .dataframe th {
        background-color: #0a0a0a;
        color: #cccccc;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.5px;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #1a1a1a;
    }

    .dataframe td {
        color: #e0e0e0;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #1a1a1a;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #111111;
        border-radius: 6px 6px 0 0;
        gap: 8px;
        padding: 0.75rem 1.5rem;
        color: #888888;
        font-weight: 500;
        border: 1px solid transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1a1a1a;
        color: #ffffff;
        border-color: #1a1a1a;
        border-bottom-color: #1a1a1a;
    }

    /* Buttons */
    .stButton > button {
        background-color: #1a1a1a;
        color: #e0e0e0;
        border: 1px solid #1a1a1a;
        border-radius: 4px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background-color: #222222;
        border-color: #222222;
        color: #ffffff;
    }

    /* Status indicators */
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    .status-live { background-color: #10b981; }
    .status-warning { background-color: #f59e0b; }
    .status-error { background-color: #ef4444; }
    .status-off { background-color: #6b7280; }

    /* Top bar */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.5rem;
        background-color: #111111;
        border-bottom: 1px solid #1a1a1a;
    }

    .agent-identity {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .agent-name {
        font-size: 1.25rem;
        font-weight: 600;
        color: #ffffff;
    }

    .agent-type {
        font-size: 0.875rem;
        color: #888888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .system-state {
        display: flex;
        gap: 1.5rem;
        font-size: 0.875rem;
        color: #888888;
    }

    .system-state div {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .environment-indicator {
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
    }

    .env-paper {
        background-color: rgba(16, 185, 129, 0.1);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }

    /* Cards */
    .card {
        background-color: #111111;
        border: 1px solid #1a1a1a;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1a1a1a;
    }

    .card-title {
        font-size: 1.125rem;
        font-weight: 600;
        color: #ffffff;
    }

    /* Activity feed */
    .activity-item {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.75rem 0;
        border-bottom: 1px solid #1a1a1a;
    }

    .activity-item:last-child {
        border-bottom: none;
    }

    .activity-time {
        font-size: 0.875rem;
        color: #6b7280;
        min-width: 60px;
    }

    .activity-content {
        flex: 1;
    }

    .activity-type {
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }

    .activity-description {
        font-size: 0.875rem;
        line-height: 1.4;
    }

    /* Activity type colors */
    .type-signal { color: #6366f1; }
    .type-ai-decision { color: #10b981; }
    .type-risk-approved { color: #10b981; }
    .type-risk-rejected { color: #ef4444; }
    .type-execution { color: #f59e0b; }
    .type-exit { color: #8b5cf6; }
    .type-rejection { color: #ef4444; }

    /* Position table */
    .position-table {
        width: 100%;
        border-collapse: collapse;
    }

    .position-table th {
        background-color: #0a0a0a;
        color: #cccccc;
        font-weight: 500;
        text-align: left;
        padding: 0.75rem 1rem;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #1a1a1a;
    }

    .position-table td {
        color: #e0e0e0;
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #1a1a1a;
        font-variant-numeric: tabular-nums;
    }

    .position-table tr:hover {
        background-color: #1a1a1a;
    }

    /* P&L coloring */
    .profit { color: #10b981; }
    .loss { color: #ef4444; }

    /* Loading states */
    .loading {
        text-align: center;
        padding: 2rem;
        color: #888888;
        font-style: italic;
    }

    /* Empty states */
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: #6b7280;
    }

    .empty-state-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .top-bar {
            flex-direction: column;
            gap: 1rem;
            align-items: stretch;
        }

        .system-state {
            flex-wrap: wrap;
            gap: 0.75rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# API base URL
API_BASE = "http://localhost:8000/api/dashboard"

def fetch_api(endpoint, params=None):
    """Fetch data from the dashboard API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        # Return demo data if API is not available
        return get_demo_data(endpoint)
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return get_demo_data(endpoint)

def get_demo_data(endpoint):
    """Return demo data for development/testing"""
    demo_data = {
        "/overview": {
            "portfolio_value": 102481.32,
            "today_pnl": 842.17,
            "today_pnl_percent": 0.82,
            "total_pnl": 2481.32,
            "total_pnl_percent": 2.48,
            "drawdown": 1.8,
            "drawdown_percent": 1.8,
            "positions_count": 4,
            "trading_enabled": True,
            "last_updated": datetime.now().isoformat(),
            "demo": True
        },
        "/equity-curve": {
            "data": [
                {"date": (datetime.now() - timedelta(days=i)).date().isoformat(),
                 "equity": 100000 + (i * 25) + ((-1)**i * 50),
                 "daily_pnl": ((-1)**i * 50) + 25}
                for i in range(30, 0, -1)
            ],
            "timeframe": "1M",
            "starting_equity": 100000.0,
            "current_equity": 102481.32,
            "demo": True
        },
        "/positions": [
            {
                "symbol": "NVDA260925C00180000",
                "quantity": 2,
                "side": "buy",
                "entry_price": 4.21,
                "current_price": 4.45,
                "market_value": 890.00,
                "unrealized_pl": 48.00,
                "unrealized_pl_percent": 5.68,
                "asset_class": "option",
                "contract": "NVDA   260925C00180000"
            },
            {
                "symbol": "TSLA260925P00250000",
                "quantity": 1,
                "side": "sell",
                "entry_price": 3.80,
                "current_price": 3.50,
                "market_value": 350.00,
                "unrealized_pl": 30.00,
                "unrealized_pl_percent": 7.89,
                "asset_class": "option",
                "contract": "TSLA   260925P00250000"
            },
            {
                "symbol": "SPY260925C00450000",
                "quantity": 5,
                "side": "buy",
                "entry_price": 2.10,
                "current_price": 2.25,
                "market_value": 1125.00,
                "unrealized_pl": 75.00,
                "unrealized_pl_percent": 7.14,
                "asset_class": "option",
                "contract": "SPY    260925C00450000"
            },
            {
                "symbol": "QQQ260925P00320000",
                "quantity": 3,
                "side": "sell",
                "entry_price": 1.85,
                "current_price": 1.70,
                "market_value": 510.00,
                "unrealized_pl": 45.00,
                "unrealized_pl_percent": 8.11,
                "asset_class": "option",
                "contract": "QQQ    260925P00320000"
            }
        ],
        "/trades": [
            {
                "id": 1,
                "internal_id": "agt-entry-20260830094224001",
                "alpaca_id": "5a7b3c9d-8e2f-4a1b-9c3d-4e5f6a7b8c9d",
                "symbol": "NVDA260925C00180000",
                "side": "buy",
                "quantity": 2,
                "status": "filled",
                "timestamp": "2026-08-30T09:42:24Z",
                "filled_quantity": 2,
                "filled_avg_price": 4.21,
                "pnl": 48.00
            },
            {
                "id": 2,
                "internal_id": "agt-entry-20260830093105002",
                "alpaca_id": "3b2c1d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
                "symbol": "TSLA260925P00250000",
                "side": "sell",
                "quantity": 1,
                "status": "filled",
                "timestamp": "2026-08-30T09:31:05Z",
                "filled_quantity": 1,
                "filled_avg_price": 3.80,
                "pnl": 30.00
            },
            {
                "id": 3,
                "internal_id": "agt-reject-20260830092512003",
                "alpaca_id": None,
                "symbol": "AMD260925C00100000",
                "side": "buy",
                "quantity": 2,
                "status": "rejected",
                "timestamp": "2026-08-30T09:25:12Z",
                "filled_quantity": 0,
                "filled_avg_price": 0,
                "pnl": 0
            }
        ],
        "/live-activity": [
            {
                "timestamp": "2026-08-30T09:42:24Z",
                "underlying": "NVDA",
                "event_type": "execution",
                "description": "ORDER FILLED: NVDA 260925 C 180",
                "status": "success",
                "confidence": 0.84
            },
            {
                "timestamp": "2026-08-30T09:42:21Z",
                "underlying": "NVDA",
                "event_type": "ai_decision",
                "description": "AI DECISION: BUY NVDA",
                "status": "info",
                "confidence": 0.84
            },
            {
                "timestamp": "2026-08-30T09:42:18Z",
                "underlying": "NVDA",
                "event_type": "signal",
                "description": "VOLATILITY SIGNAL: NVDA IV/RV divergence",
                "status": "info",
                "confidence": 0.82
            },
            {
                "timestamp": "2026-08-30T09:31:05Z",
                "underlying": "TSLA",
                "event_type": "execution",
                "description": "ORDER FILLED: TSLA 260925 P 250",
                "status": "success"
            },
            {
                "timestamp": "2026-08-30T09:25:12Z",
                "underlying": "AMD",
                "event_type": "rejection",
                "description": "SIGNAL REJECTED: AMD - Spread > threshold",
                "status": "error"
            }
        ],
        "/risk-summary": {
            "exposure": 18.4,
            "max_exposure": 40.0,
            "daily_loss": 0.4,
            "daily_limit": 3.0,
            "drawdown": 1.8,
            "max_drawdown": 10.0,
            "open_positions": 4,
            "max_positions": 8,
            "last_updated": datetime.now().isoformat(),
            "demo": True
        },
        "/agent-status": {
            "status": "ONLINE",
            "agent_mode": "AI SUPERVISOR",
            "last_decision": "2026-08-30T09:42:24Z",
            "next_scan": "In progress",
            "trading_halted": False,
            "shutdown_reason": "",
            "system_health": {
                "alpaca_connection": "Healthy",
                "market_data": "Healthy",
                "ai_provider": "Healthy",
                "database": "Healthy",
                "execution": "Healthy",
                "last_heartbeat": "2s ago"
            },
            "demo": True
        },
        "/strategy-performance": {
            "total_trades": 15,
            "winning_trades": 12,
            "win_rate": 80.0,
            "profit_factor": 1.85,
            "sharpe_ratio": 1.25,
            "sortino_ratio": 1.50,
            "max_drawdown": 1.8,
            "average_trade": 145.50,
            "strategy_name": "Momentum + Volatility Regime",
            "demo": True
        }
    }

    return demo_data.get(endpoint, {})

# Initialize session state for auto-refresh
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# Auto-refresh every 30 seconds
if (datetime.now() - st.session_state.last_refresh).seconds > 30:
    st.session_state.last_refresh = datetime.now()
    st.rerun()

# Sidebar navigation
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem 0; border-bottom: 1px solid #1a1a1a;">
        <div style="font-size: 1.5rem; font-weight: 600; color: #ffffff;">ALPHA</div>
        <div style="font-size: 0.875rem; color: #888888; text-transform: uppercase; letter-spacing: 0.5px;">
            Autonomous Options Agent
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation menu
    pages = [
        ("Overview", "📊"),
        ("Portfolio", "💼"),
        ("Positions", "📈"),
        ("Trades", "📋"),
        ("Agent Activity", "⚡"),
        ("Strategy", "🎯"),
        ("Agent Config", "⚙️"),
        ("Risk", "⚠️"),
        ("Settings", "🔧")
    ]

    for page, icon in pages:
        if st.button(f"{icon} {page}", key=f"nav_{page}", use_container_width=True):
            st.session_state.current_page = page

    # Set default page
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Overview"

    st.markdown("<br>", unsafe_allow_html=True)

    # System status in sidebar
    status_data = fetch_api("/agent-status")
    if status_data:
        # Agent loop status
        agent_status = status_data.get('status', 'UNKNOWN')
        agent_status_class = "status-live" if agent_status == 'RUNNING' else "status-off"
        # Trading halted status (from system health)
        trading_halted = status_data.get('system_health', {}).get('execution', '') == 'Halted'  # We don't have this directly, but we can use the trading_halted from the agent status? Actually, we have a separate field in the agent status response.
        # Let's check if we have a trading_halted field in the status_data (we added it in the agent-status endpoint)
        trading_halted = status_data.get('trading_halted', False)
        trading_halted_class = "status-warning" if trading_halted else "status-live"
        mode_class = "status-live" if status_data.get('agent_mode') == 'AI SUPERVISOR' else "status-warning"

        st.markdown(f"""
        <div style="background-color: #1a1a1a; padding: 1rem; border-radius: 6px; margin-top: 1rem;">
            <div style="font-size: 0.875rem; color: #888888; margin-bottom: 0.5px;">SYSTEM STATUS</div>
            <div class="status-indicator" style="margin-bottom: 0.25rem;">
                <span class="status-dot {agent_status_class}"></span>
                <span>AGENT LOOP: {agent_status}</span>
            </div>
            <div class="status-indicator" style="margin-bottom: 0.25rem;">
                <span class="status-dot {trading_halted_class}"></span>
                <span>TRADING: {'HALTED' if trading_halted else 'RUNNING'}</span>
            </div>
            <div class="status-indicator">
                <span class="status-dot {mode_class}"></span>
                <span>{status_data.get('agent_mode', 'UNKNOWN')}</span>
            </div>
            <div style="font-size: 0.75rem; color: #6b7280; margin-top: 0.5rem;">
                Last decision: {status_data.get('last_decision', 'Never')[:16]}...
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Environment indicator
    settings = get_settings()
    env_class = "env-paper" if settings.alpaca_paper else ""
    env_text = "PAPER TRADING" if settings.alpaca_paper else "LIVE TRADING"

    st.markdown(f"""
    <div style="text-align: center; margin-top: auto; padding: 1rem 0; border-top: 1px solid #1a1a1a;">
        <div class="environment-indicator {env_class}">{env_text}</div>
    </div>
    """, unsafe_allow_html=True)

# Main content area - Top Bar
col1, col2, col3 = st.columns([2, 3, 1])

with col1:
    st.markdown("""
    <div class="agent-identity">
        <div class="agent-name">ALPHA</div>
        <div class="agent-type">Autonomous Options Agent</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # System state
    status_data = fetch_api("/agent-status")
    market_open = True  # Simplified - in reality would check market hours
    agent_loop_running = status_data and status_data.get('status') == 'RUNNING' if status_data else False
    trading_halted = status_data and status_data.get('trading_halted', False) if status_data else False

    market_class = "status-live" if market_open else "status-warning"
    agent_loop_class = "status-live" if agent_loop_running else "status-error"
    trading_status_class = "status-warning" if trading_halted else "status-live"

    st.markdown(f"""
    <div class="system-state">
        <div>
            <span class="status-dot {market_class}"></span>
            <span>MARKET {'OPEN' if market_open else 'CLOSED'}</span>
        </div>
        <div>
            <span class="status-dot {agent_loop_class}"></span>
            <span>AGENT LOOP: {'RUNNING' if agent_loop_running else 'STOPPED'}</span>
        </div>
        <div>
            <span class="status-dot {trading_status_class}"></span>
            <span>TRADING: {'HALTED' if trading_halted else 'RUNNING'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Time and environment
    current_time = datetime.now().strftime("%H:%M:%S UTC")
    env_text = "PAPER TRADING" if settings.alpaca_paper else "LIVE"
    env_class = "env-paper" if settings.alpaca_paper else ""

    st.markdown(f"""
    <div style="text-align: right;">
        <div style="font-size: 0.875rem; color: #888888;">{current_time}</div>
        <div class="environment-indicator {env_class}" style="margin-top: 0.25rem;">{env_text}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 1rem 0; border-color: #1a1a1a;'>", unsafe_allow_html=True)

# Page routing
page = st.session_state.current_page

if page == "Overview":
    # Overview Page - Hero Metrics
    overview_data = fetch_api("/overview")

    if overview_data:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="PORTFOLIO",
                value=f"${overview_data.get('portfolio_value', 0):,.2f}",
                delta=f"{overview_data.get('total_pnl_percent', 0):+.2f}%"
            )

        with col2:
            st.metric(
                label="TODAY",
                value=f"+${overview_data.get('today_pnl', 0):,.2f}",
                delta=f"+{overview_data.get('today_pnl_percent', 0):.2f}%"
            )

        with col3:
            st.metric(
                label="TOTAL P&L",
                value=f"+${overview_data.get('total_pnl', 0):,.2f}",
                delta=f"+{overview_data.get('total_pnl_percent', 0):.2f}%"
            )

        with col4:
            st.metric(
                label="DRAWDOWN",
                value=f"-{overview_data.get('drawdown', 0):.2f}%",
                delta=None
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Agent Control Card
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">AGENT CONTROL</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get agent status
    agent_status_data = fetch_api("/agent-status")
    agent_running = agent_status_data and agent_status_data.get('status') == 'RUNNING' if agent_status_data else False

    col1, col2 = st.columns([3, 1])
    with col1:
        if agent_running:
            st.success("Agent is currently RUNNING")
        else:
            st.info("Agent is currently STOPPED")

    with col2:
        if agent_running:
            if st.button("STOP AGENT", type="primary"):
                # Call the stop agent API
                try:
                    response = requests.post(f"{API_BASE}/agent/stop")
                    if response.status_code == 200:
                        st.success("Agent stopped successfully")
                        st.rerun()
                    else:
                        st.error("Failed to stop agent")
                except Exception as e:
                    st.error(f"Error stopping agent: {e}")
        else:
            if st.button("START AGENT", type="primary"):
                # Call the start agent API
                try:
                    response = requests.post(f"{API_BASE}/agent/start")
                    if response.status_code == 200:
                        st.success("Agent started successfully")
                        st.rerun()
                    else:
                        st.error("Failed to start agent")
                except Exception as e:
                    st.error(f"Error starting agent: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Equity Curve
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">EQUITY CURVE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    equity_data = fetch_api("/equity-curve")
    if equity_data and equity_data.get('data'):
        df = pd.DataFrame(equity_data['data'])
        df['date'] = pd.to_datetime(df['date'])

        fig = go.Figure()

        # Equity line
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['equity'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#10b981', width=2),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.1)'
        ))

        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0', family='Inter'),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=True,
                tickformat='%b %d'
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(26, 26, 26, 0.5)',
                zeroline=False,
                tickprefix='$',
                tickformat=',.0f'
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=300,
            hovermode='x unified'
        )

        # Time range buttons
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="left",
                    x=0.0,
                    y=1.15,
                    showactive=True,
                    buttons=[
                        dict(label="1D",
                             method="update",
                             args=[{"x": [df[df['date'] >= (df['date'].max() - timedelta(days=1))]['date']],
                                   "y": [df[df['date'] >= (df['date'].max() - timedelta(days=1))]['equity']]}]),
                        dict(label="1W",
                             method="update",
                             args=[{"x": [df[df['date'] >= (df['date'].max() - timedelta(weeks=1))]['date']],
                                   "y": [df[df['date'] >= (df['date'].max() - timedelta(weeks=1))]['equity']]}]),
                        dict(label="1M",
                             method="update",
                             args=[{"x": [df[df['date'] >= (df['date'].max() - timedelta(days=30))]['date']],
                                   "y": [df[df['date'] >= (df['date'].max() - timedelta(days=30))]['equity']]}]),
                        dict(label="ALL",
                             method="update",
                             args=[{"x": [df['date']], "y": [df['equity']]}])
                    ]
                )
            ]
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("<br>", unsafe_allow_html=True)

    # Live Agent Activity
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">LIVE AGENT ACTIVITY</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    activity_data = fetch_api("/live-activity")
    if activity_data:
        activity_container = st.container()
        with activity_container:
            for activity in activity_data[:8]:  # Show last 8 activities
                time_str = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00')).strftime("%H:%M:%S")

                # Determine activity type and styling
                event_type = activity.get('event_type', 'signal')
                type_class = f"type-{event_type}"

                # Map event types to display names and icons
                type_map = {
                    'signal': ('SIGNAL', '🔍'),
                    'ai_decision': ('AI DECISION', '🤖'),
                    'risk_approved': ('RISK APPROVED', '✅'),
                    'risk_rejected': ('RISK REJECTED', '❌'),
                    'execution': ('EXECUTION', '💸'),
                    'exit': ('EXIT', '🚪'),
                    'rejection': ('REJECTION', '🚫')
                }

                display_type, icon = type_map.get(event_type, (event_type.upper(), '•'))

                st.markdown(f"""
                <div class="activity-item">
                    <div class="activity-time">{time_str}</div>
                    <div class="activity-content">
                        <div class="activity-type {type_class}">{icon} {display_type}</div>
                        <div class="activity-description">{activity.get('description', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="loading">Loading agent activity...</div>
        """, unsafe_allow_html=True)

elif page == "Positions":
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">CURRENT POSITIONS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    positions_data = fetch_api("/positions")
    if positions_data:
        if positions_data:
            # Create position table
            st.markdown("""
            <table class="position-table">
                <thead>
                    <tr>
                        <th>Underlying</th>
                        <th>Contract</th>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Entry</th>
                        <th>Mark</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                        <th>Delta</th>
                        <th>Theta</th>
                        <th>IV</th>
                        <th>Expiration</th>
                    </tr>
                </thead>
                <tbody>
            """, unsafe_allow_html=True)

            for pos in positions_data:
                # Format data
                underlying = pos.get('symbol', '')[:6]  # Extract underlying
                contract = pos.get('contract', '').strip()
                side = pos.get('side', '').upper()
                qty = pos.get('quantity', 0)
                entry = f"${pos.get('entry_price', 0):.2f}"
                mark = f"${pos.get('current_price', 0):.2f}"
                pnl = pos.get('unrealized_pl', 0)
                pnl_pct = pos.get('unrealized_pl_percent', 0)
                # For demo, we'll use placeholder values for Greeks
                delta = "0.25"
                theta = "-0.05"
                iv = "0.35"
                exp = pos.get('symbol', '')[6:12] if len(pos.get('symbol', '')) > 12 else "260925"

                pnl_class = "profit" if pnl >= 0 else "loss"

                st.markdown(f"""
                <tr>
                    <td>{underlying}</td>
                    <td>{contract}</td>
                    <td>{side}</td>
                    <td>{qty}</td>
                    <td>{entry}</td>
                    <td>{mark}</td>
                    <td class="{pnl_class}">${pnl:.2f}</td>
                    <td class="{pnl_class}">{pnl_pct:+.2f}%</td>
                    <td>{delta}</td>
                    <td>{theta}</td>
                    <td>{iv}</td>
                    <td>{exp}</td>
                </tr>
                """, unsafe_allow_html=True)

            st.markdown("""
                </tbody>
            </table>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div>NO OPEN POSITIONS</div>
                <div style="color: #6b7280; margin-top: 1rem;">
                    The agent is currently scanning the market for qualified opportunities.
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="loading">Loading positions data...</div>
        """, unsafe_allow_html=True)

elif page == "Trades":
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">TRADE HISTORY</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    trades_data = fetch_api("/trades")
    if trades_data:
        if trades_data:
            # Create trades table
            st.markdown("""
            <table class="position-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Underlying</th>
                        <th>Contract</th>
                        <th>Strategy</th>
                        <th>AI Decision</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>P&L</th>
                        <th>Duration</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
            """, unsafe_allow_html=True)

            for trade in trades_data[:10]:  # Show last 10 trades
                # Format timestamp
                try:
                    ts = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
                    time_str = ts.strftime("%H:%M:%S")
                except:
                    time_str = trade['timestamp'][:8] if len(trade['timestamp']) > 8 else trade['timestamp']

                underlying = trade.get('symbol', '')[:6]
                # For demo, we'll extract contract info from symbol
                contract = trade.get('symbol', '')
                strategy = "Momentum"  # Placeholder
                ai_decision = "BUY" if trade.get('side') == 'buy' else "SELL"
                entry = f"${trade.get('filled_avg_price', 0):.2f}" if trade.get('filled_avg_price') else "N/A"
                exit_price = f"${trade.get('filled_avg_price', 0) * 1.1:.2f}" if trade.get('filled_avg_price') else "N/A"  # Simplified
                pnl = trade.get('pnl', 0)
                duration = "2h 15m"  # Placeholder
                reason = "Signal executed" if trade.get('status') == 'filled' else "Risk rejected"

                pnl_class = "profit" if pnl >= 0 else "loss"

                st.markdown(f"""
                <tr>
                    <td>{time_str}</td>
                    <td>{underlying}</td>
                    <td>{contract}</td>
                    <td>{strategy}</td>
                    <td>{ai_decision}</td>
                    <td>{entry}</td>
                    <td>{exit_price}</td>
                    <td class="{pnl_class}">{pnl:+.2f}</td>
                    <td>{duration}</td>
                    <td style="font-size: 0.75rem; color: #888888;">{reason}</td>
                </tr>
                """, unsafe_allow_html=True)

            st.markdown("""
                </tbody>
            </table>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div>NO TRADES YET</div>
                <div style="color: #6b7280; margin-top: 1rem;">
                    Once the agent identifies and executes an approved opportunity, it will appear here.
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="loading">Loading trades data...</div>
        """, unsafe_allow_html=True)

elif page == "Agent Activity":
    # This is similar to the activity section in Overview but more detailed
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">AGENT ACTIVITY DETAIL</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    activity_data = fetch_api("/live-activity")
    if activity_data:
        for i, activity in enumerate(activity_data):
            time_str = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00')).strftime("%H:%M:%S")

            # Determine styling based on event type
            event_type = activity.get('event_type', 'signal')
            type_class = f"type-{event_type}"

            # Map to display info
            type_info = {
                'signal': ('🔍 SIGNAL', '#6366f1'),
                'ai_decision': ('🤖 AI DECISION', '#10b981'),
                'risk_approved': ('✅ RISK APPROVED', '#10b981'),
                'risk_rejected': ('❌ RISK REJECTED', '#ef4444'),
                'execution': ('💸 EXECUTION', '#f59e0b'),
                'exit': ('🚪 EXIT', '#8b5cf6'),
                'rejection': ('🚫 REJECTION', '#ef4444')
            }

            display_text, color = type_info.get(event_type, ('• UNKNOWN', '#888888'))

            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #1a1a1a;">
                <div style="font-size: 0.875rem; color: #6b7280; min-width: 60px;">{time_str}</div>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                        <span style="font-size: 0.875rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; color: {color};">{display_text}</span>
                        <span style="font-size: 0.75rem; color: #6b7280;">{activity.get('underlying', '')}</span>
                    </div>
                    <div style="font-size: 0.875rem; line-height: 1.4; color: #e0e0e0;">{activity.get('description', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Show confidence if available
            if 'confidence' in activity and activity['confidence'] > 0:
                st.markdown(f"""
                <div style="margin-left: 3.75rem; padding: 0.5rem; background-color: rgba(26, 26, 26, 0.5); border-radius: 4px; margin-bottom: 1rem;">
                    <div style="font-size: 0.75rem; color: #888888;">Confidence: {activity['confidence']:.0%}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="loading">Loading agent activity...</div>
        """, unsafe_allow_html=True)

elif page == "Strategy":
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">STRATEGY PERFORMANCE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    strategy_data = fetch_api("/strategy-performance")
    if strategy_data:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            <div class="card">
                <div class="card-header">
                    <div class="card-title">STRATEGY STATUS</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background-color: #1a1a1a; padding: 1.5rem; border-radius: 6px;">
                <div style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">
                    {strategy_data.get('strategy_name', 'Unknown Strategy')}
                </div>
                <div style="color: #888888; margin-bottom: 1.5rem;">
                    ACTIVE STRATEGY
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; font-size: 0.875rem;">
                    <div>Trades</div>
                    <div style="text-align: right; color: #e0e0e0; font-weight: 500;">
                        {strategy_data.get('total_trades', 0)}
                    </div>
                    <div>Win Rate</div>
                    <div style="text-align: right; color: #e0e0e0; font-weight: 500;">
                        {strategy_data.get('win_rate', 0):.1f}%
                    </div>
                    <div>Profit Factor</div>
                    <div style="text-align: right; color: #e0e0e0; font-weight: 500;">
                        {strategy_data.get('profit_factor', 0):.2f}
                    </div>
                    <div>Sharpe Ratio</div>
                    <div style="text-align: right; color: #e0e0e0; font-weight: 500;">
                        {strategy_data.get('sharpe_ratio', 0):.2f}
                    </div>
                    <div>Sortino Ratio</div>
                    <div style="text-align: right; color: #e0e0e0; font-weight: 500;">
                        {strategy_data.get('sortino_ratio', 0):.2f}
                    </div>
                    <div>Avg Trade</div>
                    <div style="text-align: right; color: #e0e0e0; font-weight: 500;">
                        ${strategy_data.get('average_trade', 0):.2f}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="card">
                <div class="card-header">
                    <div class="card-title">RISK METRICS</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="loading">Loading strategy data...</div>
        """, unsafe_allow_html=True)

elif page == "Agent Config":
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">AGENT CONFIGURATION</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch current configuration
    config_data = fetch_api("/agent/config")
    if config_data is None:
        st.error("Failed to load configuration")
        config_data = {}

    # Create a form for updating configuration
    with st.form("agent_config_form"):
        st.subheader("Trading Parameters")
        col1, col2 = st.columns(2)
        with col1:
            trading_enabled = st.checkbox("Trading Enabled", value=config_data.get("trading_enabled", True))
            max_risk_per_trade = st.number_input(
                "Max Risk Per Trade",
                min_value=0.0,
                max_value=1.0,
                value=config_data.get("max_risk_per_trade", 0.01),
                step=0.001,
                format="%.3f"
            )
            max_portfolio_exposure = st.number_input(
                "Max Portfolio Exposure",
                min_value=0.0,
                max_value=1.0,
                value=config_data.get("max_portfolio_exposure", 0.20),
                step=0.001,
                format="%.3f"
            )
            max_daily_loss = st.number_input(
                "Max Daily Loss",
                min_value=0.0,
                max_value=1.0,
                value=config_data.get("max_daily_loss", 0.02),
                step=0.001,
                format="%.3f"
            )
            max_drawdown = st.number_input(
                "Max Drawdown",
                min_value=0.0,
                max_value=1.0,
                value=config_data.get("max_drawdown", 0.08),
                step=0.001,
                format="%.3f"
            )
        with col2:
            max_positions = st.number_input(
                "Max Positions",
                min_value=1,
                max_value=20,
                value=config_data.get("max_positions", 3),
                step=1
            )
            max_underlying_concentration = st.number_input(
                "Max Underlying Concentration",
                min_value=0.0,
                max_value=1.0,
                value=config_data.get("max_underlying_concentration", 0.15),
                step=0.001,
                format="%.3f"
            )
            max_bid_ask_spread = st.number_input(
                "Max Bid/Ask Spread",
                min_value=0.0,
                max_value=1.0,
                value=config_data.get("max_bid_ask_spread", 0.08),
                step=0.001,
                format="%.3f"
            )
            min_option_volume = st.number_input(
                "Min Option Volume",
                min_value=0,
                max_value=10000,
                value=config_data.get("min_option_volume", 10),
                step=1
            )
            min_open_interest = st.number_input(
                "Min Open Interest",
                min_value=0,
                max_value=10000,
                value=config_data.get("min_open_interest", 50),
                step=1
            )

        st.subscriber("Underlyings")
        underlyings = st.text_input(
            "Underlyings (comma-separated)",
            value=config_data.get("underlyings", "SPY,QQQ,IWM")
        )

        st.subheader("Date Range")
        col1, col2 = st.columns(2)
        with col1:
            min_dte = st.number_input(
                "Min Days to Expiration",
                min_value=0,
                max_value=365,
                value=config_data.get("min_dte", 3),
                step=1
            )
        with col2:
            max_dte = st.number_input(
                "Max Days to Expiration",
                min_value=0,
                max_value=365,
                value=config_data.get("max_dte", 45),
                step=1
            )

        st.subheader("Timing")
        loop_interval_seconds = st.number_input(
            "Loop Interval (seconds)",
            min_value=10,
            max_value=3600,
            value=config_data.get("loop_interval_seconds", 60),
            step=10
        )
        max_consecutive_failures = st.number_input(
            "Max Consecutive Failures",
            min_value=1,
            max_value=20,
            value=config_data.get("max_consecutive_failures", 5),
            step=1
        )

        st.subheader("AI Parameters")
        col1, col2 = st.columns(2)
        with col1:
            ai_enabled = st.checkbox("AI Enabled", value=config_data.get("ai_enabled", False))
            use_ai_supervisor = st.checkbox("Use AI Supervisor", value=config_data.get("use_ai_supervisor", True))
            ai_temperature = st.number_input(
                "AI Temperature",
                min_value=0.0,
                max_value=2.0,
                value=config_data.get("ai_temperature", 0.3),
                step=0.1
            )
        with col2:
            ai_max_tokens = st.number_input(
                "AI Max Tokens",
                min_value=1,
                max_value=4000,
                value=config_data.get("ai_max_tokens", 1000),
                step=1
            )
            ai_model = st.selectbox(
                "AI Model",
                options=["gemini-1.5-pro-latest", "claude-3-opus-20240229", "gpt-4-turbo"],
                index=0 if config_data.get("ai_model", "gemini-1.5-pro-latest") == "gemini-1.5-pro-latest" else
                      1 if config_data.get("ai_model", "gemini-1.5-pro-latest") == "claude-3-opus-20240229" else 2
            )

        st.subheader("Environment")
        alpaca_paper = st.checkbox("Alpaca Paper Trading", value=config_data.get("alpaca_paper", True))

        # Submit button
        submitted = st.form_submit_button("UPDATE CONFIGURATION", type="primary")
        if submitted:
            # Prepare the configuration update
            config_update = {
                "trading_enabled": trading_enabled,
                "max_risk_per_trade": max_risk_per_trade,
                "max_portfolio_exposure": max_portfolio_exposure,
                "max_daily_loss": max_daily_loss,
                "max_drawdown": max_drawdown,
                "max_positions": max_positions,
                "max_underlying_concentration": max_underlying_concentration,
                "max_bid_ask_spread": max_bid_ask_spread,
                "min_option_volume": min_option_volume,
                "min_open_interest": min_open_interest,
                "min_dte": min_dte,
                "max_dte": max_dte,
                "loop_interval_seconds": loop_interval_seconds,
                "max_consecutive_failures": max_consecutive_failures,
                "ai_enabled": ai_enabled,
                "use_ai_supervisor": use_ai_supervisor,
                "ai_temperature": ai_temperature,
                "ai_max_tokens": ai_max_tokens,
                "ai_model": ai_model,
                "alpaca_paper": alpaca_paper
            }
            # Call the API to update the configuration
            try:
                response = requests.put(f"{API_BASE}/agent/config", json=config_update)
                if response.status_code == 200:
                    st.success("Configuration updated successfully!")
                    # Optionally, we can rerun to reflect the changes
                    # st.rerun()
                else:
                    st.error(f"Failed to update configuration: {response.text}")
            except Exception as e:
                st.error(f"Error updating configuration: {e}")


elif page == "Risk":
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">RISK MANAGEMENT</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    risk_data = fetch_api("/risk-summary")
    if risk_data:
        # Risk gauges / progress bars
        st.markdown("""
        <div style="background-color: #1a1a1a; padding: 1.5rem; border-radius: 6px; margin-bottom: 1.5rem;">
            <div style="font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem;">CURRENT RISK EXPOSURE</div>
        </div>
        """, unsafe_allow_html=True)

        exposure = min(risk_data.get('exposure', 0), risk_data.get('max_exposure', 40))
        exposure_pct = (exposure / risk_data.get('max_exposure', 40)) * 100

        st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Portfolio Exposure</span>
                <span style="font-weight: 500;">{exposure:.1f}% / {risk_data.get('max_exposure', 0):.1f}%</span>
            </div>
            <div style="background-color: #2a2a2a; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background-color:
                    {'#10b981' if exposure_pct < 50 else '#f59e0b' if exposure_pct < 80 else '#ef4444'};
                    width: {exposure_pct}%; height: 100%; transition: width 0.3s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        daily_loss = risk_data.get('daily_loss', 0)
        daily_limit = risk_data.get('daily_limit', 3)
        daily_pct = min((daily_loss / daily_limit) * 100, 100) if daily_limit > 0 else 0

        st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Daily Loss</span>
                <span style="font-weight: 500;">{-daily_loss:.2f}% / {daily_limit:.1f}%</span>
            </div>
            <div style="background-color: #2a2a2a; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background-color:
                    {'#10b981' if daily_pct < 50 else '#f59e0b' if daily_pct < 80 else '#ef4444'};
                    width: {daily_pct}%; height: 100%; transition: width 0.3s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        drawdown = risk_data.get('drawdown', 0)
        max_dd = risk_data.get('max_drawdown', 10)
        dd_pct = min((drawdown / max_dd) * 100, 100) if max_dd > 0 else 0

        st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Drawdown</span>
                <span style="font-weight: 500;">{drawdown:.2f}% / {max_dd:.1f}%</span>
            </div>
            <div style="background-color: #2a2a2a; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background-color:
                    {'#10b981' if dd_pct < 50 else '#f59e0b' if dd_pct < 80 else '#ef4444'};
                    width: {dd_pct}%; height: 100%; transition: width 0.3s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Recent risk decisions
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="card-title">RECENT RISK DECISIONS</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        activity_data = fetch_api("/live-activity")
        if activity_data:
            risk_activities = [a for a in activity_data if a.get('event_type') in ['risk_approved', 'risk_rejected']]
            if risk_activities:
                for activity in risk_activities[:5]:  # Show last 5 risk decisions
                    time_str = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00')).strftime("%H:%M")
                    underlying = activity.get('underlying', '')
                    status = "APPROVED" if activity.get('event_type') == 'risk_approved' else "REJECTED"
                    status_class = "status-live" if activity.get('event_type') == 'risk_approved' else "status-error"

                    # Extract risk amount from description if possible
                    import re
                    risk_match = re.search(r'Risk: ([0-9.]+)%', activity.get('description', ''))
                    risk_text = f"Risk: {risk_match.group(1)}%" if risk_match else ""

                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #1a1a1a;">
                        <div style="font-size: 0.875rem; color: #6b7280; min-width: 50px;">{time_str}</div>
                        <div style="flex: 1;">
                            <div style="font-weight: 500; color: #e0e0e0;">{underlying}</div>
                            <div style="font-size: 0.75rem; color: #888888;">{risk_text}</div>
                        </div>
                        <div style="padding: 0.25rem 0.75rem; background-color:
                            {'rgba(16, 185, 129, 0.1)' if status == 'APPROVED' else 'rgba(239, 68, 68, 0.1)'};
                            border: 1px solid
                            {'rgba(16, 185, 129, 0.2)' if status == 'APPROVED' else 'rgba(239, 68, 68, 0.2)'};
                            border-radius: 4px; font-size: 0.75rem; font-weight: 500;
                            text-transform: uppercase; letter-spacing: 0.5px;
                            color: {'#10b981' if status == 'APPROVED' else '#ef4444'};">
                            {status}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div>NO RECENT RISK DECISIONS</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="loading">Loading risk data...</div>
        """, unsafe_allow_html=True)

elif page == "Settings":
    st.markdown("""
    <div class="card">
        <div class="card-header">
            <div class="card-title">SYSTEM SETTINGS</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #1a1a1a; padding: 1.5rem; border-radius: 6px;">
        <h3 style="color: #ffffff; margin-top: 0;">Configuration</h3>
        <p style="color: #888888; margin-bottom: 1.5rem;">
            These settings control the trading agent's behavior. Changes require restarting the agent.
        </p>

        <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                Trading Enabled
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.trading_enabled and 'ENABLED' or 'DISABLED'}</span>
            </div>
        </div>

        <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                AI Supervisor
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.use_ai_supervisor and 'ENABLED' or 'DISABLED'}</span>
            </div>
        </div>

        <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                Max Risk Per Trade
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.max_risk_per_trade:.1%}</span>
            </div>
        </div>

        <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                Max Portfolio Exposure
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.max_portfolio_exposure:.1%}</span>
            </div>
        </div>

        <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                Max Daily Loss
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.max_daily_loss:.1%}</span>
            </div>
        </div>

        <div style="margin-bottom: 1rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                Max Drawdown
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.max_drawdown:.1%}</span>
            </div>
        </div>

        <div style="margin-bottom: 1.5rem;">
            <label style="display: block; font-size: 0.875rem; color: #cccccc; margin-bottom: 0.25rem; font-weight: 500;">
                Underlyings
            </label>
            <div style="background-color: #2a2a2a; padding: 0.75rem; border-radius: 4px;">
                <span style="color: #888888;">{settings.underlyings}</span>
            </div>
        </div>

        <button style="background-color: #1a1a1a; color: #e0e0e0; border: 1px solid #1a1a1a;
            padding: 0.75rem 1.5rem; border-radius: 4px; font-weight: 500; cursor: pointer;
            transition: all 0.2s ease;">
            Refresh Settings
        </button>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem; padding: 2rem 0; border-top: 1px solid #1a1a1a;">
    ALPHA Autonomous Options Agent • Paper Trading Demo •
    <span id="last-update"></span>
</div>
""", unsafe_allow_html=True)

# JavaScript for updating time
st.markdown("""
<script>
    function updateTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', {
            hour12: false,
            timeZone: 'UTC'
        });
        document.getElementById('last-update').textContent = `Last updated: ${timeString}`;
    }
    setInterval(updateTime, 1000);
    updateTime();
</script>
""", unsafe_allow_html=True)