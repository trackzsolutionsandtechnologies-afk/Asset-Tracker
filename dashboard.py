"""
Dashboard module with visualizations
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
from google_sheets import read_data
from config import SHEETS

def dashboard_page():
    """Main dashboard page with visualizations"""
    st.title("📊 Asset Tracker Dashboard")
    
    # Load data
    assets_df = read_data(SHEETS["assets"])
    locations_df = read_data(SHEETS["locations"])
    transfers_df = read_data(SHEETS["transfers"])
    categories_df = read_data(SHEETS["categories"])
    
    if assets_df.empty:
        st.warning("No asset data available. Please add assets to see the dashboard.")
        return
    
    # Ensure we work on mutable copies
    assets_df = assets_df.copy()
    locations_df = locations_df.copy()
    transfers_df = transfers_df.copy()
    categories_df = categories_df.copy()

    # Initialize interactive filter state
    filters = st.session_state.setdefault("dashboard_filters", {})
    # Remove filters for columns that no longer exist
    invalid_filters = [col for col in filters.keys() if col not in assets_df.columns]
    if invalid_filters:
        for col in invalid_filters:
            filters.pop(col, None)
        st.session_state["dashboard_filters"] = dict(filters)

    def toggle_filter(column: str, value: str):
        """Toggle a column/value filter and rerun to refresh visuals."""
        current_filters = st.session_state.setdefault("dashboard_filters", {})
        if current_filters.get(column) == value:
            current_filters.pop(column, None)
        else:
            current_filters[column] = value
        st.session_state["dashboard_filters"] = dict(current_filters)
        st.rerun()

    # Section intro and filter controls
    info_col, button_col = st.columns([3, 1])
    with info_col:
        st.caption(
            "Click a slice or bar in any chart to filter the Asset Summary table. "
            "Click the same visual again to remove that filter."
        )
        if filters:
            applied = ", ".join(f"{k}: {v}" for k, v in filters.items())
            st.info(f"Active filters → {applied}", icon="✨")
    with button_col:
        if st.button("Reset filters", type="secondary", use_container_width=True):
            st.session_state["dashboard_filters"] = {}
            st.rerun()

    # Apply filters to assets data
    filtered_assets_df = assets_df.copy()
    for column, value in filters.items():
        if column in filtered_assets_df.columns:
            filtered_assets_df = filtered_assets_df[filtered_assets_df[column] == value]

    # Key Metrics
    st.header("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_assets = len(filtered_assets_df)
    active_assets = len(filtered_assets_df[filtered_assets_df["Status"] == "Active"]) if "Status" in filtered_assets_df.columns else 0
    total_locations = len(locations_df) if not locations_df.empty else 0
    total_transfers = len(transfers_df) if not transfers_df.empty else 0
    
    with col1:
        st.metric("Total Assets", total_assets)
    with col2:
        st.metric("Active Assets", active_assets)
    with col3:
        st.metric("Total Locations", total_locations)
    with col4:
        st.metric("Total Transfers", total_transfers)
    
    st.divider()
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Assets by Status")
        if "Status" in filtered_assets_df.columns:
            status_counts = filtered_assets_df["Status"].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Asset Status Distribution"
            )
            fig_status.update_traces(textposition="inside", textinfo="percent+label")
            fig_status.update_layout(clickmode="event+select")
            status_event = plotly_events(
                fig_status,
                click_event=True,
                hover_event=False,
                override_width="100%",
                key="status_chart"
            )
            if status_event:
                selected_status = status_event[0].get("label")
                if selected_status:
                    toggle_filter("Status", selected_status)
        else:
            st.info("Status data not available")
    
    with col2:
        st.subheader("Assets by Condition")
        if "Condition" in filtered_assets_df.columns:
            condition_counts = filtered_assets_df["Condition"].value_counts()
            fig_condition = px.bar(
                x=condition_counts.index,
                y=condition_counts.values,
                title="Assets by Condition",
                labels={"x": "Condition", "y": "Count"}
            )
            fig_condition.update_traces(marker_color="#5C3E94")
            fig_condition.update_layout(clickmode="event+select")
            condition_event = plotly_events(
                fig_condition,
                click_event=True,
                hover_event=False,
                override_width="100%",
                key="condition_chart"
            )
            if condition_event:
                selected_condition = condition_event[0].get("x")
                if selected_condition is not None:
                    toggle_filter("Condition", selected_condition)
        else:
            st.info("Condition data not available")
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Assets by Location")
        if "Location" in filtered_assets_df.columns and not filtered_assets_df["Location"].isna().all():
            location_counts = filtered_assets_df["Location"].value_counts().head(10)
            if not location_counts.empty:
                fig_location = px.bar(
                    x=location_counts.values,
                    y=location_counts.index,
                    orientation='h',
                    title="Top 10 Locations by Asset Count",
                    labels={"x": "Count", "y": "Location"}
                )
                fig_location.update_traces(marker_color="#98EECC")
                fig_location.update_layout(clickmode="event+select")
                location_event = plotly_events(
                    fig_location,
                    click_event=True,
                    hover_event=False,
                    override_width="100%",
                    key="location_chart"
                )
                if location_event:
                    selected_location = location_event[0].get("y")
                    if selected_location:
                        toggle_filter("Location", selected_location)
            else:
                st.info("No location data available")
        else:
            st.info("Location data not available")
    
    with col2:
        st.subheader("Assets by Category")
        if "Category" in filtered_assets_df.columns and not filtered_assets_df["Category"].isna().all():
            category_counts = filtered_assets_df["Category"].value_counts().head(10)
            if not category_counts.empty:
                fig_category = px.pie(
                    values=category_counts.values,
                    names=category_counts.index,
                    title="Top 10 Asset Categories"
                )
                fig_category.update_traces(textposition="inside", textinfo="percent+label")
                fig_category.update_layout(clickmode="event+select")
                category_event = plotly_events(
                    fig_category,
                    click_event=True,
                    hover_event=False,
                    override_width="100%",
                    key="category_chart"
                )
                if category_event:
                    selected_category = category_event[0].get("label")
                    if selected_category:
                        toggle_filter("Category", selected_category)
            else:
                st.info("No category data available")
        else:
            st.info("Category data not available")
    
    # Charts Row 3 - Purchase Cost Analysis
    if "Purchase Cost" in assets_df.columns:
        st.subheader("Purchase Cost Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Convert Purchase Cost to numeric
            assets_df["Purchase Cost"] = pd.to_numeric(assets_df["Purchase Cost"], errors='coerce')
            total_cost = assets_df["Purchase Cost"].sum()
            avg_cost = assets_df["Purchase Cost"].mean()
            
            st.metric("Total Asset Value", f"${total_cost:,.2f}")
            st.metric("Average Asset Cost", f"${avg_cost:,.2f}")
        
        with col2:
            # Cost by Category
            if "Category" in assets_df.columns:
                cost_by_category = assets_df.groupby("Category")["Purchase Cost"].sum().sort_values(ascending=False).head(10)
                if not cost_by_category.empty:
                    fig_cost = px.bar(
                        x=cost_by_category.index,
                        y=cost_by_category.values,
                        title="Total Cost by Category (Top 10)",
                        labels={"x": "Category", "y": "Total Cost ($)"}
                    )
                    st.plotly_chart(fig_cost, use_container_width=True)
    
    # Recent Transfers
    if not transfers_df.empty and "Date" in transfers_df.columns:
        st.subheader("Recent Transfers")
        recent_transfers = transfers_df.tail(10)
        st.dataframe(recent_transfers, use_container_width=True)
    
    # Asset Summary Table
    st.subheader("Asset Summary")
    summary_cols = ["Asset ID", "Asset Name", "Category", "Location", "Status", "Condition"]
    available_cols = [col for col in summary_cols if col in filtered_assets_df.columns]
    table_source = filtered_assets_df[available_cols] if available_cols else filtered_assets_df
    st.dataframe(table_source.head(50), use_container_width=True)
