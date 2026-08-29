import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
import sys

# Add backend to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.settings import get_settings
from backend.app.data.live_alpaca import LiveAlpacaClient

# Page configuration
st.set_page_config(
    page_title="Alpaca AI Trading Agent Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🤖 Alpaca AI Trading Agent Dashboard")
st.markdown("*Live monitoring of autonomous options trading agent*")

# Sidebar
st.sidebar.title("Navigation")
st.sidebar.info("Dashboard refreshes automatically. For live data, ensure markets are open and system is running.")

# Helper functions
def get_db_connection():
    """Get database connection."""
    settings = get_settings()
    return sqlite3.connect(settings.database_path)

def load_journal_data():
    """Load decision journal data."""
    try:
        conn = get_db_connection()
        query = """
        SELECT
            timestamp,
            underlying,
            market_state,
            features,
            strategy_signal,
            ai_decision,
            ai_confidence,
            ai_reasoning,
            risk_decision,
            execution,
            result
        FROM decision_journal
        ORDER BY timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading journal data: {e}")
        return pd.DataFrame()

def load_orders_data():
    """Load orders data."""
    try:
        conn = get_db_connection()
        query = """
        SELECT
            id,
            internal_id,
            alpaca_id,
            symbol,
            side,
            qty,
            status,
            created_at,
            payload
        FROM orders
        ORDER BY created_at DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error loading orders data: {e}")
        return pd.DataFrame()

def get_account_info():
    """Get current account information from Alpaca."""
    try:
        settings = get_settings()
        if not settings.alpaca_api_key or settings.alpaca_api_key.startswith("your_"):
            return None

        client = LiveAlpacaClient(settings)
        account = client.get_account()
        return {
            'equity': float(account.equity),
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'portfolio_value': float(account.portfolio_value),
            'status': str(account.status),
            'trading_blocked': account.trading_blocked
        }
    except Exception as e:
        # Don't show error in production - just return None for demo
        return None

def get_positions():
    """Get current positions from Alpaca."""
    try:
        settings = get_settings()
        if not settings.alpaca_api_key or settings.alpaca_api_key.startswith("your_"):
            return []

        client = LiveAlpacaClient(settings)
        positions = client.list_positions()
        return positions
    except Exception as e:
        # Don't show error in production - just return empty list for demo
        return []

# Load data
journal_df = load_journal_data()
orders_df = load_orders_data()
account_info = get_account_info()
positions = get_positions()

# Main dashboard layout
tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio", "📋 Positions", "📝 Trades & Signals", "🧠 Agent Reasoning"])

with tab1:
    st.header("Portfolio Overview")

    # Account info section
    col1, col2, col3, col4 = st.columns(4)

    if account_info:
        with col1:
            st.metric(
                label="Total Equity",
                value=f"${account_info['equity']:,.2f}",
                delta=None
            )
        with col2:
            st.metric(
                label="Cash",
                value=f"${account_info['cash']:,.2f}",
                delta=None
            )
        with col3:
            st.metric(
                label="Buying Power",
                value=f"${account_info['buying_power']:,.2f}",
                delta=None
            )
        with col4:
            st.metric(
                label="Portfolio Value",
                value=f"${account_info['portfolio_value']:,.2f}",
                delta=None
            )

        # Additional metrics
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric(
                label="Account Status",
                value=account_info['status'],
                delta=None
            )
        with col6:
            trading_status = "🟢 Enabled" if not account_info['trading_blocked'] else "🔴 Blocked"
            st.metric(
                label="Trading Status",
                value=trading_status,
                delta=None
            )
        with col7:
            st.metric(
                label="Positions Count",
                value=len(positions),
                delta=None
            )
        with col8:
            # Calculate daily P&L from journal if possible
            st.metric(
                label="Today's Trades",
                value=len(journal_df[journal_df['timestamp'].str.contains(datetime.now().strftime('%Y-%m-%d'))]),
                delta=None
            )
    else:
        # Show demo/mock data when Alpaca not connected
        with col1:
            st.metric(label="Total Equity", value="$100,000.00")
        with col2:
            st.metric(label="Cash", value="$100,000.00")
        with col3:
            st.metric(label="Buying Power", value="$400,000.00")
        with col4:
            st.metric(label="Portfolio Value", value="$100,000.00")
        with col5:
            st.metric(label="Account Status", value="ACTIVE (Demo)")
        with col6:
            st.metric(label="Trading Status", value="🟢 Enabled")
        with col7:
            st.metric(label="Positions Count", value="0")
        with col8:
            st.metric(label="Today's Trades", value="0")

        st.info("💡 **Demo Mode**: Connect Alpaca API keys to see live account data")

with tab2:
    st.header("Current Positions")

    if positions:
        # Convert positions to DataFrame for display
        positions_data = []
        for pos in positions:
            positions_data.append({
                'Symbol': getattr(pos, 'symbol', 'N/A'),
                'Quantity': getattr(pos, 'qty', 0),
                'Side': getattr(pos, 'side', 'N/A').title(),
                'Entry Price': f"${float(getattr(pos, 'avg_entry_price', 0)):,.2f}",
                'Current Price': f"${float(getattr(pos, 'current_price', 0)):,.2f}" if hasattr(pos, 'current_price') else "N/A",
                'Market Value': f"${float(getattr(pos, 'market_value', 0)):,.2f}" if hasattr(pos, 'market_value') else "N/A",
                'Unrealized P&L': f"${float(getattr(pos, 'unrealized_pl', 0)):,.2f}" if hasattr(pos, 'unrealized_pl') else "N/A",
                'Unrealized P&L %': f"{float(getattr(pos, 'unrealized_plpc', 0)) * 100:.2f}%" if hasattr(pos, 'unrealized_plpc') else "N/A",
            })

        if positions_data:
            positions_df = pd.DataFrame(positions_data)
            st.dataframe(positions_df, use_container_width=True)
        else:
            st.info("No position data available to display")
    else:
        # Show demo data
        st.info("📭 No open positions (markets closed or no trades executed)")
        st.markdown("""
        **Position data will appear here when:**
        - Markets are open (Monday-Friday, 9:30 AM - 4:00 PM ET)
        - The trading agent generates and executes signals
        - Positions are held overnight or intraday
        """)

        # Show example position structure
        with st.expander("📋 See example position format"):
            st.code("""
            Position Fields:
            - Symbol: e.g., SPY240830C00500000
            - Quantity: Number of contracts
            - Side: Long or Short
            - Entry Price: Average entry price
            - Current Price: Real-time market price
            - Market Value: Position value
            - Unrealized P&L: Profit/loss if closed now
            - Unrealized P&L %: Return percentage
            """, language="text")

with tab3:
    st.header("Trading Activity")

    # Orders section
    st.subheader("📋 Order History")
    if not orders_df.empty:
        # Format orders for display
        orders_display = orders_df.copy()
        if 'created_at' in orders_display.columns:
            orders_display['created_at'] = pd.to_datetime(orders_display['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(orders_display[['created_at', 'symbol', 'side', 'qty', 'status', 'internal_id']],
                    use_container_width=True, hide_index=True)
    else:
        st.info("📭 No orders executed yet")

    st.divider()

    # Signals/Journal section
    st.subheader("📊 Recent Signals & Decisions")
    if not journal_df.empty:
        # Format journal data for display
        journal_display = journal_df.copy()

        # Extract key information from JSON fields
        def extract_ai_decision(row):
            try:
                if row['ai_decision'] and isinstance(row['ai_decision'], str):
                    data = json.loads(row['ai_decision'])
                    return data.get('decision', 'N/A')
                return 'N/A'
            except:
                return 'N/A'

        def extract_ai_confidence(row):
            try:
                if row['ai_decision'] and isinstance(row['ai_decision'], str):
                    data = json.loads(row['ai_decision'])
                    return f"{data.get('confidence', 0):.2%}"
                return 'N/A'
            except:
                return 'N/A'

        def extract_risk_approved(row):
            try:
                if row['risk_decision'] and isinstance(row['risk_decision'], str):
                    data = json.loads(row['risk_decision'])
                    return data.get('approved', False)
                return False
            except:
                return False

        journal_display['AI Decision'] = journal_display.apply(extract_ai_decision, axis=1)
        journal_display['AI Confidence'] = journal_display.apply(extract_ai_confidence, axis=1)
        journal_display['Risk Approved'] = journal_display.apply(extract_risk_approved, axis=1)
        journal_display['Timestamp'] = pd.to_datetime(journal_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        journal_display['Underlying'] = journal_display['underlying'].fillna('-')

        # Display relevant columns
        display_cols = ['Timestamp', 'Underlying', 'AI Decision', 'AI Confidence', 'Risk Approved']
        st.dataframe(journal_display[display_cols], use_container_width=True, hide_index=True)

        # Show recent activity chart
        if len(journal_display) > 1:
            st.subheader("📈 Signal Frequency (Last 24h)")
            journal_display['datetime'] = pd.to_datetime(journal_display['timestamp'], utc=True)
            recent = journal_display[journal_display['datetime'] > (pd.Timestamp.now(tz='UTC') - pd.Timedelta(hours=24))]
            if not recent.empty:
                recent['hour'] = recent['datetime'].dt.floor('h')
                hourly_counts = recent.groupby('hour').size().reset_index(name='count')
                st.line_chart(hourly_counts.set_index('hour')['count'])
            else:
                st.info("No activity in last 24 hours")
    else:
        st.info("📭 No trading activity recorded yet")

with tab4:
    st.header("🧠 Agent Reasoning & Decision Chain")

    if not journal_df.empty:
        # Show most recent decision with full reasoning
        latest = journal_df.iloc[0]  # Most recent first

        st.subheader("Latest Decision")
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Timestamp:**")
            st.markdown(latest['timestamp'])
            st.markdown("**Underlying:**")
            st.markdown(latest['underlying'] or "N/A")

        with col2:
            # Parse and display AI decision
            try:
                if latest['ai_decision'] and isinstance(latest['ai_decision'], str):
                    ai_data = json.loads(latest['ai_decision'])
                    st.markdown("**AI Decision:**")
                    st.markdown(f"**{ai_data.get('decision', 'N/A')}** (Confidence: {ai_data.get('confidence', 0):.2%})")
                    st.markdown("**Thesis:**")
                    st.markdown(ai_data.get('thesis', 'No thesis provided'))

                    if ai_data.get('risk_factors'):
                        st.markdown("**Risk Factors:**")
                        for risk in ai_data['risk_factors']:
                            st.markdown(f"• {risk}")

                    if ai_data.get('invalidation_conditions'):
                        st.markdown("**Invalidation Conditions:**")
                        for condition in ai_data['invalidation_conditions']:
                            st.markdown(f"• {condition}")
            except Exception as e:
                st.markdown("**AI Decision:**")
                st.markdown("Error parsing AI decision")
                st.exception(e)

        st.divider()

        # Show full decision chain for latest entry
        st.subheader("Full Decision Chain")

        # Create expandable sections for each part of the chain
        with st.expander("📊 Market State & Features", expanded=False):
            try:
                if latest['market_state'] and isinstance(latest['market_state'], str):
                    market_data = json.loads(latest['market_state'])
                    st.json(market_data)
                else:
                    st.write("No market state data")
            except:
                st.write(latest['market_state'])

        with st.expander("📈 Strategy Signal", expanded=False):
            try:
                if latest['strategy_signal'] and isinstance(latest['strategy_signal'], str):
                    signal_data = json.loads(latest['strategy_signal'])
                    st.json(signal_data)
                else:
                    st.write(latest['strategy_signal'])
            except:
                st.write(latest['strategy_signal'])

        with st.expander("🤖 AI Reasoning", expanded=True):
            try:
                if latest['ai_decision'] and isinstance(latest['ai_decision'], str):
                    ai_data = json.loads(latest['ai_decision'])
                    st.json(ai_data)
                else:
                    st.write(latest['ai_decision'])
            except:
                st.write(latest['ai_decision'])

        with st.expander("⚠️ Risk Assessment", expanded=False):
            try:
                if latest['risk_decision'] and isinstance(latest['risk_decision'], str):
                    risk_data = json.loads(latest['risk_decision'])
                    st.json(risk_data)
                else:
                    st.write(latest['risk_decision'])
            except:
                st.write(latest['risk_decision'])

        with st.expander("💸 Execution Details", expanded=False):
            try:
                if latest['execution'] and isinstance(latest['execution'], str):
                    exec_data = json.loads(latest['execution'])
                    st.json(exec_data)
                else:
                    st.write(latest['execution'] or "No execution (signal rejected or no signal)")
            except:
                st.write(latest['execution'] or "No execution")

        with st.expander("📈 Trade Result", expanded=False):
            try:
                if latest['result'] and isinstance(latest['result'], str):
                    result_data = json.loads(latest['result'])
                    st.json(result_data)
                else:
                    st.write(latest['result'] or "No result yet")
            except:
                st.write(latest['result'] or "No result yet")

        st.divider()

        # Show all recent decisions in timeline
        st.subheader("Recent Decision Timeline")
        for idx, row in journal_df.head(5).iterrows():  # Show last 5 decisions
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
                with col1:
                    st.caption(pd.to_datetime(row['timestamp']).strftime('%H:%M:%S'))
                with col2:
                    st.caption(row['underlying'] or '-')
                with col3:
                    try:
                        if row['ai_decision'] and isinstance(row['ai_decision'], str):
                            ai_dec = json.loads(row['ai_decision'])
                            st.caption(f"{ai_dec.get('decision', 'N/A')} {ai_dec.get('confidence', 0):.0%}")
                        else:
                            st.caption("N/A")
                    except:
                        st.caption("N/A")
                with col4:
                    try:
                        if row['ai_decision'] and isinstance(row['ai_decision'], str):
                            ai_dec = json.loads(row['ai_decision'])
                            thesis = ai_dec.get('thesis', 'No thesis')
                            st.caption(thesis[:50] + "..." if len(thesis) > 50 else thesis)
                        else:
                            st.caption("No AI reasoning")
                    except:
                        st.caption("Error parsing reasoning")
                st.divider()
    else:
        st.info("📭 No decision data available yet")
        st.markdown("""
        **Decision chain data will appear when:**
        - The trading agent is running and generating signals
        - Market conditions trigger strategy signals
        - The AI supervisor evaluates those signals
        - The risk engine makes approval decisions
        - Trades are executed or rejected
        """)

        # Show example of what the decision chain looks like
        with st.expander("🔍 See example decision chain format"):
            st.markdown("""
            Each decision record includes:

            1. **Market State**: Account info, portfolio state
            2. **Features**: Technical indicators (returns, momentum, RSI, etc.)
            3. **Strategy Signal**: Raw signal from Liquid Momentum/Volatility Mispricing/Mean Reversion
            4. **AI Reasoning**: Decision, confidence, thesis, risk factors, invalidation conditions
            5. **Risk Assessment**: Approved/rejected with reasons (position sizing, liquidity, etc.)
            6. **Execution Details**: Order ID, quantity, status, Alpaca ID
            7. **Trade Result**: Position details if filled, or rejection reasons

            This provides a complete audit trail for every trading decision.
            """)

# Auto-refresh every 30 seconds
st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if st.sidebar.button("🔄 Refresh Now"):
    st.rerun()

# Auto-refresh using JavaScript (optional)
st.sidebar.markdown(
    """
    <script>
    setTimeout(function(){
        window.location.reload();
    }, 30000);
    </script>
    """,
    unsafe_allow_html=True
)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Alpaca AI Trading Agent Dashboard<br>
        Built for Hackathon Competition<br>
        Markets open Monday 9:30 AM ET
    </div>
    """,
    unsafe_allow_html=True
)