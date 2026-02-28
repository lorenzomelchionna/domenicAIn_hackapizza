#!/usr/bin/env python3
"""Streamlit dashboard to monitor Hackapizza 2.0 multi-agent system. Run alongside main.py."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from src.monitor_state import MONITOR_STATE_PATH, read_monitor_state

st.set_page_config(
    page_title="Hackapizza Monitor",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .phase-badge {
        font-size: 1.5rem;
        font-weight: bold;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 1rem;
    }
    .phase-speaking { background: #e3f2fd; color: #1565c0; }
    .phase-closed_bid { background: #fff3e0; color: #e65100; }
    .phase-waiting { background: #f3e5f5; color: #7b1fa2; }
    .phase-serving { background: #e8f5e9; color: #2e7d32; }
    .phase-stopped { background: #ffebee; color: #c62828; }
    .metric-card {
        background: #f5f5f5;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.25rem 0;
    }
</style>
""", unsafe_allow_html=True)


def phase_class(phase: str) -> str:
    return f"phase-{phase}" if phase else "phase-stopped"


def main() -> None:
    st.title("🍕 Hackapizza 2.0 Monitor")
    st.caption("Real-time dashboard for the multi-agent restaurant system. Run `python run.py` in another terminal.")

    data = read_monitor_state()
    if data is None:
        st.warning(
            f"No monitor data yet. Start the game with `python run.py` and ensure it's running. "
            f"State is written to `{MONITOR_STATE_PATH}`."
        )
        st.info("The dashboard will auto-refresh every 3 seconds when data becomes available.")
        time.sleep(3)
        st.rerun()
        return

    state = data.get("state", {})
    event_log = data.get("event_log", [])
    updated_at = data.get("updated_at", "unknown")

    phase = state.get("phase", "stopped")
    st.markdown(
        f'<div class="phase-badge {phase_class(phase)}">Phase: {phase.upper()}</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Turn", state.get("turn_id", 0))
    with col2:
        st.metric("Balance", f"${state.get('balance', 0):.2f}")
    with col3:
        st.metric("Reputation", f"{state.get('reputation', 0):.2f}")
    with col4:
        st.metric("Restaurant Open", "Yes" if state.get("is_open", True) else "No")
    with col5:
        st.metric("Recipes", state.get("recipes_count", 0))

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Menu", "📦 Inventory", "🏪 Market", "📜 Event Log"])

    with tab1:
        menu = state.get("menu", [])
        if menu:
            st.dataframe(menu, use_container_width=True, hide_index=True)
        else:
            st.info("No menu items yet.")

    with tab2:
        inventory = state.get("inventory", {})
        if inventory:
            st.dataframe(
                [{"ingredient": k, "quantity": v} for k, v in inventory.items()],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Inventory empty.")

    with tab3:
        entries = state.get("market_entries", [])
        if entries:
            st.dataframe(entries, use_container_width=True, hide_index=True)
        else:
            st.info("No market entries.")

    with tab4:
        if event_log:
            for e in reversed(event_log[-50:]):
                tag = e.get("tag", "")
                msg = e.get("message", "")
                ts = e.get("ts", "")[:19] if e.get("ts") else ""
                st.text(f"[{ts}] [{tag}] {msg}")
        else:
            st.info("No events yet.")

    st.divider()
    col_a, col_b = st.columns([3, 1])
    with col_a:
        pending = state.get("pending_clients", [])
        prepared = state.get("prepared_dishes", [])
        if pending or prepared:
            st.subheader("Active")
            if pending:
                st.write("**Pending clients:**", len(pending))
                for c in pending[:5]:
                    st.text(f"  • {c.get('clientName', '?')}: {c.get('orderText', '')}")
            if prepared:
                st.write("**Prepared dishes:**", prepared)
    with col_b:
        st.caption(f"Last update: {updated_at}")

    time.sleep(3)
    st.rerun()


if __name__ == "__main__":
    main()
