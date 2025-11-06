"""
Dashboard module with visualizations
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    
    # Key Metrics
    st.header("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_assets = len(assets_df)
    active_assets = len(assets_df[assets_df["Status"] == "Active"]) if "Status" in assets_df.columns else 0
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
        if "Status" in assets_df.columns:
            status_counts = assets_df["Status"].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Asset Status Distribution"
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("Status data not available")
    
    with col2:
        st.subheader("Assets by Condition")
        if "Condition" in assets_df.columns:
            condition_counts = assets_df["Condition"].value_counts()
            fig_condition = px.bar(
                x=condition_counts.index,
                y=condition_counts.values,
                title="Assets by Condition",
                labels={"x": "Condition", "y": "Count"}
            )
            st.plotly_chart(fig_condition, use_container_width=True)
        else:
            st.info("Condition data not available")
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Assets by Location")
        if "Location" in assets_df.columns and not assets_df["Location"].isna().all():
            location_counts = assets_df["Location"].value_counts().head(10)
            if not location_counts.empty:
                fig_location = px.bar(
                    x=location_counts.values,
                    y=location_counts.index,
                    orientation='h',
                    title="Top 10 Locations by Asset Count",
                    labels={"x": "Count", "y": "Location"}
                )
                st.plotly_chart(fig_location, use_container_width=True)
            else:
                st.info("No location data available")
        else:
            st.info("Location data not available")
    
    with col2:
        st.subheader("Assets by Category")
        if "Category" in assets_df.columns and not assets_df["Category"].isna().all():
            category_counts = assets_df["Category"].value_counts().head(10)
            if not category_counts.empty:
                fig_category = px.pie(
                    values=category_counts.values,
                    names=category_counts.index,
                    title="Top 10 Asset Categories"
                )
                st.plotly_chart(fig_category, use_container_width=True)
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
    available_cols = [col for col in summary_cols if col in assets_df.columns]
    if available_cols:
        st.dataframe(assets_df[available_cols].head(20), use_container_width=True)
    else:
        st.dataframe(assets_df.head(20), use_container_width=True)
