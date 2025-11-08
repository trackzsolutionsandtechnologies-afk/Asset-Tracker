"""
Forms module for Asset Tracker
"""
import base64
from io import BytesIO
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from google_sheets import read_data, append_data, update_data, delete_data, find_row, ensure_sheet_headers
# Helper utilities for modal views

def _open_view_modal(prefix: str, title: str, record: Dict[str, str], order: Optional[List[str]] = None) -> None:
    st.session_state[f"{prefix}_view_title"] = title
    st.session_state[f"{prefix}_view_record"] = record
    st.session_state[f"{prefix}_view_order"] = order
    st.session_state[f"{prefix}_view_open"] = True
    st.rerun()


def _render_view_modal(prefix: str, placeholder: Optional["st.delta_generator.DeltaGenerator"] = None) -> None:
    if not st.session_state.get(f"{prefix}_view_open"):
        return

    record = st.session_state.get(f"{prefix}_view_record", {}) or {}
    title = st.session_state.get(f"{prefix}_view_title", "Details")
    order = st.session_state.get(f"{prefix}_view_order")

    modal_ctx = getattr(st, "modal", None)
    if callable(modal_ctx):
        ctx_manager = modal_ctx(title)
    else:
        container_parent = placeholder if placeholder is not None else st
        ctx_manager = container_parent.container()

    with ctx_manager:
        if modal_ctx is None:
            st.subheader(title)
        keys = order or list(record.keys())
        if not keys:
            st.info("No details available.")
        else:
            cols = st.columns(2)
            col_idx = 0
            for key in keys:
                if key is None:
                    continue
                value = record.get(key, "")
                with cols[col_idx % 2]:
                    st.text_input(key, value if value not in (None, "") else "N/A", disabled=True)
                col_idx += 1

        close_key = f"{prefix}_view_close"
        close_button = st.button("Close", key=close_key)
        if close_button:
            for suffix in ("_view_open", "_view_record", "_view_title", "_view_order"):
                st.session_state.pop(f"{prefix}{suffix}", None)
            st.rerun()
from config import SHEETS, SESSION_KEYS
from auth import hash_password

def generate_location_id() -> str:
    """Generate a unique Location ID"""
    import uuid
    # Generate a short unique ID
    return f"LOC-{uuid.uuid4().hex[:8].upper()}"

def generate_supplier_id() -> str:
    """Generate a unique Supplier ID"""
    import uuid
    # Generate a short unique ID
    return f"SUP-{uuid.uuid4().hex[:8].upper()}"

def generate_category_id() -> str:
    """Generate a unique Category ID"""
    import uuid
    # Generate a short unique ID
    return f"CAT-{uuid.uuid4().hex[:8].upper()}"

def generate_subcategory_id() -> str:
    """Generate a unique Sub Category ID"""
    import uuid
    # Generate a short unique ID
    return f"SUB-{uuid.uuid4().hex[:8].upper()}"

def generate_transfer_id() -> str:
    """Generate a unique Transfer ID"""
    import uuid
    return f"TRF-{uuid.uuid4().hex[:8].upper()}"

def generate_maintenance_id() -> str:
    """Generate a unique Maintenance ID"""
    import uuid
    return f"MTN-{uuid.uuid4().hex[:8].upper()}"

def generate_assignment_id() -> str:
    """Generate a unique Assignment ID"""
    import uuid
    return f"ASN-{uuid.uuid4().hex[:8].upper()}"

def location_form():
    """Location"""
    st.header("📍 Location Management")
    
    df = read_data(SHEETS["locations"])
    
    tab1, tab2 = st.tabs(["Add New Location", "View/Edit Locations"])
    
    with tab1:
        # Align styling with supplier form (white card, green primary button, hide spinners)
        st.markdown(
            """
            <style>
            div[data-testid="stTabPanel"] div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            div[data-testid="stTabPanel"] div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stTabPanel"] div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            [data-testid="stStatusWidget"],
            .stSpinner {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Show success message if exists
        if "location_success_message" in st.session_state:
            st.success(st.session_state["location_success_message"])
            # Clear message after showing
            del st.session_state["location_success_message"]
        
        # Initialize form key for reset
        if "location_form_key" not in st.session_state:
            st.session_state["location_form_key"] = 0
        
        with st.form(key=f"location_form_{st.session_state['location_form_key']}"):
            auto_generate = st.checkbox("Auto-generate Location ID", value=True, key=f"auto_gen_{st.session_state['location_form_key']}")
            if auto_generate:
                # Generate ID once and store in session state
                if "generated_location_id" not in st.session_state:
                    st.session_state["generated_location_id"] = generate_location_id()
                location_id = st.text_input("Location ID *", value=st.session_state["generated_location_id"], disabled=True, help="Auto-generated unique identifier", key=f"loc_id_{st.session_state['location_form_key']}")
            else:
                location_id = st.text_input("Location ID *", help="Unique identifier for the location", key=f"loc_id_manual_{st.session_state['location_form_key']}")
                if "generated_location_id" in st.session_state:
                    del st.session_state["generated_location_id"]
            
            location_name = st.text_input("Location Name *", key=f"loc_name_{st.session_state['location_form_key']}")
            department = st.text_input("Department *", key=f"dept_{st.session_state['location_form_key']}")
            
            submitted = st.form_submit_button("Add Location", use_container_width=True, type="primary")
            
            if submitted:
                if not location_id or not location_name or not department:
                    st.error("Please fill in all required fields")
                elif not df.empty and "Location ID" in df.columns and location_id in df["Location ID"].values:
                    st.error("Location ID already exists")
                else:
                    with st.spinner("Adding location..."):
                        if append_data(SHEETS["locations"], [location_id, location_name, department]):
                            # Clear generated location ID and reset form
                            if "generated_location_id" in st.session_state:
                                del st.session_state["generated_location_id"]
                            # Clear search bar
                            if "location_search" in st.session_state:
                                del st.session_state["location_search"]
                            # Set success message
                            st.session_state["location_success_message"] = f"✅ Location '{location_name}' (ID: {location_id}) added successfully!"
                            # Increment form key to reset form
                            st.session_state["location_form_key"] += 1
                            st.rerun()
                        else:
                            st.error("Failed to add location")
    
    with tab2:
        # Show success message if exists
        if "location_success_message" in st.session_state:
            st.success(st.session_state["location_success_message"])
            # Clear message after showing
            del st.session_state["location_success_message"]
        
        if not df.empty and "Location ID" in df.columns:
            st.subheader("All Locations")
            
            # Search bar
            search_term = st.text_input("🔍 Search Locations", placeholder="Search by Location ID, Name, or Department...", key="location_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    df["Location ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    df["Location Name"].astype(str).str.contains(search_term, case=False, na=False) |
                    df["Department"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = df[mask]
                if filtered_df.empty:
                    st.info(f"No locations found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(df)} location(s)")

                # Determine admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"

                view_placeholder = st.empty()
                edit_placeholder = st.empty()

                # Table header - adjust columns based on admin status
                if is_admin:
                    header_cols = st.columns([3, 4, 3, 1, 1, 1])
                else:
                    header_cols = st.columns([3, 4, 3, 1, 1])

                header_labels = ["**Location ID**", "**Location Name**", "**Department**", "**View**", "**Edit**"]
                if is_admin:
                    header_labels.append("**Delete**")

                for col_widget, label in zip(header_cols, header_labels):
                    with col_widget:
                        st.write(label)
                st.divider()

                # Display table with edit/delete buttons
                button_counter = 0
                for idx, row in filtered_df.iterrows():
                    location_id_value = row.get("Location ID", "")
                    unique_suffix = f"{location_id_value}_{button_counter}"
                    button_counter += 1

                    if not df[df["Location ID"] == location_id_value].empty:
                        original_idx = int(df[df["Location ID"] == location_id_value].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    if is_admin:
                        col1, col2, col3, col_view, col_edit, col_delete = st.columns([3, 4, 3, 1, 1, 1])
                    else:
                        col1, col2, col3, col_view, col_edit = st.columns([3, 4, 3, 1, 1])

                    with col1:
                        st.write(row.get("Location ID", "N/A"))
                    with col2:
                        st.write(row.get("Location Name", "N/A"))
                    with col3:
                        st.write(row.get("Department", "N/A"))
                    with col_view:
                        if st.button("👁️", key=f"location_view_{unique_suffix}", use_container_width=True, help="View details"):
                            record = {
                                "Location ID": location_id_value,
                                "Location Name": row.get("Location Name", ""),
                                "Department": row.get("Department", ""),
                            }
                            _open_view_modal(
                                "location",
                                f"Location Details: {row.get('Location Name', '')}",
                                record,
                                ["Location ID", "Location Name", "Department"],
                            )
                    with col_edit:
                        edit_key = f"location_edit_{unique_suffix}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this location"):
                            st.session_state["edit_location_id"] = location_id_value
                            st.session_state["edit_location_idx"] = int(original_idx)
                            st.rerun()
                    if is_admin:
                        with col_delete:
                            delete_key = f"location_delete_{unique_suffix}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this location"):
                                location_name_to_delete = row.get("Location Name", "Unknown")
                                location_id_to_delete = location_id_value or "Unknown"
                                if delete_data(SHEETS["locations"], original_idx):
                                    st.session_state["location_success_message"] = (
                                        f"✅ Location '{location_name_to_delete}' (ID: {location_id_to_delete}) deleted successfully!"
                                    )
                                    if "location_search" in st.session_state:
                                        del st.session_state["location_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete location")

                    st.divider()

                _render_view_modal("location", view_placeholder)

            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No locations found. Add a new location using the 'Add New Location' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_location_id" in st.session_state and st.session_state["edit_location_id"]:
                with edit_placeholder.container():
                    st.subheader("Edit Location")
                    edit_id = st.session_state["edit_location_id"]
                    edit_idx = st.session_state.get("edit_location_idx", 0)
                    
                    location_rows = df[df["Location ID"] == edit_id]
                    if not location_rows.empty:
                        location = location_rows.iloc[0]
                        
                        with st.form("edit_location_form"):
                            new_location_id = st.text_input("Location ID", value=location.get("Location ID", ""), disabled=True)
                            new_location_name = st.text_input("Location Name", value=location.get("Location Name", ""))
                            new_department = st.text_input("Department", value=location.get("Department", ""))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Update Location", use_container_width=True):
                                    with st.spinner("Updating location..."):
                                        if update_data(SHEETS["locations"], edit_idx, [new_location_id, new_location_name, new_department]):
                                            st.session_state["location_success_message"] = f"✅ Location '{new_location_name}' (ID: {new_location_id}) updated successfully!"
                                            st.session_state.pop("edit_location_id", None)
                                            st.session_state.pop("edit_location_idx", None)
                                            if "location_search" in st.session_state:
                                                del st.session_state["location_search"]
                                            st.rerun()
                                        else:
                                            st.error("Failed to update location")
                            with col2:
                                if st.form_submit_button("Cancel", use_container_width=True):
                                    st.session_state.pop("edit_location_id", None)
                                    st.session_state.pop("edit_location_idx", None)
                                    st.rerun()

        else:
            st.info("No locations found. Add a new location using the 'Add New Location' tab.")

def asset_depreciation_form():
    """Depreciation schedules based on Asset Master data."""
    st.header("📉 Depreciation")

    expected_headers = [
        "Schedule ID",
        "Asset ID",
        "Asset Name",
        "Purchase Date",
        "Purchase Cost",
        "Useful Life (Years)",
        "Salvage Value",
        "Method",
        "Period",
        "Period End",
        "Opening Value",
        "Depreciation",
        "Closing Value",
        "Generated On",
    ]
    ensure_sheet_headers(SHEETS["depreciation"], expected_headers)

    assets_df = read_data(SHEETS["assets"])
    depreciation_df = read_data(SHEETS["depreciation"])

    def _get_asset_record(asset_id: str) -> Dict[str, str]:
        if assets_df.empty or "Asset ID" not in assets_df.columns:
            return {}
        matches = assets_df[assets_df["Asset ID"].astype(str) == str(asset_id)]
        if matches.empty:
            return {}
        return matches.iloc[0].to_dict()

    def _parse_purchase_date(value) -> Optional[datetime]:
        if not value:
            return None
        try:
            return pd.to_datetime(value, errors="coerce").to_pydatetime()
        except Exception:
            return None

    def _calculate_schedule(
        asset_id: str,
        asset_name: str,
        purchase_date: datetime,
        purchase_cost: float,
        useful_life: int,
        salvage_value: float,
    ) -> Dict[str, object]:
        if useful_life <= 0:
            return {"error": "Useful life must be greater than zero."}
        if purchase_cost < 0:
            return {"error": "Purchase cost cannot be negative."}
        if salvage_value < 0:
            return {"error": "Salvage value cannot be negative."}
        if salvage_value > purchase_cost:
            return {"error": "Salvage value cannot exceed purchase cost."}

        cost = float(purchase_cost)
        salvage = float(salvage_value)
        straight_line = (cost - salvage) / useful_life if useful_life else 0.0
        straight_line = max(straight_line, 0.0)

        schedule_rows: List[Dict[str, object]] = []
        opening_value = cost

        for period_index in range(1, useful_life + 1):
            depreciation_amount = straight_line
            closing_value = opening_value - depreciation_amount
            if period_index == useful_life:
                # Force closing value to salvage to avoid rounding drift.
                closing_value = salvage
                depreciation_amount = opening_value - closing_value

            period_end = purchase_date + pd.DateOffset(years=period_index)
            schedule_rows.append(
                {
                    "Period": f"Year {period_index}",
                    "Period End": period_end.strftime("%Y-%m-%d"),
                    "Opening Value": round(opening_value, 2),
                    "Depreciation": round(depreciation_amount, 2),
                    "Closing Value": round(closing_value, 2),
                }
            )
            opening_value = closing_value

        schedule_df = pd.DataFrame(schedule_rows)
        generated_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            import uuid

            schedule_id = f"DEP-{uuid.uuid4().hex[:8].upper()}"
        except Exception:
            schedule_id = f"DEP-{int(datetime.now().timestamp())}"

        sheet_rows = []
        for row in schedule_rows:
            sheet_rows.append(
                [
                    schedule_id,
                    asset_id,
                    asset_name,
                    purchase_date.strftime("%Y-%m-%d") if purchase_date else "",
                    round(cost, 2),
                    useful_life,
                    round(salvage, 2),
                    "Straight-Line",
                    row["Period"],
                    row["Period End"],
                    row["Opening Value"],
                    row["Depreciation"],
                    row["Closing Value"],
                    generated_on,
                ]
            )

        return {
            "schedule_id": schedule_id,
            "dataframe": schedule_df,
            "sheet_rows": sheet_rows,
            "generated_on": generated_on,
        }

    tab_generate, tab_view = st.tabs(["Generate Schedule", "View Schedules"])

    with tab_generate:
        if assets_df.empty or "Asset ID" not in assets_df.columns:
            st.info("No assets found. Add assets in the Asset Master first.")
        else:
            asset_options = []
            for _, row in assets_df.iterrows():
                asset_id = str(row.get("Asset ID", "")).strip()
                asset_name = str(row.get("Asset Name", "")).strip()
                if asset_id:
                    label = f"{asset_id} – {asset_name}" if asset_name else asset_id
                    asset_options.append((label, asset_id))

            asset_options = sorted(asset_options, key=lambda x: x[0])

            with st.form("depreciation_form"):
                asset_labels = [option[0] for option in asset_options]
                selection = st.selectbox(
                    "Select Asset",
                    asset_labels,
                    help="Choose the asset to calculate depreciation for.",
                )
                selected_asset_id = next(
                    (asset_id for label, asset_id in asset_options if label == selection),
                    "",
                )
                asset_record = _get_asset_record(selected_asset_id)

                default_cost = 0.0
                if asset_record:
                    try:
                        default_cost = float(asset_record.get("Purchase Cost", 0) or 0)
                    except Exception:
                        default_cost = 0.0

                default_purchase_date = _parse_purchase_date(asset_record.get("Purchase Date"))
                if default_purchase_date is None:
                    default_purchase_date = datetime.now()

                purchase_date_input = st.date_input(
                    "Purchase Date",
                    value=default_purchase_date.date(),
                    help="Adjust if the purchase date in Asset Master is incorrect.",
                )
                purchase_cost_input = st.number_input(
                    "Purchase Cost",
                    min_value=0.0,
                    value=float(round(default_cost, 2)) if default_cost else 0.0,
                    step=0.01,
                )
                useful_life_input = st.number_input(
                    "Useful Life (years)",
                    min_value=1,
                    value=5,
                    step=1,
                )
                salvage_value_input = st.number_input(
                    "Salvage Value",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                )
                st.selectbox(
                    "Depreciation Method",
                    ["Straight-Line"],
                    index=0,
                    help="Straight-line depreciation spreads cost evenly across years.",
                )

                submitted = st.form_submit_button(
                    "Calculate Depreciation", use_container_width=True
                )

            if submitted:
                if not selected_asset_id:
                    st.error("Please select an asset.")
                else:
                    asset_name = str(asset_record.get("Asset Name", "")).strip()
                    schedule_result = _calculate_schedule(
                        selected_asset_id,
                        asset_name,
                        datetime.combine(purchase_date_input, datetime.min.time()),
                        purchase_cost_input,
                        int(useful_life_input),
                        salvage_value_input,
                    )
                    if isinstance(schedule_result, dict) and schedule_result.get("error"):
                        st.error(schedule_result["error"])
                    else:
                        st.session_state["depreciation_generated_schedule"] = {
                            "asset_id": selected_asset_id,
                            "asset_name": asset_name,
                            **schedule_result,
                        }
                        st.success("Depreciation schedule generated.")

        state_key = "depreciation_generated_schedule"
        if state_key in st.session_state:
            schedule_state = st.session_state[state_key]
            st.subheader(
                f"Schedule Preview · {schedule_state['asset_id']} "
                f"{'('+schedule_state['asset_name']+')' if schedule_state['asset_name'] else ''}"
            )
            st.dataframe(schedule_state["dataframe"], use_container_width=True)

            csv_data = schedule_state["dataframe"].to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                csv_data,
                file_name=f"{schedule_state['asset_id']}_depreciation.csv",
                mime="text/csv",
            )

            if st.button("Save schedule to Google Sheet", use_container_width=True):
                all_saved = True
                for row in schedule_state["sheet_rows"]:
                    if not append_data(SHEETS["depreciation"], row):
                        all_saved = False
                        break
                if all_saved:
                    st.success("Depreciation schedule saved to Google Sheet.")
                    st.session_state.pop(state_key, None)
                    st.rerun()
                else:
                    st.error("Failed to save the schedule. Please try again.")

    with tab_view:
        if depreciation_df.empty:
            st.info("No depreciation schedules found. Generate one to get started.")
            return

        asset_filter_options = ["All Assets"] + sorted(
            depreciation_df.get("Asset ID", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
        )
        asset_filter = st.selectbox("Filter by Asset", asset_filter_options)

        filtered_df = depreciation_df.copy()
        if asset_filter != "All Assets":
            filtered_df = filtered_df[filtered_df["Asset ID"].astype(str) == asset_filter]

        if filtered_df.empty:
            st.info("No schedules match the selected filters.")
            return

        schedule_ids = filtered_df["Schedule ID"].dropna().unique().tolist()
        schedule_filter_options = ["All Schedules"] + schedule_ids
        schedule_filter = st.selectbox("Filter by Schedule", schedule_filter_options)

        if schedule_filter != "All Schedules":
            filtered_df = filtered_df[filtered_df["Schedule ID"] == schedule_filter]

        st.caption(f"Showing {len(filtered_df)} depreciation row(s).")
        st.dataframe(filtered_df, use_container_width=True)

        csv_export = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Filtered CSV",
            csv_export,
            file_name="depreciation_schedules.csv",
            mime="text/csv",
        )

def supplier_form():
    """Supplier"""
    st.header("🚚 Supplier Management")
    
    df = read_data(SHEETS["suppliers"])
    
    tab1, tab2 = st.tabs(["Add New Supplier", "View/Edit Suppliers"])
    
    with tab1:
        # Green Add Supplier button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Supplier */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the Supplier section */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Show success message if exists
        if "supplier_success_message" in st.session_state:
            st.success(st.session_state["supplier_success_message"])
            # Clear message after showing
            del st.session_state["supplier_success_message"]
        
        # Initialize form key for reset
        if "supplier_form_key" not in st.session_state:
            st.session_state["supplier_form_key"] = 0
        
        with st.form(key=f"supplier_form_{st.session_state['supplier_form_key']}"):
            auto_generate = st.checkbox("Auto-generate Supplier ID", value=True, key=f"auto_gen_sup_{st.session_state['supplier_form_key']}")
            if auto_generate:
                # Generate ID once and store in session state
                if "generated_supplier_id" not in st.session_state:
                    st.session_state["generated_supplier_id"] = generate_supplier_id()
                supplier_id = st.text_input("Supplier ID *", value=st.session_state["generated_supplier_id"], disabled=True, help="Auto-generated unique identifier", key=f"sup_id_{st.session_state['supplier_form_key']}")
            else:
                supplier_id = st.text_input("Supplier ID *", help="Unique identifier for the supplier", key=f"sup_id_manual_{st.session_state['supplier_form_key']}")
                if "generated_supplier_id" in st.session_state:
                    del st.session_state["generated_supplier_id"]
            
            supplier_name = st.text_input("Supplier Name *", key=f"sup_name_{st.session_state['supplier_form_key']}")
            
            submitted = st.form_submit_button("Add Supplier", use_container_width=True, type="primary")
            
            if submitted:
                if not supplier_id or not supplier_name:
                    st.error("Please fill in all required fields")
                elif not df.empty and "Supplier ID" in df.columns and supplier_id in df["Supplier ID"].values:
                    st.error("Supplier ID already exists")
                else:
                    with st.spinner("Adding supplier..."):
                        if append_data(SHEETS["suppliers"], [supplier_id, supplier_name]):
                            # Clear generated supplier ID and reset form
                            if "generated_supplier_id" in st.session_state:
                                del st.session_state["generated_supplier_id"]
                            # Clear search bar
                            if "supplier_search" in st.session_state:
                                del st.session_state["supplier_search"]
                            # Set success message
                            st.session_state["supplier_success_message"] = f"✅ Supplier '{supplier_name}' (ID: {supplier_id}) added successfully!"
                            # Increment form key to reset form
                            st.session_state["supplier_form_key"] += 1
                            st.rerun()
                        else:
                            st.error("Failed to add supplier")
    
    with tab2:
        # Show success message if exists
        if "supplier_success_message" in st.session_state:
            st.success(st.session_state["supplier_success_message"])
            # Clear message after showing
            del st.session_state["supplier_success_message"]
        
        if not df.empty and "Supplier ID" in df.columns:
            st.subheader("All Suppliers")
            
            # Search bar
            search_term = st.text_input("🔍 Search Suppliers", placeholder="Search by Supplier ID or Name...", key="supplier_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    df["Supplier ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    df["Supplier Name"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = df[mask]
                if filtered_df.empty:
                    st.info(f"No suppliers found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(df)} supplier(s)")

                view_placeholder = st.empty()
                edit_placeholder = st.empty()
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"






                
                
                # Table header - adjust columns based on admin status
                if is_admin:
                    header_cols = st.columns([3, 4, 1, 1, 1])
                else:
                    header_cols = st.columns([3, 4, 1, 1])

                header_labels = ["**Supplier ID**", "**Supplier Name**", "**View**", "**Edit**"]
                if is_admin:
                    header_labels.append("**Delete**")

                for col_widget, label in zip(header_cols, header_labels):
                    with col_widget:
                        st.write(label)
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not df[df["Supplier ID"] == row.get('Supplier ID', '')].empty:
                        original_idx = int(df[df["Supplier ID"] == row.get('Supplier ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    if is_admin:
                        col1, col2, col_view, col_edit, col_delete = st.columns([3, 4, 1, 1, 1])
                    else:
                        col1, col2, col_view, col_edit = st.columns([3, 4, 1, 1])

                    with col1:
                        st.write(row.get('Supplier ID', 'N/A'))
                    with col2:
                        st.write(row.get('Supplier Name', 'N/A'))
                    with col_view:
                        if st.button("👁️", key=f"supplier_view_{row.get('Supplier ID', idx)}", use_container_width=True, help="View details"):
                            record = {
                                "Supplier ID": row.get("Supplier ID", ""),
                                "Supplier Name": row.get("Supplier Name", ""),
                            }
                            _open_view_modal(
                                "supplier",
                                f"Supplier Details: {row.get('Supplier Name', '')}",
                                record,
                                ["Supplier ID", "Supplier Name"],
                            )
                    with col_edit:
                        edit_key = f"edit_sup_{row.get('Supplier ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this supplier"):
                            st.session_state["edit_supplier_id"] = row.get('Supplier ID', '')
                            st.session_state["edit_supplier_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin:
                        with col_delete:
                            delete_key = f"delete_sup_{row.get('Supplier ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this supplier"):
                                supplier_name_to_delete = row.get('Supplier Name', 'Unknown')
                                supplier_id_to_delete = row.get('Supplier ID', 'Unknown')
                                if delete_data(SHEETS["suppliers"], original_idx):
                                    # Set success message
                                    st.session_state["supplier_success_message"] = f"✅ Supplier '{supplier_name_to_delete}' (ID: {supplier_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "supplier_search" in st.session_state:
                                        del st.session_state["supplier_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete supplier")
                    
                    st.divider()
                _render_view_modal("supplier", view_placeholder)
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No suppliers found. Add a new supplier using the 'Add New Supplier' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_supplier_id" in st.session_state and st.session_state["edit_supplier_id"]:
                with edit_placeholder.container():
                    st.subheader("Edit Supplier")
                    edit_id = st.session_state["edit_supplier_id"]
                    edit_idx = st.session_state.get("edit_supplier_idx", 0)
                    
                    supplier_rows = df[df["Supplier ID"] == edit_id]
                    if not supplier_rows.empty:
                        supplier = supplier_rows.iloc[0]
                        
                        with st.form("edit_supplier_form"):
                            new_supplier_id = st.text_input("Supplier ID", value=supplier.get("Supplier ID", ""), disabled=True)
                            new_supplier_name = st.text_input("Supplier Name", value=supplier.get("Supplier Name", ""))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Update Supplier", use_container_width=True):
                                    with st.spinner("Updating supplier..."):
                                        if update_data(SHEETS["suppliers"], edit_idx, [new_supplier_id, new_supplier_name]):
                                            # Set success message
                                            st.session_state["supplier_success_message"] = f"✅ Supplier '{new_supplier_name}' (ID: {new_supplier_id}) updated successfully!"
                                            if "edit_supplier_id" in st.session_state:
                                                del st.session_state["edit_supplier_id"]
                                            if "edit_supplier_idx" in st.session_state:
                                                del st.session_state["edit_supplier_idx"]
                                            # Clear search bar
                                            if "supplier_search" in st.session_state:
                                                del st.session_state["supplier_search"]
                                            st.rerun()
                                        else:
                                            st.error("Failed to update supplier")
                            with col2:
                                if st.form_submit_button("Cancel", use_container_width=True):
                                    if "edit_supplier_id" in st.session_state:
                                        del st.session_state["edit_supplier_id"]
                                    if "edit_supplier_idx" in st.session_state:
                                        del st.session_state["edit_supplier_idx"]
                                    st.rerun()
                    else:
                        st.warning("Selected supplier not found in data.")
        else:
            st.info("No suppliers found. Add a new supplier using the 'Add New Supplier' tab.")

def category_form():
    """Asset Category and Sub Category"""
    st.header("📂 Category Management")
    
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add Category", "Add Sub Category", "View/Edit Categories", "View/Edit Sub Categories"])
    
    with tab1:
        # Green Add Category button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Category */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            /* Target the primary button in the Category section */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Show success message if exists
        if "category_success_message" in st.session_state:
            st.success(st.session_state["category_success_message"])
            # Clear message after showing
            del st.session_state["category_success_message"]
        
        # Initialize form key for reset
        if "category_form_key" not in st.session_state:
            st.session_state["category_form_key"] = 0
        
        with st.form(key=f"category_form_{st.session_state['category_form_key']}"):
            auto_generate = st.checkbox("Auto-generate Category ID", value=True, key=f"auto_gen_cat_{st.session_state['category_form_key']}")
            if auto_generate:
                # Generate ID once and store in session state
                if "generated_category_id" not in st.session_state:
                    st.session_state["generated_category_id"] = generate_category_id()
                category_id = st.text_input("Category ID *", value=st.session_state["generated_category_id"], disabled=True, help="Auto-generated unique identifier", key=f"cat_id_{st.session_state['category_form_key']}")
            else:
                category_id = st.text_input("Category ID *", help="Unique identifier for the category", key=f"cat_id_manual_{st.session_state['category_form_key']}")
                if "generated_category_id" in st.session_state:
                    del st.session_state["generated_category_id"]
            
            category_name = st.text_input("Category Name *", key=f"cat_name_{st.session_state['category_form_key']}")
            
            submitted = st.form_submit_button("Add Category", use_container_width=True, type="primary")
            
            if submitted:
                if not category_id or not category_name:
                    st.error("Please fill in all required fields")
                elif not categories_df.empty and "Category ID" in categories_df.columns and category_id in categories_df["Category ID"].values:
                    st.error("Category ID already exists")
                else:
                    with st.spinner("Adding category..."):
                        if append_data(SHEETS["categories"], [category_id, category_name]):
                            # Clear generated category ID and reset form
                            if "generated_category_id" in st.session_state:
                                del st.session_state["generated_category_id"]
                            # Clear search bar
                            if "category_search" in st.session_state:
                                del st.session_state["category_search"]
                            # Set success message
                            st.session_state["category_success_message"] = f"✅ Category '{category_name}' (ID: {category_id}) added successfully!"
                            # Increment form key to reset form
                            st.session_state["category_form_key"] += 1
                            st.rerun()
                        else:
                            st.error("Failed to add category")
    
    with tab2:
        # Green Add Sub Category button styling, white form background, and hide loading indicators
        st.markdown("""
            <style>
            /* White background for Add Sub Category form */
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                
                border: none !important;
            }
            /* Target the primary button in the subcategory form */
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            /* Hide loading indicators */
            [data-testid="stStatusWidget"] {
                display: none !important;
            }
            .stSpinner {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # Show success message if exists
        if "subcategory_success_message" in st.session_state:
            st.success(st.session_state["subcategory_success_message"])
            # Clear message after showing
            del st.session_state["subcategory_success_message"]

        # Initialize form key for reset
        if "subcategory_form_key" not in st.session_state:
            st.session_state["subcategory_form_key"] = 0

        if categories_df.empty:
            st.warning("Please add categories first before adding subcategories")
        else:
            with st.form(key=f"subcategory_form_{st.session_state['subcategory_form_key']}"):
                # Show category names in dropdown but store category ID
                category_options = categories_df["Category Name"].tolist()
                category_names = ["Select category"] + category_options
                selected_category_name = st.selectbox("Category *", category_names, key=f"subcat_cat_{st.session_state['subcategory_form_key']}")

                # Map selected category name back to category ID
                if selected_category_name != "Select category":
                    category_id = categories_df[categories_df["Category Name"] == selected_category_name]["Category ID"].iloc[0]
                    category_name = selected_category_name
                else:
                    category_id = "Select category"
                    category_name = ""

                auto_generate = st.checkbox("Auto-generate Sub Category ID", value=True, key=f"auto_gen_subcat_{st.session_state['subcategory_form_key']}")
                if auto_generate:
                    # Generate ID once and store in session state
                    if "generated_subcategory_id" not in st.session_state:
                        st.session_state["generated_subcategory_id"] = generate_subcategory_id()
                    subcategory_id = st.text_input("Sub Category ID *", value=st.session_state["generated_subcategory_id"], disabled=True, help="Auto-generated unique identifier", key=f"subcat_id_{st.session_state['subcategory_form_key']}")
                else:
                    subcategory_id = st.text_input("Sub Category ID *", help="Unique identifier for the subcategory", key=f"subcat_id_manual_{st.session_state['subcategory_form_key']}")
                    if "generated_subcategory_id" in st.session_state:
                        del st.session_state["generated_subcategory_id"]

                subcategory_name = st.text_input("Sub Category Name *", key=f"subcat_name_{st.session_state['subcategory_form_key']}")

                submitted = st.form_submit_button("Add Sub Category", use_container_width=True, type="primary")

                if submitted:
                    if selected_category_name == "Select category" or not subcategory_id or not subcategory_name:
                        st.error("Please fill in all required fields")
                    elif not subcategories_df.empty and "SubCategory ID" in subcategories_df.columns and subcategory_id in subcategories_df["SubCategory ID"].values:
                        st.error("Sub Category ID already exists")
                    else:
                        with st.spinner("Adding sub category..."):
                            # Save: SubCategory ID, Category ID, Category Name, SubCategory Name
                            if append_data(SHEETS["subcategories"], [subcategory_id, category_id, category_name, subcategory_name]):
                                # Clear generated subcategory ID and reset form
                                if "generated_subcategory_id" in st.session_state:
                                    del st.session_state["generated_subcategory_id"]
                                # Clear search bar
                                if "subcategory_search" in st.session_state:
                                    del st.session_state["subcategory_search"]
                                # Set success message
                                st.session_state["subcategory_success_message"] = f"✅ Sub Category '{subcategory_name}' (ID: {subcategory_id}) added successfully!"
                                # Increment form key to reset form
                                st.session_state["subcategory_form_key"] += 1
                                st.rerun()
                            else:
                                st.error("Failed to add sub category")
    
    with tab3:
        # Show success message if exists
        if "category_success_message" in st.session_state:
            st.success(st.session_state["category_success_message"])
            # Clear message after showing
            del st.session_state["category_success_message"]
        
        if not categories_df.empty and "Category ID" in categories_df.columns:
            st.subheader("All Categories")
            
            # Search bar
            search_term = st.text_input("🔍 Search Categories", placeholder="Search by Category ID or Name...", key="category_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    categories_df["Category ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    categories_df["Category Name"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = categories_df[mask]
                if filtered_df.empty:
                    st.info(f"No categories found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = categories_df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(categories_df)} category(ies)")
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"
                
                # Table header - adjust columns based on admin status
                header_cols = st.columns([3, 4, 1, 1] + ([1] if is_admin else []))
                header_labels = ["**Category ID**", "**Category Name**", "**View**", "**Edit**"]
                if is_admin:
                    header_labels.append("**Delete**")
                for col_widget, label in zip(header_cols, header_labels):
                    with col_widget:
                        st.write(label)
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not categories_df[categories_df["Category ID"] == row.get('Category ID', '')].empty:
                        original_idx = int(categories_df[categories_df["Category ID"] == row.get('Category ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    cols = st.columns([3, 4, 1, 1] + ([1] if is_admin else []))
                    col1, col2, col_view, col_edit = cols[:4]
                    col_delete = cols[4] if is_admin else None

                    with col1:
                        st.write(row.get('Category ID', 'N/A'))
                    with col2:
                        st.write(row.get('Category Name', 'N/A'))
                    with col_view:
                        if st.button("👁️", key=f"category_view_{row.get('Category ID', idx)}", use_container_width=True, help="View details"):
                            record = {
                                "Category ID": row.get("Category ID", ""),
                                "Category Name": row.get("Category Name", ""),
                            }
                            _open_view_modal(
                                "category",
                                f"Category Details: {row.get('Category Name', '')}",
                                record,
                                ["Category ID", "Category Name"],
                            )
                    with col_edit:
                        edit_key = f"edit_cat_{row.get('Category ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this category"):
                            st.session_state["edit_category_id"] = row.get('Category ID', '')
                            st.session_state["edit_category_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin and col_delete is not None:
                        with col_delete:
                            delete_key = f"delete_cat_{row.get('Category ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this category"):
                                category_name_to_delete = row.get('Category Name', 'Unknown')
                                category_id_to_delete = row.get('Category ID', 'Unknown')
                                if delete_data(SHEETS["categories"], original_idx):
                                    # Set success message
                                    st.session_state["category_success_message"] = f"✅ Category '{category_name_to_delete}' (ID: {category_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "category_search" in st.session_state:
                                        del st.session_state["category_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete category")
                    
                    st.divider()
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No categories found. Add a new category using the 'Add Category' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_category_id" in st.session_state and st.session_state["edit_category_id"]:
                st.subheader("Edit Category")
                edit_id = st.session_state["edit_category_id"]
                edit_idx = st.session_state.get("edit_category_idx", 0)
                
                category_rows = categories_df[categories_df["Category ID"] == edit_id]
                if not category_rows.empty:
                    category = category_rows.iloc[0]
                    
                    with st.form("edit_category_form"):
                        new_category_id = st.text_input("Category ID", value=category.get("Category ID", ""), disabled=True)
                        new_category_name = st.text_input("Category Name", value=category.get("Category Name", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update Category", use_container_width=True):
                                with st.spinner("Updating category..."):
                                    if update_data(SHEETS["categories"], edit_idx, [new_category_id, new_category_name]):
                                        # Set success message
                                        st.session_state["category_success_message"] = f"✅ Category '{new_category_name}' (ID: {new_category_id}) updated successfully!"
                                        if "edit_category_id" in st.session_state:
                                            del st.session_state["edit_category_id"]
                                        if "edit_category_idx" in st.session_state:
                                            del st.session_state["edit_category_idx"]
                                        # Clear search bar
                                        if "category_search" in st.session_state:
                                            del st.session_state["category_search"]
                                        st.rerun()
                                    else:
                                        st.error("Failed to update category")
                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                if "edit_category_id" in st.session_state:
                                    del st.session_state["edit_category_id"]
                                if "edit_category_idx" in st.session_state:
                                    del st.session_state["edit_category_idx"]
                                st.rerun()
                else:
                    st.warning("Selected category not found in data.")
        else:
            st.info("No categories found. Add a new category using the 'Add Category' tab.")
    
    with tab4:
        # Show success message if exists
        if "subcategory_success_message" in st.session_state:
            st.success(st.session_state["subcategory_success_message"])
            # Clear message after showing
            del st.session_state["subcategory_success_message"]
        
        if not subcategories_df.empty and "SubCategory ID" in subcategories_df.columns:
            st.subheader("All Sub Categories")
            
            # Search bar
            search_term = st.text_input("🔍 Search Sub Categories", placeholder="Search by Sub Category ID, Name, Category ID, or Category Name...", key="subcategory_search")
            
            # Filter data based on search
            if search_term:
                mask = (
                    subcategories_df["SubCategory ID"].astype(str).str.contains(search_term, case=False, na=False) |
                    subcategories_df["SubCategory Name"].astype(str).str.contains(search_term, case=False, na=False) |
                    subcategories_df["Category ID"].astype(str).str.contains(search_term, case=False, na=False)
                )
                # Add Category Name to search if column exists
                if "Category Name" in subcategories_df.columns:
                    mask = mask | subcategories_df["Category Name"].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = subcategories_df[mask]
                if filtered_df.empty:
                    st.info(f"No subcategories found matching '{search_term}'")
                    filtered_df = pd.DataFrame()
            else:
                filtered_df = subcategories_df
            
            if not filtered_df.empty:
                # Show count
                st.caption(f"Showing {len(filtered_df)} of {len(subcategories_df)} subcategory(ies)")
                
                # Check if user is admin
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = user_role.lower() == "admin"
                
                header_cols = st.columns([2, 2, 3, 3, 1, 1] + ([1] if is_admin else []))
                header_labels = [
                    "**Sub Category ID**",
                    "**Category ID**",
                    "**Category Name**",
                    "**Sub Category Name**",
                    "**View**",
                    "**Edit**",
                ]
                if is_admin:
                    header_labels.append("**Delete**")
                for col_widget, label in zip(header_cols, header_labels):
                    with col_widget:
                        st.write(label)
                st.divider()

                # Display table with edit/delete buttons
                for idx, row in filtered_df.iterrows():
                    # Get original index from df for delete/update operations
                    # Convert to Python int to avoid JSON serialization issues
                    if not subcategories_df[subcategories_df["SubCategory ID"] == row.get('SubCategory ID', '')].empty:
                        original_idx = int(subcategories_df[subcategories_df["SubCategory ID"] == row.get('SubCategory ID', '')].index[0])
                    else:
                        original_idx = int(idx) if isinstance(idx, (int, type(pd.NA))) else 0

                    cols = st.columns([2, 2, 3, 3, 1, 1] + ([1] if is_admin else []))
                    col1, col2, col3, col4, col_view, col_edit = cols[:6]
                    col_delete = cols[6] if is_admin else None

                    with col1:
                        st.write(row.get('SubCategory ID', 'N/A'))
                    with col2:
                        st.write(row.get('Category ID', 'N/A'))
                    with col3:
                        st.write(row.get('Category Name', 'N/A'))
                    with col4:
                        st.write(row.get('SubCategory Name', 'N/A'))
                    with col_view:
                        if st.button("👁️", key=f"subcategory_view_{row.get('SubCategory ID', idx)}", use_container_width=True, help="View details"):
                            record = {
                                "Sub Category ID": row.get("SubCategory ID", ""),
                                "Category ID": row.get("Category ID", ""),
                                "Category Name": row.get("Category Name", ""),
                                "Sub Category Name": row.get("SubCategory Name", ""),
                            }
                            _open_view_modal(
                                "subcategory",
                                f"Sub Category Details: {row.get('SubCategory Name', '')}",
                                record,
                                ["Sub Category ID", "Category ID", "Category Name", "Sub Category Name"],
                            )
                    with col_edit:
                        edit_key = f"edit_subcat_{row.get('SubCategory ID', idx)}"
                        if st.button("✏️", key=edit_key, use_container_width=True, help="Edit this subcategory"):
                            st.session_state["edit_subcategory_id"] = row.get('SubCategory ID', '')
                            st.session_state["edit_subcategory_idx"] = int(original_idx)  # Ensure it's a Python int
                            st.rerun()
                    # Only show delete button for admin users
                    if is_admin and col_delete is not None:
                        with col_delete:
                            delete_key = f"delete_subcat_{row.get('SubCategory ID', idx)}"
                            if st.button("🗑️", key=delete_key, use_container_width=True, help="Delete this subcategory"):
                                subcategory_name_to_delete = row.get('SubCategory Name', 'Unknown')
                                subcategory_id_to_delete = row.get('SubCategory ID', 'Unknown')
                                if delete_data(SHEETS["subcategories"], original_idx):
                                    # Set success message
                                    st.session_state["subcategory_success_message"] = f"✅ Sub Category '{subcategory_name_to_delete}' (ID: {subcategory_id_to_delete}) deleted successfully!"
                                    # Clear search bar
                                    if "subcategory_search" in st.session_state:
                                        del st.session_state["subcategory_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to delete subcategory")
                    
                    st.divider()
                _render_view_modal("subcategory")
            elif search_term:
                # Search returned no results, but search was performed
                pass
            else:
                st.info("No subcategories found. Add a new subcategory using the 'Add Sub Category' tab.")

            # Edit form (shown when edit button is clicked)
            if "edit_subcategory_id" in st.session_state and st.session_state["edit_subcategory_id"]:
                st.subheader("Edit Sub Category")
                edit_id = st.session_state["edit_subcategory_id"]
                edit_idx = st.session_state.get("edit_subcategory_idx", 0)
                
                subcategory_rows = subcategories_df[subcategories_df["SubCategory ID"] == edit_id]
                if not subcategory_rows.empty:
                    subcategory = subcategory_rows.iloc[0]
                    
                    with st.form("edit_subcategory_form"):
                        new_subcategory_id = st.text_input("Sub Category ID", value=subcategory.get("SubCategory ID", ""), disabled=True)
                        
                        # Category dropdown for editing - show category names
                        selected_category_name = None
                        if not categories_df.empty:
                            category_options = categories_df["Category Name"].tolist()
                            current_category_id = subcategory.get("Category ID", "")
                            # Find the category name for the current category ID
                            if not categories_df[categories_df["Category ID"] == current_category_id].empty:
                                current_category_name = categories_df[categories_df["Category ID"] == current_category_id]["Category Name"].iloc[0]
                                if current_category_name in category_options:
                                    default_index = category_options.index(current_category_name) + 1
                                else:
                                    default_index = 0
                            else:
                                default_index = 0
                            selected_category_name = st.selectbox("Category *", ["Select category"] + category_options, index=default_index)
                            
                            # Map selected category name back to category ID
                            if selected_category_name != "Select category":
                                new_category_id = categories_df[categories_df["Category Name"] == selected_category_name]["Category ID"].iloc[0]
                                new_category_name = selected_category_name
                            else:
                                new_category_id = "Select category"
                                new_category_name = ""
                        else:
                            new_category_id = st.text_input("Category ID *", value=subcategory.get("Category ID", ""))
                            new_category_name = st.text_input("Category Name *", value=subcategory.get("Category Name", ""))
                            selected_category_name = None
                        
                        new_subcategory_name = st.text_input("Sub Category Name", value=subcategory.get("SubCategory Name", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update Sub Category", use_container_width=True):
                                if selected_category_name == "Select category" or (selected_category_name is None and new_category_id == "Select category"):
                                    st.error("Please select a category")
                                else:
                                    with st.spinner("Updating subcategory..."):
                                        # Update: SubCategory ID, Category ID, Category Name, SubCategory Name
                                        if update_data(SHEETS["subcategories"], edit_idx, [new_subcategory_id, new_category_id, new_category_name, new_subcategory_name]):
                                            # Set success message
                                            st.session_state["subcategory_success_message"] = f"✅ Sub Category '{new_subcategory_name}' (ID: {new_subcategory_id}) updated successfully!"
                                            if "edit_subcategory_id" in st.session_state:
                                                del st.session_state["edit_subcategory_id"]
                                            if "edit_subcategory_idx" in st.session_state:
                                                del st.session_state["edit_subcategory_idx"]
                                            # Clear search bar
                                            if "subcategory_search" in st.session_state:
                                                del st.session_state["subcategory_search"]
                                            st.rerun()
                                        else:
                                            st.error("Failed to update subcategory")
                        with col2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                if "edit_subcategory_id" in st.session_state:
                                    del st.session_state["edit_subcategory_id"]
                                if "edit_subcategory_idx" in st.session_state:
                                    del st.session_state["edit_subcategory_idx"]
                                st.rerun()
                else:
                    st.warning("Selected subcategory not found in data.")
        else:
            st.info("No subcategories found. Add a new subcategory using the 'Add Sub Category' tab.")

def generate_asset_id() -> str:
    """Generate a unique Asset ID/Barcode"""
    import uuid
    # Generate a short unique ID
    return f"AST-{uuid.uuid4().hex[:8].upper()}"

def asset_master_form():
    """Asset Master Form"""
    st.header("📦 Asset Master Management")
    
    MAX_ATTACHMENT_CHARS = 48000  # ~35 KB base64 fits Google Sheets cell limit

    asset_expected_headers = [
        "Asset ID",
        "Asset Name",
        "Category",
        "Sub Category",
        "Model/Serial No",
        "Purchase Date",
        "Purchase Cost",
        "Warranty",
        "Supplier",
        "Location",
        "Assigned To",
        "Condition",
        "Status",
        "Remarks",
        "Attachment",
    ]
    ensure_sheet_headers(SHEETS["assets"], asset_expected_headers)

    assets_df = read_data(SHEETS["assets"])
    locations_df = read_data(SHEETS["locations"])
    suppliers_df = read_data(SHEETS["suppliers"])
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    users_df = read_data(SHEETS["users"])
    
    def find_column(df: pd.DataFrame, targets):
        for target in targets:
            for col in df.columns:
                if str(col).strip().lower() == target:
                    return col
        return None

    def unique_clean(series: pd.Series) -> list[str]:
        return sorted(series.dropna().astype(str).str.strip().unique()) if not series.empty else []

    category_name_col = find_column(categories_df, ["category name", "category"])
    category_id_col = find_column(categories_df, ["category id", "categoryid"])
    subcat_name_col = find_column(subcategories_df, ["subcategory name", "sub category name", "subcategory", "sub category"])
    subcat_cat_id_col = find_column(subcategories_df, ["category id", "categoryid"])
    subcat_cat_name_col = find_column(subcategories_df, ["category name", "category"])
    user_username_col = find_column(users_df, ["username", "user name", "name"])

    category_norm_series = None
    if not categories_df.empty and category_name_col:
        category_norm_series = categories_df[category_name_col].astype(str).str.strip().str.lower()

    subcat_name_norm_series = None
    if not subcategories_df.empty and subcat_name_col:
        subcat_name_norm_series = subcategories_df[subcat_name_col].astype(str).str.strip().str.lower()

    subcat_cat_name_norm_series = None
    if not subcategories_df.empty and subcat_cat_name_col:
        subcat_cat_name_norm_series = subcategories_df[subcat_cat_name_col].astype(str).str.strip().str.lower()

    tab1, tab2, tab3 = st.tabs(["Add New Asset", "View/Edit Assets", "Reports"])
    
    with tab1:
        st.markdown(
            """
            <style>
            div[data-testid="stTabPanel"] div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            div[data-testid="stTabPanel"] div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stTabPanel"] div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            [data-testid="stStatusWidget"],
            .stSpinner {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        with st.form("asset_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                auto_generate = st.checkbox("Auto-generate Asset ID", value=True)
                if auto_generate:
                    # Generate ID once and store in session state
                    if "generated_asset_id" not in st.session_state:
                        st.session_state["generated_asset_id"] = generate_asset_id()
                    asset_id = st.text_input("Asset ID / Barcode", value=st.session_state["generated_asset_id"], disabled=True)
                else:
                    asset_id = st.text_input("Asset ID / Barcode *")
                    if "generated_asset_id" in st.session_state:
                        del st.session_state["generated_asset_id"]
                
                asset_name = st.text_input("Asset Name *")
                
                if not subcategories_df.empty and subcat_name_col:
                    subcategory_name_options = unique_clean(subcategories_df[subcat_name_col])
                else:
                    subcategory_name_options = []

                if subcategory_name_options:
                    category = st.selectbox(
                        "Category (Sub Category Name) *",
                        ["Select sub category"] + subcategory_name_options,
                        key="asset_category_select",
                    )
                else:
                    category = st.selectbox(
                        "Category (Sub Category Name) *",
                        ["No subcategories available"],
                        disabled=True,
                        key="asset_category_select",
                    )
                    category = ""

                category_names_for_selected = []
                selected_subcat_norm = str(category).strip().lower()
                matching_subcats = pd.DataFrame()
                if (
                    category
                    and category not in ("Select sub category", "")
                    and subcat_name_norm_series is not None
                ):
                    matching_subcats = subcategories_df[subcat_name_norm_series == selected_subcat_norm]
                    if not matching_subcats.empty:
                        if subcat_cat_name_col:
                            category_names_for_selected = unique_clean(matching_subcats[subcat_cat_name_col])
                        elif (
                            subcat_cat_id_col
                            and category_id_col
                            and category_name_col
                            and category_norm_series is not None
                        ):
                            ids = matching_subcats[subcat_cat_id_col].dropna().astype(str)
                            cat_matches = categories_df[
                                categories_df[category_id_col]
                                .astype(str)
                                .str.strip()
                                .str.lower()
                                .isin(ids.str.strip().str.lower())
                            ]
                            if not cat_matches.empty:
                                category_names_for_selected = unique_clean(cat_matches[category_name_col])

                category_help = None
                if not category_names_for_selected:
                    if category in ("Select sub category", ""):
                        category_help = "Please select a sub category first."
                    else:
                        category_help = "No category mapping found for the selected sub category."

                subcategory_options = (
                    ["Select category name"] + category_names_for_selected
                    if category_names_for_selected
                    else ["None"]
                )

                subcategory = st.selectbox(
                    "Sub Category (Category Name)",
                    subcategory_options,
                    key="asset_subcategory_select",
                    help=category_help,
                )
                
                model_serial = st.text_input("Model / Serial No")
                purchase_date = st.date_input("Purchase Date")
            
            with col2:
                purchase_cost = st.number_input("Purchase Cost", min_value=0.0, value=0.0, step=0.01)
                warranty = st.selectbox("Warranty", ["No", "Yes"])
                
                if not suppliers_df.empty:
                    supplier_options = suppliers_df["Supplier Name"].tolist()
                    supplier = st.selectbox("Supplier", ["None"] + supplier_options)
                else:
                    supplier = st.text_input("Supplier")
                
                if not locations_df.empty:
                    location_options = locations_df["Location Name"].tolist()
                    location = st.selectbox("Location", ["None"] + location_options)
                else:
                    location = st.text_input("Location")
                
                refresh_key = st.session_state.pop("refresh_asset_users", False)
                if refresh_key:
                    users_df = read_data(SHEETS["users"])
                if not users_df.empty and user_username_col and user_username_col in users_df.columns:
                    user_options = ["None"] + users_df[user_username_col].dropna().astype(str).tolist()
                    assigned_to = st.selectbox("Assigned To", user_options)
                else:
                    assigned_to = st.text_input("Assigned To")
                condition = st.selectbox("Condition", ["Excellent", "Good", "Fair", "Poor", "Damaged"])
                status = st.selectbox(
                    "Status",
                    [
                        "Active",
                        "Inactive",
                        "Maintenance",
                        "Retired",
                        "Assigned",
                        "Returned",
                        "Under Repair",
                    ],
                )
                remarks = st.text_area("Remarks")
                attachment_file = st.file_uploader(
                    "Attachment (Image or File)",
                    type=None,
                    help="Upload related documents or images.",
                )
                attachment = ""
                attachment_too_large = False
                if attachment_file is not None:
                    file_content = attachment_file.getvalue()
                    encoded = base64.b64encode(file_content).decode("utf-8")
                    if len(encoded) > MAX_ATTACHMENT_CHARS:
                        st.warning("Attachment is too large to store. Please upload a smaller file (approx. < 35 KB).", icon="⚠️")
                        attachment = ""
                        attachment_too_large = True
                    else:
                        attachment = f"data:{attachment_file.type};name={attachment_file.name};base64,{encoded}"
            
            submitted = st.form_submit_button("Add Asset", use_container_width=True)

            if submitted:
                if attachment_file is not None and attachment == "" and attachment_too_large:
                    st.error("Attachment was not uploaded because it exceeds the allowed size. Please upload a smaller file.")
                elif not asset_id or not asset_name:
                    st.error("Please fill in Asset ID and Asset Name")
                elif not assets_df.empty and asset_id in assets_df["Asset ID"].values:
                    st.error("Asset ID already exists")
                else:
                    data = [
                        asset_id,
                        asset_name,
                        category if category not in ("", "Select sub category") else "",
                        subcategory
                        if subcategory not in ("", "None", "Select category", "Select category name")
                        else "",
                        model_serial,
                        purchase_date.strftime("%Y-%m-%d") if purchase_date else "",
                        purchase_cost,
                        warranty,
                        supplier if supplier != "None" else "",
                        location if location != "None" else "",
                        assigned_to if assigned_to != "None" else "",
                        condition,
                        status,
                        remarks,
                        attachment,
                    ]
                    if append_data(SHEETS["assets"], data):
                        st.success("Asset added successfully!")
                        # Clear generated asset ID
                        if "generated_asset_id" in st.session_state:
                            del st.session_state["generated_asset_id"]
                        st.rerun()
                    else:
                        st.error("Failed to add asset")
    
    with tab2:
        if "asset_success_message" in st.session_state:
            st.success(st.session_state["asset_success_message"])
            del st.session_state["asset_success_message"]

        if not assets_df.empty:
            st.subheader("All Assets")

            st.markdown(
                """
                <style>
                div[data-testid="column"] div[data-testid="stButton"] button,
                div[data-testid="column"] button[kind="secondary"],
                div[data-testid="column"] div[data-testid^="baseButton"] button {
                    border: none !important;
                    background: transparent !important;
                    box-shadow: none !important;
                    padding: 0 !important;
                }
                div[data-testid="column"] div[data-testid="stButton"] button:focus-visible,
                div[data-testid="column"] button[kind="secondary"]:focus-visible,
                div[data-testid="column"] div[data-testid^="baseButton"] button:focus-visible {
                    outline: none !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            search_term = st.text_input(
                "🔍 Search Assets",
                placeholder="Search by Asset ID, Name, or Location...",
                key="asset_search",
            )

            if search_term:
                mask = (
                    assets_df["Asset ID"].astype(str).str.contains(search_term, case=False, na=False)
                    | assets_df["Asset Name"].astype(str).str.contains(search_term, case=False, na=False)
                    | assets_df.get("Location", pd.Series(dtype=str)).astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = assets_df[mask]
                if filtered_df.empty:
                    st.info(f"No assets found matching '{search_term}'")
                    return
            else:
                filtered_df = assets_df

            st.caption(f"Showing {len(filtered_df)} of {len(assets_df)} asset(s)")

            user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
            is_admin = str(user_role).lower() == "admin"

            condition_options = ["Excellent", "Good", "Fair", "Poor", "Damaged"]
            status_options = [
                "Active",
                "Inactive",
                "Maintenance",
                "Retired",
                "Assigned",
                "Returned",
                "Under Repair",
            ]

            view_placeholder = st.empty()
            edit_placeholder = st.empty()

            if is_admin:
                header_cols = st.columns([3, 4, 4, 3, 1, 1, 1])
            else:
                header_cols = st.columns([3, 4, 4, 3, 1, 1])

            header_labels = ["**Asset ID**", "**Asset Name**", "**Category**", "**Status**"]
            for col, label in zip(header_cols, header_labels):
                with col:
                    st.write(label)

            st.divider()

            button_counter = 0
            for idx, row in filtered_df.iterrows():
                asset_id_value = row.get("Asset ID", "")
                unique_suffix = f"{asset_id_value}_{button_counter}"
                button_counter += 1

                matching_rows = assets_df[assets_df["Asset ID"].astype(str) == str(asset_id_value)]
                original_idx = int(matching_rows.index[0]) if not matching_rows.empty else int(idx)

                if is_admin:
                    cols = st.columns([3, 4, 4, 3, 1, 1, 1])
                    col_asset, col_name, col_category, col_status, col_view, col_edit, col_delete = cols
                else:
                    cols = st.columns([3, 4, 4, 3, 1, 1])
                    col_asset, col_name, col_category, col_status, col_view, col_edit = cols
                    col_delete = None

                is_editing = (
                    st.session_state.get("edit_asset_id") == asset_id_value
                    and st.session_state.get("edit_asset_idx") == original_idx
                )

                with col_asset:
                    st.write(asset_id_value or "N/A")
                with col_name:
                    st.write(row.get("Asset Name", row.get("Asset Name *", "N/A")))
                category_display = "- " if is_editing else row.get("Category", row.get("Category Name", "N/A"))
                status_value = row.get("Status", "N/A")
                status_display = "- " if is_editing else status_value

                with col_category:
                    st.write(category_display)
                with col_status:
                    if is_editing or str(status_display).strip().lower() != "active":
                        st.write(status_display)
                    else:
                        st.markdown(
                            f"<span style='color: #c1121f; font-weight: 600;'>{status_display}</span>",
                            unsafe_allow_html=True,
                        )

                if is_editing:
                    col_view.write("-")
                    with col_edit:
                        st.write("-")
                    if is_admin and col_delete is not None:
                        with col_delete:
                            st.write("-")
                else:
                    with col_view:
                        if st.button(
                            "👁️",
                            key=f"asset_view_{unique_suffix}",
                            use_container_width=True,
                            help="View details",
                        ):
                            record = {
                                "Asset ID": asset_id_value,
                                "Asset Name": row.get("Asset Name", row.get("Asset Name *", "")),
                                "Category": row.get("Category", row.get("Category Name", "")),
                                "Sub Category": row.get("Sub Category", row.get("SubCategory Name", "")),
                                "Location": row.get("Location", ""),
                                "Assigned To": row.get("Assigned To", ""),
                                "Status": row.get("Status", ""),
                                "Condition": row.get("Condition", ""),
                                "Supplier": row.get("Supplier", ""),
                                "Model / Serial No": row.get("Model / Serial No", row.get("Model/Serial No", "")),
                                "Purchase Date": row.get("Purchase Date", ""),
                                "Purchase Cost": row.get("Purchase Cost", ""),
                                "Warranty": row.get("Warranty", ""),
                                "Remarks": row.get("Remarks", ""),
                            }
                            _open_view_modal(
                                "asset",
                                f"Asset Details: {asset_id_value}",
                                record,
                                [
                                    "Asset ID",
                                    "Asset Name",
                                    "Category",
                                    "Sub Category",
                                    "Location",
                                    "Assigned To",
                                    "Status",
                                    "Condition",
                                    "Supplier",
                                    "Model / Serial No",
                                    "Purchase Date",
                                    "Purchase Cost",
                                    "Warranty",
                                    "Remarks",
                                ],
                            )

                    with col_edit:
                        if st.button("✏️", key=f"asset_edit_{unique_suffix}", use_container_width=True, help="Edit this asset"):
                            st.session_state["edit_asset_id"] = asset_id_value
                            st.session_state["edit_asset_idx"] = original_idx
                            st.rerun()

                    if is_admin and col_delete is not None:
                        with col_delete:
                            if st.button("🗑️", key=f"asset_delete_{unique_suffix}", use_container_width=True, help="Delete this asset"):
                                if delete_data(SHEETS["assets"], original_idx):
                                    st.session_state["asset_success_message"] = f"🗑️ Asset '{asset_id_value}' deleted."
                                    st.rerun()
                                else:
                                    st.error("Failed to delete asset")

                st.divider()

            _render_view_modal("asset", view_placeholder)

            if "edit_asset_id" in st.session_state and st.session_state["edit_asset_id"]:
                with edit_placeholder.container():
                    edit_id = st.session_state["edit_asset_id"]
                    edit_idx = st.session_state.get("edit_asset_idx", 0)
                    edit_rows = assets_df[assets_df["Asset ID"].astype(str) == str(edit_id)]
                    if edit_rows.empty:
                        st.warning("Selected asset not found in data.")
                    else:
                        row = edit_rows.iloc[0]
                        st.subheader(f"Edit Asset: {edit_id}")
                        with st.form(f"asset_edit_form_{edit_id}"):
                            col_left, col_right = st.columns(2)

                            with col_left:
                                st.text_input("Asset ID", value=edit_id, disabled=True)
                                new_name = st.text_input("Asset Name *", value=row.get("Asset Name", row.get("Asset Name *", "")))

                                edit_subcategory_name_options = []
                                if not subcategories_df.empty and subcat_name_col:
                                    edit_subcategory_name_options.extend(
                                        subcategories_df[subcat_name_col].dropna().astype(str).str.strip().tolist()
                                    )
                                current_category_value = row.get("Category", row.get("Category Name", ""))
                                if current_category_value and current_category_value not in edit_subcategory_name_options:
                                    edit_subcategory_name_options.append(current_category_value)
                                edit_subcategory_name_options = sorted(dict.fromkeys(edit_subcategory_name_options))

                                if edit_subcategory_name_options:
                                    cat_list = ["Select sub category"] + edit_subcategory_name_options
                                    try:
                                        default_cat_index = cat_list.index(current_category_value) if current_category_value in cat_list else 0
                                    except ValueError:
                                        default_cat_index = 0
                                    selected_category = st.selectbox("Category (Sub Category Name)", cat_list, index=default_cat_index)
                                else:
                                    selected_category = st.selectbox(
                                        "Category (Sub Category Name)",
                                        ["No subcategories available"],
                                        disabled=True,
                                    )
                                    selected_category = ""

                                category_names_for_selected_edit = []
                                selected_category_norm = str(selected_category).strip().lower()
                                if (
                                    selected_category
                                    and selected_category not in ("Select sub category", "")
                                    and subcat_name_norm_series is not None
                                ):
                                    matching_rows_edit = subcategories_df[subcat_name_norm_series == selected_category_norm]
                                    if not matching_rows_edit.empty:
                                        if subcat_cat_name_col:
                                            category_names_for_selected_edit = unique_clean(matching_rows_edit[subcat_cat_name_col])
                                        elif (
                                            subcat_cat_id_col
                                            and category_id_col
                                            and category_name_col
                                            and category_norm_series is not None
                                        ):
                                            ids_edit = matching_rows_edit[subcat_cat_id_col].dropna().astype(str)
                                            cat_matches_edit = categories_df[
                                                categories_df[category_id_col]
                                                .astype(str)
                                                .str.strip()
                                                .str.lower()
                                                .isin(ids_edit.str.strip().str.lower())
                                            ]
                                            if not cat_matches_edit.empty:
                                                category_names_for_selected_edit = unique_clean(cat_matches_edit[category_name_col])

                                current_subcat_value = row.get(
                                    "Sub Category",
                                    row.get("SubCategory Name", row.get("Sub Category Name", "")),
                                )
                                if current_subcat_value and current_subcat_value not in category_names_for_selected_edit:
                                    category_names_for_selected_edit.append(current_subcat_value)
                                category_names_for_selected_edit = sorted(dict.fromkeys(category_names_for_selected_edit))

                                edit_subcategory_options = (
                                    ["Select category name"] + category_names_for_selected_edit
                                    if category_names_for_selected_edit
                                    else ["None"]
                                )
                                try:
                                    default_subcat_index = (
                                        edit_subcategory_options.index(current_subcat_value)
                                        if current_subcat_value in edit_subcategory_options
                                        else 0
                                    )
                                except ValueError:
                                    default_subcat_index = 0

                                subcategory_help_edit_final = None
                                if not category_names_for_selected_edit:
                                    if selected_category in ("Select sub category", ""):
                                        subcategory_help_edit_final = "Please select a sub category first."
                                    else:
                                        subcategory_help_edit_final = "No category mapping found for the selected sub category."

                                selected_subcategory = st.selectbox(
                                    "Sub Category (Category Name)",
                                    edit_subcategory_options,
                                    index=default_subcat_index,
                                    key=f"asset_edit_subcategory_final_{edit_id}",
                                    help=subcategory_help_edit_final,
                                )

                                model_serial = st.text_input(
                                    "Model / Serial No",
                                    value=row.get("Model / Serial No", row.get("Model/Serial No", "")),
                                )

                                purchase_date_value = row.get("Purchase Date", "")
                                try:
                                    default_date = (
                                        datetime.strptime(purchase_date_value, "%Y-%m-%d").date()
                                        if purchase_date_value
                                        else datetime.now().date()
                                    )
                                except Exception:
                                    default_date = datetime.now().date()
                                new_purchase_date = st.date_input("Purchase Date", value=default_date)

                            with col_right:
                                purchase_cost = st.number_input(
                                    "Purchase Cost",
                                    min_value=0.0,
                                    value=float(str(row.get("Purchase Cost", 0)).replace(",", "") or 0),
                                    step=0.01,
                                )
                                warranty_existing = str(row.get("Warranty", "")).strip().lower()
                                warranty_edit = st.selectbox(
                                    "Warranty",
                                    ["No", "Yes"],
                                    index=1 if warranty_existing == "yes" else 0,
                                )

                                if not suppliers_df.empty:
                                    supplier_options = suppliers_df["Supplier Name"].tolist()
                                    supplier_list = ["None"] + supplier_options
                                    try:
                                        default_supplier_index = supplier_list.index(row.get("Supplier", "None"))
                                    except ValueError:
                                        default_supplier_index = 0
                                    new_supplier = st.selectbox("Supplier", supplier_list, index=default_supplier_index)
                                else:
                                    new_supplier = st.text_input("Supplier", value=row.get("Supplier", ""))

                                if not locations_df.empty:
                                    location_options = locations_df["Location Name"].tolist()
                                    location_list = ["None"] + location_options
                                    try:
                                        default_location_index = location_list.index(row.get("Location", "None"))
                                    except ValueError:
                                        default_location_index = 0
                                    new_location = st.selectbox("Location", location_list, index=default_location_index)
                                else:
                                    new_location = st.text_input("Location", value=row.get("Location", ""))

                                if not users_df.empty and "Username" in users_df.columns:
                                    user_options_edit = ["None"] + users_df["Username"].dropna().astype(str).tolist()
                                    try:
                                        assigned_default = user_options_edit.index(str(row.get("Assigned To", "None")))
                                    except ValueError:
                                        assigned_default = 0
                                    assigned_to = st.selectbox("Assigned To", user_options_edit, index=assigned_default)
                                else:
                                    assigned_to = st.text_input("Assigned To", value=row.get("Assigned To", ""))

                                condition = st.selectbox(
                                    "Condition",
                                    condition_options,
                                    index=condition_options.index(str(row.get("Condition", "Good"))) if str(row.get("Condition", "Good")) in condition_options else 1,
                                )
                                status = st.selectbox(
                                    "Status",
                                    status_options,
                                    index=status_options.index(str(row.get("Status", "Active"))) if str(row.get("Status", "Active")) in status_options else 0,
                                )
                                remarks = st.text_area("Remarks", value=row.get("Remarks", ""))
                                existing_attachment = row.get("Attachment", "")
                                if existing_attachment:
                                    st.caption("Existing attachment on file. Upload a new one to replace it.")
                                attachment_upload = st.file_uploader(
                                    "Attachment (Image or File)",
                                    type=None,
                                    key=f"asset_attachment_{edit_id}",
                                )
                                attachment_value = existing_attachment
                                attachment_too_large_edit = False
                                if attachment_upload is not None:
                                    encoded_edit = base64.b64encode(attachment_upload.getvalue()).decode("utf-8")
                                    if len(encoded_edit) > MAX_ATTACHMENT_CHARS:
                                        st.warning("Attachment is too large to store. Please upload a smaller file (approx. < 35 KB).", icon="⚠️")
                                        attachment_too_large_edit = True
                                    else:
                                        attachment_value = f"data:{attachment_upload.type};name={attachment_upload.name};base64,{encoded_edit}"

                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.form_submit_button("Update Asset", use_container_width=True):
                                    if attachment_upload is not None and attachment_too_large_edit:
                                        st.error("Attachment was not updated because it exceeds the allowed size. Please upload a smaller file.")
                                        st.stop()
                                    updated_data = [
                                        edit_id,
                                        new_name,
                                        selected_category if selected_category not in ("", "Select sub category") else row.get("Category", ""),
                                        selected_subcategory
                                        if selected_subcategory not in ("", "None", "Select category", "Select category name")
                                        else row.get("Sub Category", row.get("SubCategory Name", "")),
                                        model_serial,
                                        new_purchase_date.strftime("%Y-%m-%d"),
                                        purchase_cost,
                                        warranty_edit,
                                        new_supplier if new_supplier != "None" else "",
                                        new_location if new_location != "None" else "",
                                        assigned_to if assigned_to != "None" else "",
                                        condition,
                                        status,
                                        remarks,
                                        attachment_value,
                                    ]

                                    if update_data(SHEETS["assets"], edit_idx, updated_data):
                                        st.session_state["asset_success_message"] = f"✅ Asset '{edit_id}' updated successfully!"
                                        st.session_state.pop("edit_asset_id", None)
                                        st.session_state.pop("edit_asset_idx", None)
                                        if "asset_search" in st.session_state:
                                            del st.session_state["asset_search"]
                                        st.rerun()
                                    else:
                                        st.error("Failed to update asset")
                            with col_cancel:
                                if st.form_submit_button("Cancel", use_container_width=True):
                                    st.session_state.pop("edit_asset_id", None)
                                    st.session_state.pop("edit_asset_idx", None)
                                    st.rerun()

        else:
            st.info("No assets found. Add a new asset using the 'Add New Asset' tab.")

    with tab3:
        if assets_df.empty:
            st.info("No assets available to generate a report.")
        else:
            st.subheader("Asset Master Report")

            status_series = assets_df.get("Status", pd.Series(dtype=str))
            location_series = assets_df.get("Location", pd.Series(dtype=str))
            category_series = assets_df.get("Category", assets_df.get("Category Name", pd.Series(dtype=str)))

            status_options = (
                sorted(status_series.dropna().astype(str).str.strip().unique().tolist())
                if not status_series.empty
                else []
            )
            location_options = (
                sorted(location_series.dropna().astype(str).str.strip().unique().tolist())
                if not location_series.empty
                else []
            )
            category_options = (
                sorted(category_series.dropna().astype(str).str.strip().unique().tolist())
                if isinstance(category_series, pd.Series) and not category_series.empty
                else []
            )

            col_filters = st.columns(3)
            with col_filters[0]:
                selected_status = st.multiselect("Filter by Status", status_options)
            with col_filters[1]:
                selected_location = st.multiselect("Filter by Location", location_options)
            with col_filters[2]:
                selected_category = st.multiselect("Filter by Category", category_options)

            report_df = assets_df.copy()
            if selected_status and not status_series.empty:
                report_df = report_df[
                    report_df["Status"].astype(str).str.strip().isin(selected_status)
                ]
            if selected_location and not location_series.empty:
                report_df = report_df[
                    report_df["Location"].astype(str).str.strip().isin(selected_location)
                ]
            if selected_category and isinstance(category_series, pd.Series):
                category_column_name = category_series.name
                report_df = report_df[
                    report_df[category_column_name].astype(str).str.strip().isin(selected_category)
                ]

            if report_df.empty:
                st.warning("No records match the selected filters.")
            else:
                st.caption(f"{len(report_df)} asset(s) match the current filters.")
                st.dataframe(report_df, use_container_width=True)

                excel_buffer = BytesIO()
                try:
                    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                        report_df.to_excel(writer, index=False, sheet_name="Assets")
                    excel_buffer.seek(0)
                    excel_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    excel_filename = "asset_master_report.xlsx"
                except Exception:
                    excel_buffer = BytesIO()
                    report_df.to_csv(excel_buffer, index=False)
                    excel_buffer.seek(0)
                    excel_mime = "text/csv"
                    excel_filename = "asset_master_report.csv"

                st.download_button(
                    "Download Asset Report",
                    data=excel_buffer,
                    file_name=excel_filename,
                    mime=excel_mime,
                    use_container_width=True,
                )

def asset_transfer_form():
    """Asset Transfer Form"""
    st.header("🚚 Asset Transfer Management")
    
    transfers_df = read_data(SHEETS["transfers"])
    def find_column(df: pd.DataFrame, targets: list[str]) -> str | None:
        for target in targets:
            for col in df.columns:
                if str(col).strip().lower() == target:
                    return col
        return None

    assets_df = read_data(SHEETS["assets"])
    locations_df = read_data(SHEETS["locations"])
    users_df = read_data(SHEETS["users"])

    transfer_id_col = (
        find_column(
            transfers_df,
            [
                "transfer id",
                "transferid",
                "transfer",
                "id",
            ],
        )
        if not transfers_df.empty
        else None
    )
    transfer_asset_id_col = (
        find_column(
            transfers_df,
            [
                "asset id",
                "asset",
                "asset code",
                "assetid",
            ],
        )
        if not transfers_df.empty
        else None
    )
    transfer_from_col = (
        find_column(
            transfers_df,
            [
                "from location",
                "from",
                "source location",
            ],
        )
        if not transfers_df.empty
        else None
    )
    transfer_to_col = (
        find_column(
            transfers_df,
            [
                "to location",
                "to",
                "destination location",
            ],
        )
        if not transfers_df.empty
        else None
    )
    transfer_date_col = (
        find_column(
            transfers_df,
            [
                "transfer date",
                "date",
                "transferdate",
            ],
        )
        if not transfers_df.empty
        else None
    )
    transfer_approved_by_col = (
        find_column(
            transfers_df,
            [
                "approved by",
                "approver",
                "approved",
            ],
        )
        if not transfers_df.empty
        else None
    )

    asset_id_col = find_column(
        assets_df,
        [
            "asset id",
            "asset id / barcode",
            "asset id/barcode",
            "asset id barcode",
            "assetid",
            "asset code",
            "barcode",
        ],
    ) if not assets_df.empty else None

    asset_location_col = (
        find_column(
            assets_df,
            [
                "location",
                "location name",
                "current location",
                "asset location",
            ],
        )
        if not assets_df.empty
        else None
    )
    
    tab1, tab2 = st.tabs(["New Transfer", "View Transfers"])
    
    with tab1:
        st.markdown(
            """
            <style>
            div[data-testid="stForm"] {
                background-color: white !important;
                padding: 20px !important;
                border-radius: 10px !important;
                border: 1px solid #e0e0e0 !important;
            }
            div[data-testid="stForm"] button[kind="primary"],
            button.stButton > button[kind="primary"] {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div[data-testid="stForm"] button[kind="primary"]:hover,
            button.stButton > button[kind="primary"]:hover {
                background-color: #218838 !important;
                border-color: #1e7e34 !important;
            }
            [data-testid="stStatusWidget"],
            .stSpinner {
                display: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        if "transfer_success_message" in st.session_state:
            st.success(st.session_state["transfer_success_message"])
            del st.session_state["transfer_success_message"]

        if "transfer_form_key" not in st.session_state:
            st.session_state["transfer_form_key"] = 0

        form_key = st.session_state["transfer_form_key"]

        with st.form(f"transfer_form_{form_key}"):
            if "generated_transfer_id" not in st.session_state:
                st.session_state["generated_transfer_id"] = generate_transfer_id()

            transfer_id = st.text_input(
                "Transfer ID",
                value=st.session_state["generated_transfer_id"],
                disabled=True,
                key=f"transfer_id_{form_key}",
            )

            if not assets_df.empty:
                asset_column = asset_id_col or assets_df.columns[0]
                asset_options = (
                    assets_df[asset_column]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                    .tolist()
                )
                asset_options = sorted(asset_options)
                asset_id = st.selectbox(
                    "Asset ID *",
                    ["Select asset"] + asset_options,
                    key=f"transfer_asset_{form_key}",
                )
            else:
                asset_id = st.text_input("Asset ID *", key=f"transfer_asset_text_{form_key}")
                st.warning("No assets found. Please add assets first.")

            if not locations_df.empty:
                location_col = None
                for candidate in locations_df.columns:
                    if str(candidate).strip().lower() in {"location name", "location", "name"}:
                        location_col = candidate
                        break
                location_col = location_col or locations_df.columns[0]
                location_options = (
                    locations_df[location_col]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                    .tolist()
                )
                location_options = sorted(location_options)
                col1, col2 = st.columns(2)
                with col1:
                    from_location = st.selectbox(
                        "From Location *",
                        ["Select location"] + location_options,
                        key=f"transfer_from_location_{form_key}",
                    )
                with col2:
                    to_location = st.selectbox(
                        "To Location *",
                        ["Select location"] + location_options,
                        key=f"transfer_to_location_{form_key}",
                    )
            else:
                col1, col2 = st.columns(2)
                with col1:
                    from_location = st.text_input(
                        "From Location *",
                        key=f"transfer_from_location_text_{form_key}",
                    )
                with col2:
                    to_location = st.text_input(
                        "To Location *",
                        key=f"transfer_to_location_text_{form_key}",
                    )

            transfer_date = st.date_input(
                "Transfer Date *",
                value=datetime.now().date(),
                key=f"transfer_date_{form_key}",
            )

            approved_by_options = []
            approved_by_placeholder = "Select approver"
            approved_by_column = None
            if not users_df.empty:
                for col in users_df.columns:
                    if str(col).strip().lower() in {"username", "user name", "name", "full name"}:
                        approved_by_column = col
                        break
                if approved_by_column:
                    approved_by_options = (
                        users_df[approved_by_column]
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .replace("", pd.NA)
                        .dropna()
                        .unique()
                        .tolist()
                    )
                    approved_by_options = sorted(approved_by_options)

            if approved_by_options:
                approved_by = st.selectbox(
                    "Approved By *",
                    [approved_by_placeholder] + approved_by_options,
                    key=f"transfer_approved_by_{form_key}",
                )
            else:
                approved_by = st.text_input(
                    "Approved By *",
                    key=f"transfer_approved_by_text_{form_key}",
                )

            submitted = st.form_submit_button(
                "Create Transfer",
                use_container_width=True,
                type="primary",
            )
            
            if submitted:
                if asset_id == "Select asset" or not asset_id:
                    st.error("Please select an asset")
                elif from_location == "Select location" or to_location == "Select location":
                    st.error("Please select both locations")
                elif from_location == to_location:
                    st.error("From and To locations cannot be the same")
                elif not approved_by or (approved_by_options and approved_by == approved_by_placeholder):
                    st.error("Please enter approver name")
                else:
                    data_map = {
                        (transfer_id_col or "Transfer ID"): transfer_id,
                        (transfer_asset_id_col or "Asset ID"): asset_id,
                        (transfer_from_col or "From Location"): from_location,
                        (transfer_to_col or "To Location"): to_location,
                        (transfer_date_col or "Transfer Date"): transfer_date.strftime("%Y-%m-%d"),
                        (transfer_approved_by_col or "Approved By"): approved_by,
                    }

                    if not transfers_df.empty:
                        column_order = list(transfers_df.columns)
                    else:
                        column_order = [
                            transfer_id_col or "Transfer ID",
                            transfer_asset_id_col or "Asset ID",
                            transfer_from_col or "From Location",
                            transfer_to_col or "To Location",
                            transfer_date_col or "Transfer Date",
                            transfer_approved_by_col or "Approved By",
                        ]
                    data = [data_map.get(col, "") for col in column_order]
                    if append_data(SHEETS["transfers"], data):
                        if not assets_df.empty and asset_id_col:
                            asset_row = assets_df[
                                assets_df[asset_id_col].astype(str).str.strip()
                                == str(asset_id).strip()
                            ]
                            if not asset_row.empty:
                                row_index = int(asset_row.index[0])
                                column_order = list(assets_df.columns)
                                asset_series = asset_row.iloc[0].copy()
                                location_column = asset_location_col
                                if not location_column or location_column not in column_order:
                                    for candidate in column_order:
                                        if str(candidate).strip().lower().startswith("location"):
                                            location_column = candidate
                                            break
                                if location_column and location_column in column_order:
                                    asset_series.loc[location_column] = to_location
                                else:
                                    st.warning(
                                        "Unable to map transfer location back to Assets sheet because the location column could not be identified.",
                                        icon="⚠️",
                                    )
                                asset_series = asset_series.reindex(column_order, fill_value="")

                                asset_data = []
                                for val in asset_series.tolist():
                                    if pd.isna(val):
                                        asset_data.append("")
                                    else:
                                        if hasattr(val, "item"):
                                            try:
                                                val = val.item()
                                            except Exception:
                                                val = str(val)
                                        asset_data.append(val)
                                update_data(SHEETS["assets"], row_index, asset_data)
                        elif assets_df.empty:
                            st.warning("Assets sheet is empty – cannot sync transfer location.", icon="⚠️")
                        elif not asset_id_col:
                            st.warning(
                                "Unable to identify the Asset ID column in the Assets sheet, so the location could not be updated.",
                                icon="⚠️",
                            )

                        st.session_state["transfer_success_message"] = (
                            f"✅ Transfer '{transfer_id}' created successfully!"
                        )
                        if "generated_transfer_id" in st.session_state:
                            del st.session_state["generated_transfer_id"]
                        st.session_state["transfer_form_key"] += 1
                        if "transfer_search" in st.session_state:
                            del st.session_state["transfer_search"]
                        st.rerun()
                    else:
                        st.error("Failed to create transfer")
    
    with tab2:
        if not transfers_df.empty:
            search_term = st.text_input(
                "🔍 Search Transfers",
                placeholder="Search by Transfer ID, Asset ID, Location, Date, or Approver...",
                key="transfer_search",
            )

            filtered_df = transfers_df.copy()
            if search_term:
                term = search_term.strip().lower()
                filtered_df = filtered_df[
                    filtered_df.apply(
                        lambda row: term in " ".join(row.astype(str).str.lower()),
                        axis=1,
                    )
                ]

            if filtered_df.empty:
                if search_term:
                    st.warning("No transfers match your search.")
                else:
                    st.info(
                        "No transfers found. Create a new transfer using the 'New Transfer' tab."
                    )
            else:
                header_cols = st.columns([2, 2, 2, 2, 2, 2])
                headers = [
                    "**Transfer ID**",
                    "**Asset ID**",
                    "**From Location**",
                    "**To Location**",
                    "**Transfer Date**",
                    "**Approved By**",
                ]
                for col, header in zip(header_cols, headers):
                    with col:
                        st.write(header)
                st.divider()

                for _, row in filtered_df.iterrows():
                    cols = st.columns([2, 2, 2, 2, 2, 2])
                    values = [
                        row.get(transfer_id_col or "Transfer ID", row.get("Transfer ID", "N/A")),
                        row.get(transfer_asset_id_col or "Asset ID", row.get("Asset ID", "N/A")),
                        row.get(transfer_from_col or "From Location", row.get("From Location", row.get("From", "N/A"))),
                        row.get(transfer_to_col or "To Location", row.get("To Location", row.get("To", "N/A"))),
                        row.get(transfer_date_col or "Transfer Date", row.get("Transfer Date", "N/A")),
                        row.get(transfer_approved_by_col or "Approved By", row.get("Approved By", "N/A")),
                    ]
                    for col, value in zip(cols, values):
                        with col:
                            st.write(value if value != "" else "N/A")
                    st.divider()
        else:
            st.info("No transfers found. Create a new transfer using the 'New Transfer' tab.")


def asset_maintenance_form():
    """Maintenance Form"""
    st.header("🛠️ Maintenance")

    maintenance_headers = [
        "Maintenance ID",
        "Asset ID",
        "Service Date",
        "Vendor",
        "Issue",
        "Cost",
        "Warranty Used",
        "Next Service Date",
    ]
    ensure_sheet_headers(SHEETS["maintenance"], maintenance_headers)

    maintenance_df = read_data(SHEETS["maintenance"])
    assets_df = read_data(SHEETS["assets"])

    tab1, tab2 = st.tabs(["Add Maintenance Record", "View/Edit Maintenance"])

    style_block = """
        <style>
        div[data-testid="stForm"] {
            background-color: white !important;
            padding: 20px !important;
            border-radius: 10px !important;
            border: 1px solid #e0e0e0 !important;
        }
        div[data-testid="stForm"] button[kind="primary"],
        button.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-color: #28a745 !important;
        }
        div[data-testid="stForm"] button[kind="primary"]:hover,
        button.stButton > button[kind="primary"]:hover {
            background-color: #218838 !important;
            border-color: #1e7e34 !important;
        }
        [data-testid="stStatusWidget"],
        .stSpinner {
            display: none !important;
        }
        </style>
    """

    def parse_date_value(value, fallback=None):
        if fallback is None:
            fallback = datetime.now().date()
        if value is None or value == "":
            return fallback
        if isinstance(value, datetime):
            return value.date()
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            try:
                return datetime.strptime(str(value), "%d/%m/%Y").date()
            except Exception:
                return fallback

    with tab1:
        st.markdown(style_block, unsafe_allow_html=True)

        if "maintenance_success_message" in st.session_state:
            st.success(st.session_state["maintenance_success_message"])
            del st.session_state["maintenance_success_message"]

        if "maintenance_form_key" not in st.session_state:
            st.session_state["maintenance_form_key"] = 0

        form_key = st.session_state["maintenance_form_key"]

        asset_options = []
        if not assets_df.empty and "Asset ID" in assets_df.columns:
            asset_options = ["Select asset"] + (
                assets_df["Asset ID"].dropna().astype(str).str.strip().tolist()
            )

        with st.form(f"maintenance_form_{form_key}"):
            auto_generate = st.checkbox(
                "Auto-generate Maintenance ID",
                value=True,
                key=f"maintenance_auto_{form_key}",
            )
            if auto_generate:
                if "generated_maintenance_id" not in st.session_state:
                    st.session_state["generated_maintenance_id"] = generate_maintenance_id()
                maintenance_id = st.text_input(
                    "Maintenance ID *",
                    value=st.session_state["generated_maintenance_id"],
                    disabled=True,
                    key=f"maintenance_id_{form_key}",
                )
            else:
                maintenance_id = st.text_input(
                    "Maintenance ID *",
                    key=f"maintenance_manual_id_{form_key}",
                )
                if "generated_maintenance_id" in st.session_state:
                    del st.session_state["generated_maintenance_id"]

            if asset_options:
                asset_id = st.selectbox(
                    "Asset ID *",
                    asset_options,
                    key=f"maintenance_asset_{form_key}",
                )
            else:
                asset_id = st.text_input(
                    "Asset ID *",
                    key=f"maintenance_asset_text_{form_key}",
                )
                st.warning("No assets found. Please add assets first.")

            service_date = st.date_input(
                "Service Date *",
                value=datetime.now().date(),
                key=f"maintenance_service_{form_key}",
            )
            vendor = st.text_input("Vendor", key=f"maintenance_vendor_{form_key}")
            issue = st.text_area("Issue", key=f"maintenance_issue_{form_key}")
            cost = st.number_input(
                "Cost",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key=f"maintenance_cost_{form_key}",
            )
            warranty = st.selectbox(
                "Warranty Used",
                ["No", "Yes"],
                key=f"maintenance_warranty_{form_key}",
            )
            schedule_next = st.checkbox(
                "Schedule next service date",
                value=False,
                key=f"maintenance_schedule_next_{form_key}",
            )
            next_service_date = None
            if schedule_next:
                next_service_date = st.date_input(
                    "Next Service Date",
                    value=service_date,
                    key=f"maintenance_next_service_{form_key}",
                )

            submitted = st.form_submit_button(
                "Add Maintenance Record",
                use_container_width=True,
                type="primary",
            )

            if submitted:
                if not maintenance_id:
                    st.error("Please provide a Maintenance ID")
                elif asset_options and asset_id == "Select asset":
                    st.error("Please select an Asset")
                elif not asset_id:
                    st.error("Please provide an Asset ID")
                else:
                    data_map = {
                        "Maintenance ID": maintenance_id,
                        "Asset ID": asset_id,
                        "Service Date": service_date.strftime("%Y-%m-%d"),
                        "Vendor": vendor,
                        "Issue": issue,
                        "Cost": f"{cost:.2f}",
                        "Warranty Used": warranty,
                        "Next Service Date": next_service_date.strftime("%Y-%m-%d") if next_service_date else "",
                    }
                    column_order = (
                        list(maintenance_df.columns)
                        if not maintenance_df.empty
                        else maintenance_headers
                    )
                    data = [data_map.get(col, "") for col in column_order]
                    with st.spinner("Saving maintenance record..."):
                        if append_data(SHEETS["maintenance"], data):
                            if "generated_maintenance_id" in st.session_state:
                                del st.session_state["generated_maintenance_id"]
                            st.session_state["maintenance_success_message"] = (
                                f"✅ Maintenance record '{maintenance_id}' added successfully!"
                            )
                            st.session_state["maintenance_form_key"] += 1
                            if "maintenance_search" in st.session_state:
                                del st.session_state["maintenance_search"]
                            st.rerun()
                        else:
                            st.error("Failed to save maintenance record")

    with tab2:
        user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
        is_admin = str(user_role).lower() == "admin"

        if not maintenance_df.empty:
            search_term = st.text_input(
                "🔍 Search Maintenance Records",
                placeholder="Search by maintenance ID, asset, vendor, or issue...",
                key="maintenance_search",
            )

            filtered_df = maintenance_df.copy()
            if search_term:
                term = search_term.strip().lower()
                filtered_df = filtered_df[
                    filtered_df.apply(
                        lambda row: term in " ".join(row.astype(str).str.lower()),
                        axis=1,
                    )
                ]

            if filtered_df.empty:
                if search_term:
                    st.warning("No maintenance records match your search.")
                else:
                    st.info("No maintenance records found. Add one using the 'Add Maintenance Record' tab.")
            else:
                field_headers = [
                    "**Maintenance ID**",
                    "**Asset ID**",
                    "**Service Date**",
                    "**Vendor**",
                    "**Issue**",
                    "**Cost**",
                    "**Warranty Used**",
                    "**Next Service**",
                ]
                if is_admin:
                    header_cols = st.columns([2, 2, 2, 2, 2, 1, 2, 2, 1, 1])
                else:
                    header_cols = st.columns([2, 2, 2, 2, 2, 1, 2, 2, 1])
                for col_widget, header in zip(header_cols[: len(field_headers)], field_headers):
                    with col_widget:
                        st.write(header)
                with header_cols[len(field_headers)]:
                    st.write("**Edit**")
                if is_admin:
                    with header_cols[-1]:
                        st.write("**Delete**")
                st.divider()

                asset_list = (
                    assets_df["Asset ID"].dropna().astype(str).str.strip().tolist()
                    if not assets_df.empty and "Asset ID" in assets_df.columns
                    else []
                )

                for idx, row in filtered_df.iterrows():
                    if (
                        "Maintenance ID" in maintenance_df.columns
                        and not maintenance_df[
                            maintenance_df["Maintenance ID"].astype(str) == str(row.get("Maintenance ID", ""))
                        ].empty
                    ):
                        original_idx = int(
                            maintenance_df[
                                maintenance_df["Maintenance ID"].astype(str)
                                == str(row.get("Maintenance ID", ""))
                            ].index[0]
                        )
                    else:
                        original_idx = int(idx) if isinstance(idx, int) else int(idx) if str(idx).isdigit() else 0

                    cols = (
                        st.columns([2, 2, 2, 2, 2, 1, 2, 2, 1, 1])
                        if is_admin
                        else st.columns([2, 2, 2, 2, 2, 1, 2, 2, 1])
                    )
                    display_values = [
                        row.get("Maintenance ID", "N/A"),
                        row.get("Asset ID", "N/A"),
                        row.get("Service Date", "N/A"),
                        row.get("Vendor", ""),
                        row.get("Issue", ""),
                        row.get("Cost", ""),
                        row.get("Warranty Used", ""),
                        row.get("Next Service Date", ""),
                    ]
                    for col_widget, value in zip(cols[: len(display_values)], display_values):
                        with col_widget:
                            st.write(value if value not in ("", None) else "N/A")

                    edit_placeholder = cols[len(display_values)]
                    with edit_placeholder:
                        if st.button("✏️", key=f"maintenance_edit_{row.get('Maintenance ID', idx)}"):
                            st.session_state["edit_maintenance_id"] = row.get("Maintenance ID", "")
                            st.session_state["edit_maintenance_idx"] = original_idx
                            st.rerun()

                    if is_admin:
                        with cols[-1]:
                            if st.button(
                                "🗑️",
                                key=f"maintenance_delete_{row.get('Maintenance ID', idx)}",
                            ):
                                if delete_data(SHEETS["maintenance"], original_idx):
                                    st.session_state["maintenance_success_message"] = (
                                        f"🗑️ Maintenance record '{row.get('Maintenance ID', '')}' deleted."
                                    )
                                    st.rerun()
                                else:
                                    st.error("Failed to delete maintenance record")

                    st.divider()

        else:
            st.info("No maintenance records found. Add one using the 'Add Maintenance Record' tab.")

        if (
            "edit_maintenance_id" in st.session_state
            and st.session_state["edit_maintenance_id"]
        ):
            edit_id = st.session_state["edit_maintenance_id"]
            edit_idx = st.session_state.get("edit_maintenance_idx", 0)
            edit_row = maintenance_df[maintenance_df.get("Maintenance ID", pd.Series()).astype(str) == str(edit_id)]

            if not edit_row.empty:
                record = edit_row.iloc[0]
                st.subheader(f"Edit Maintenance: {edit_id}")
                with st.form(f"edit_maintenance_form_{edit_id}"):
                    asset_options_edit = ["Select asset"] + asset_list if asset_list else []
                    if asset_options_edit:
                        try:
                            default_asset_idx = asset_options_edit.index(record.get("Asset ID", ""))
                        except ValueError:
                            default_asset_idx = 0
                        asset_id_new = st.selectbox(
                            "Asset ID *",
                            asset_options_edit,
                            index=default_asset_idx,
                        )
                    else:
                        asset_id_new = st.text_input(
                            "Asset ID *",
                            value=record.get("Asset ID", ""),
                        )

                    service_date_new = st.date_input(
                        "Service Date *",
                        value=parse_date_value(record.get("Service Date")),
                    )
                    vendor_new = st.text_input(
                        "Vendor",
                        value=record.get("Vendor", ""),
                    )
                    issue_new = st.text_area(
                        "Issue",
                        value=record.get("Issue", ""),
                    )
                    try:
                        default_cost = float(str(record.get("Cost", 0)).replace(",", ""))
                    except Exception:
                        default_cost = 0.0
                    cost_new = st.number_input(
                        "Cost",
                        min_value=0.0,
                        value=default_cost,
                        step=0.01,
                    )
                    warranty_new = st.selectbox(
                        "Warranty Used",
                        ["No", "Yes"],
                        index=1 if str(record.get("Warranty Used", "")).lower() == "yes" else 0,
                    )
                    include_next = st.checkbox(
                        "Schedule next service date",
                        value=bool(record.get("Next Service Date")),
                    )
                    next_service_new = None
                    if include_next:
                        next_service_new = st.date_input(
                            "Next Service Date",
                            value=parse_date_value(record.get("Next Service Date")),
                        )

                    col_update, col_cancel = st.columns(2)
                    with col_update:
                        if st.form_submit_button("Update", use_container_width=True):
                            if asset_options_edit and asset_id_new == "Select asset":
                                st.error("Please select an Asset")
                            elif not asset_id_new:
                                st.error("Please provide an Asset ID")
                            else:
                                update_map = {
                                    "Maintenance ID": edit_id,
                                    "Asset ID": asset_id_new,
                                    "Service Date": service_date_new.strftime("%Y-%m-%d"),
                                    "Vendor": vendor_new,
                                    "Issue": issue_new,
                                    "Cost": f"{cost_new:.2f}",
                                    "Warranty Used": warranty_new,
                                    "Next Service Date": next_service_new.strftime("%Y-%m-%d") if next_service_new else "",
                                }
                                column_order = list(maintenance_df.columns)
                                updated_row = [update_map.get(col, record.get(col, "")) for col in column_order]
                                if update_data(SHEETS["maintenance"], int(edit_idx), updated_row):
                                    st.session_state["maintenance_success_message"] = (
                                        f"✅ Maintenance record '{edit_id}' updated successfully!"
                                    )
                                    st.session_state.pop("edit_maintenance_id", None)
                                    st.session_state.pop("edit_maintenance_idx", None)
                                    st.rerun()
                                else:
                                    st.error("Failed to update maintenance record")
                    with col_cancel:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop("edit_maintenance_id", None)
                            st.session_state.pop("edit_maintenance_idx", None)
                            st.rerun()


def employee_assignment_form():
    """Assignment Form"""
    st.header("🧑‍💼 Assignment")

    assignment_headers = [
        "Assignment ID",
        "Username",
        "Asset ID",
        "Issued By",
        "Assignment Date",
        "Expected Return Date",
        "Return Date",
        "Status",
        "Condition on Issue",
        "Remarks",
    ]
    ensure_sheet_headers(SHEETS["assignments"], assignment_headers)

    assignments_df = read_data(SHEETS["assignments"])
    users_df = read_data(SHEETS["users"])
    assets_df = read_data(SHEETS["assets"])

    tab1, tab2 = st.tabs(["Add Assignment", "View/Edit Assignments"])

    style_block = """
        <style>
        div[data-testid="stForm"] {
            background-color: white !important;
            padding: 20px !important;
            border-radius: 10px !important;
            border: 1px solid #e0e0e0 !important;
        }
        div[data-testid="stForm"] button[kind="primary"],
        button.stButton > button[kind="primary"] {
            background-color: #28a745 !important;
            color: white !important;
            border-color: #28a745 !important;
        }
        div[data-testid="stForm"] button[kind="primary"]:hover,
        button.stButton > button[kind="primary"]:hover {
            background-color: #218838 !important;
            border-color: #1e7e34 !important;
        }
/* Remove border from secondary buttons (e.g., 👁️, ✏️, 🗑️) */
        div[data-testid="stForm"] button[kind="secondary"],
        button.stButton > button[kind="secondary"],
        [data-testid="stBaseButton-secondary"] {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            background: transparent !important; /* optional: makes it flat */
        }
        div[data-testid="stForm"] button[kind="secondary"]:hover,
        button.stButton > button[kind="secondary"]:hover {
            border: none !important;
            box-shadow: none !important;
            background: #f9f9f9 !important; /* optional hover effect */
        }
















        [data-testid="stStatusWidget"],
        .stSpinner {
            display: none !important;
        }
        </style>
    """

    def parse_date_value(value, fallback=None):
        if fallback is None:
            fallback = datetime.now().date()
        if value in ("", None):
            return fallback
        if isinstance(value, datetime):
            return value.date()
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            try:
                return datetime.strptime(str(value), "%d/%m/%Y").date()
            except Exception:
                return fallback

    user_options = []
    if not users_df.empty and "Username" in users_df.columns:
        user_options = [
            "Select user",
            *users_df["Username"].dropna().astype(str).str.strip().tolist(),
        ]

    issued_by_options = user_options.copy()

    asset_options = []
    if not assets_df.empty and "Asset ID" in assets_df.columns:
        asset_options = [
            "Select asset",
            *assets_df["Asset ID"].dropna().astype(str).str.strip().tolist(),
        ]

    asset_id_col = None
    asset_assigned_col = None
    asset_status_col = None
    if not assets_df.empty:
        for col in assets_df.columns:
            col_norm = str(col).strip().lower()
            if col_norm in {
                "asset id",
                "asset id / barcode",
                "asset id/barcode",
                "asset id barcode",
                "assetid",
                "barcode",
            } and asset_id_col is None:
                asset_id_col = col
            elif col_norm in {"assigned to", "assigned_to", "assignedto"} and asset_assigned_col is None:
                asset_assigned_col = col
            elif col_norm in {"status", "asset status"} and asset_status_col is None:
                asset_status_col = col

    def update_asset_assignment(asset_value: str, assignee_value: str, status_value: str | None = None) -> None:
        nonlocal assets_df
        if not asset_value:
            return
        if assets_df.empty:
            return
        if asset_id_col is None:
            return
        try:
            match = assets_df[
                assets_df[asset_id_col].astype(str).str.strip().str.lower()
                == str(asset_value).strip().lower()
            ]
            if match.empty:
                return
            row_index = int(match.index[0])
            column_order = list(assets_df.columns)
            asset_series = match.iloc[0].copy()
            if asset_assigned_col:
                asset_series.loc[asset_assigned_col] = assignee_value
            if asset_status_col and status_value is not None:
                asset_series.loc[asset_status_col] = status_value
            asset_series = asset_series.reindex(column_order, fill_value="")

            row_data: list[str] = []
            for val in asset_series.tolist():
                if pd.isna(val):
                    row_data.append("")
                else:
                    if hasattr(val, "item"):
                        try:
                            val = val.item()
                        except Exception:
                            val = str(val)
                    row_data.append(val)

            if update_data(SHEETS["assets"], row_index, row_data):
                if asset_assigned_col:
                    assets_df.at[row_index, asset_assigned_col] = assignee_value
                if asset_status_col and status_value is not None:
                    assets_df.at[row_index, asset_status_col] = status_value
        except Exception as err:
            st.warning(f"Unable to update asset assignment: {err}")

    with tab1:
        st.markdown(style_block, unsafe_allow_html=True)

        if "assignment_success_message" in st.session_state:
            st.success(st.session_state["assignment_success_message"])
            del st.session_state["assignment_success_message"]

        if "assignment_form_key" not in st.session_state:
            st.session_state["assignment_form_key"] = 0

        form_key = st.session_state["assignment_form_key"]

        with st.form(f"assignment_form_{form_key}"):
            auto_generate = st.checkbox(
                "Auto-generate Assignment ID",
                value=True,
                key=f"assignment_auto_{form_key}",
            )
            if auto_generate:
                if "generated_assignment_id" not in st.session_state:
                    st.session_state["generated_assignment_id"] = generate_assignment_id()
                assignment_id = st.text_input(
                    "Assignment ID *",
                    value=st.session_state["generated_assignment_id"],
                    disabled=True,
                    key=f"assignment_id_{form_key}",
                )
            else:
                assignment_id = st.text_input(
                    "Assignment ID *",
                    key=f"assignment_manual_id_{form_key}",
                )
                if "generated_assignment_id" in st.session_state:
                    del st.session_state["generated_assignment_id"]

            if user_options:
                username = st.selectbox(
                    "Username *",
                    user_options,
                    key=f"assignment_user_{form_key}",
                )
            else:
                username = st.text_input(
                    "Username *",
                    key=f"assignment_user_text_{form_key}",
                )
                st.warning("No users found. Please add users first.")

            if asset_options:
                asset_id = st.selectbox(
                    "Asset ID *",
                    asset_options,
                    key=f"assignment_asset_{form_key}",
                )
            else:
                asset_id = st.text_input(
                    "Asset ID *",
                    key=f"assignment_asset_text_{form_key}",
                )
                if assets_df.empty:
                    st.warning("No assets found. Please add assets first.")

            assignment_date = st.date_input(
                "Assignment Date *",
                value=datetime.now().date(),
                key=f"assignment_date_{form_key}",
            )

            if issued_by_options:
                issued_by = st.selectbox(
                    "Issued By *",
                    issued_by_options,
                    key=f"assignment_issued_by_{form_key}",
                )
            else:
                issued_by = st.text_input(
                    "Issued By *",
                    key=f"assignment_issued_by_text_{form_key}",
                )

            expected_return_date = st.date_input(
                "Expected Return Date",
                value=assignment_date,
                key=f"assignment_expected_return_{form_key}",
            )
            return_date = st.date_input(
                "Return Date",
                value=assignment_date,
                key=f"assignment_return_date_{form_key}",
            )

            status = st.selectbox(
                "Status",
                ["Assigned", "Returned", "Under Repair"],
                key=f"assignment_status_{form_key}",
            )
            condition_issue = st.selectbox(
                "Condition on Issue",
                ["Working", "Damaged", "Used"],
                key=f"assignment_condition_{form_key}",
            )
            remarks = st.text_area(
                "Remarks",
                key=f"assignment_remarks_{form_key}",
            )

            submitted = st.form_submit_button(
                "Add Assignment",
                use_container_width=True,
                type="primary",
            )

            if submitted:
                if not assignment_id:
                    st.error("Please provide an Assignment ID")
                elif user_options and username == "Select user":
                    st.error("Please select a Username")
                elif not username:
                    st.error("Please provide a Username")
                elif asset_options and asset_id == "Select asset":
                    st.error("Please select an Asset")
                elif not asset_id:
                    st.error("Please provide an Asset ID")
                elif issued_by_options and issued_by == "Select user":
                    st.error("Please select Issued By")
                elif not issued_by:
                    st.error("Please provide Issued By")
                else:
                    data_map = {
                        "Assignment ID": assignment_id,
                        "Username": username,
                        "Asset ID": asset_id,
                        "Issued By": issued_by,
                        "Assignment Date": assignment_date.strftime("%Y-%m-%d"),
                        "Expected Return Date": expected_return_date.strftime("%Y-%m-%d") if expected_return_date else "",
                        "Return Date": return_date.strftime("%Y-%m-%d") if return_date else "",
                        "Status": status,
                        "Condition on Issue": condition_issue,
                        "Remarks": remarks,
                    }
                    column_order = (
                        list(assignments_df.columns)
                        if not assignments_df.empty
                        else assignment_headers
                    )
                    data = [data_map.get(col, "") for col in column_order]
                    with st.spinner("Saving assignment..."):
                        if append_data(SHEETS["assignments"], data):
                            if "generated_assignment_id" in st.session_state:
                                del st.session_state["generated_assignment_id"]
                            st.session_state["assignment_success_message"] = (
                                f"✅ Assignment '{assignment_id}' added successfully!"
                            )
                            update_asset_assignment(asset_id, username if status == "Assigned" else "", status)
                            st.session_state["refresh_asset_users"] = True
                            st.session_state["assignment_form_key"] += 1
                            if "assignment_search" in st.session_state:
                                del st.session_state["assignment_search"]
                            st.rerun()
                        else:
                            st.error("Failed to save assignment")

    with tab2:
        user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
        is_admin = str(user_role).lower() == "admin"

        if not assignments_df.empty:
            search_term = st.text_input(
                "🔍 Search Assignments",
                placeholder="Search by assignment ID, username, or asset...",
                key="assignment_search",
            )

            filtered_df = assignments_df.copy()
            if search_term:
                term = search_term.strip().lower()
                filtered_df = filtered_df[
                    filtered_df.apply(
                        lambda row: term in " ".join(row.astype(str).str.lower()),
                        axis=1,
                    )
                ]

            if filtered_df.empty:
                if search_term:
                    st.warning("No assignments match your search.")
                else:
                    st.info("No assignments found. Add one using the 'Add Assignment' tab.")
            else:
                field_headers = [
                    "**Asset ID**",
                    "**Username**",
                    "**Status**",
                    "**Condition**",
                    "**Assignment Date**",
                    "**View**",
                ]
                header_cols = (
                    st.columns([2, 2, 2, 2, 2, 1, 1, 1])
                    if is_admin
                    else st.columns([2, 2, 2, 2, 2, 1, 1])
                )
                for col_widget, header in zip(header_cols[: len(field_headers)], field_headers):
                    with col_widget:
                        st.write(header)
                with header_cols[len(field_headers)]:
                    st.write("**Edit**")
                if is_admin:
                    with header_cols[-1]:
                        st.write("**Delete**")
                st.divider()

                for idx, row in filtered_df.iterrows():
                    if (
                        "Assignment ID" in assignments_df.columns
                        and not assignments_df[
                            assignments_df["Assignment ID"].astype(str) == str(row.get("Assignment ID", ""))
                        ].empty
                    ):
                        original_idx = int(
                            assignments_df[
                                assignments_df["Assignment ID"].astype(str)
                                == str(row.get("Assignment ID", ""))
                            ].index[0]
                        )
                    else:
                        original_idx = int(idx) if isinstance(idx, int) else int(idx) if str(idx).isdigit() else 0

                    cols = (
                        st.columns([2, 2, 2, 2, 2, 1, 1, 1])
                        if is_admin
                        else st.columns([2, 2, 2, 2, 2, 1, 1])
                    )
                    display_values = [
                        row.get("Asset ID", "N/A"),
                        row.get("Username", "N/A"),
                        row.get("Status", ""),
                        row.get("Condition on Issue", ""),
                        row.get("Assignment Date", ""),
                    ]
                    for col_widget, value in zip(cols[: len(display_values)], display_values):
                        with col_widget:
                            st.write(value if value not in ("", None) else "N/A")

                    col_view = cols[len(display_values)]
                    edit_placeholder = cols[len(display_values) + 1]
                    with col_view:
                        if st.button("👁️", key=f"assignment_view_{row.get('Assignment ID', idx)}", use_container_width=True, help="View details"):
                            record = {
                                "Assignment ID": row.get("Assignment ID", ""),
                                "Username": row.get("Username", ""),
                                "Asset ID": row.get("Asset ID", ""),
                                "Issued By": row.get("Issued By", ""),
                                "Assignment Date": row.get("Assignment Date", ""),
                                "Expected Return Date": row.get("Expected Return Date", ""),
                                "Return Date": row.get("Return Date", ""),
                                "Status": row.get("Status", ""),
                                "Condition on Issue": row.get("Condition on Issue", ""),
                                "Remarks": row.get("Remarks", ""),
                            }
                            _open_view_modal(
                                "assignment",
                                f"Assignment Details: {row.get('Assignment ID', '')}",
                                record,
                                [
                                    "Assignment ID",
                                    "Username",
                                    "Asset ID",
                                    "Issued By",
                                    "Assignment Date",
                                    "Expected Return Date",
                                    "Return Date",
                                    "Status",
                                    "Condition on Issue",
                                    "Remarks",
                                ],
                            )
                    with edit_placeholder:
                        if st.button("✏️", key=f"assignment_edit_{row.get('Assignment ID', idx)}"):
                            st.session_state["edit_assignment_id"] = row.get("Assignment ID", "")
                            st.session_state["edit_assignment_idx"] = original_idx
                            st.rerun()

                    if is_admin:
                        col_delete = cols[-1]
                        with col_delete:
                            if st.button(
                                "🗑️",
                                key=f"assignment_delete_{row.get('Assignment ID', idx)}",
                            ):
                                if delete_data(SHEETS["assignments"], original_idx):
                                    st.session_state["assignment_success_message"] = (
                                        f"🗑️ Assignment '{row.get('Assignment ID', '')}' deleted."
                                    )
                                    status_after_delete = row.get("Status", "")
                                    if str(status_after_delete).strip().lower() == "assigned":
                                        status_after_delete = ""
                                    update_asset_assignment(row.get("Asset ID", ""), "", status_after_delete)
                                    st.session_state["refresh_asset_users"] = True
                                    st.rerun()
                                else:
                                    st.error("Failed to delete assignment")

                    st.divider()
                _render_view_modal("assignment")

        else:
            st.info("No assignments found. Add one using the 'Add Assignment' tab.")

        if (
            "edit_assignment_id" in st.session_state
            and st.session_state["edit_assignment_id"]
        ):
            edit_id = st.session_state["edit_assignment_id"]
            edit_idx = st.session_state.get("edit_assignment_idx", 0)
            edit_row = assignments_df[assignments_df.get("Assignment ID", pd.Series()).astype(str) == str(edit_id)]

            if not edit_row.empty:
                record = edit_row.iloc[0]
                st.subheader(f"Edit Assignment: {edit_id}")
                with st.form(f"edit_assignment_form_{edit_id}"):
                    if user_options:
                        try:
                            default_user_idx = user_options.index(record.get("Username", ""))
                        except ValueError:
                            default_user_idx = 0
                        username_new = st.selectbox(
                            "Username *",
                            user_options,
                            index=default_user_idx,
                        )
                    else:
                        username_new = st.text_input(
                            "Username *",
                            value=record.get("Username", ""),
                        )

                    if asset_options:
                        try:
                            default_asset_idx = asset_options.index(record.get("Asset ID", ""))
                        except ValueError:
                            default_asset_idx = 0
                        asset_id_new = st.selectbox(
                            "Asset ID *",
                            asset_options,
                            index=default_asset_idx,
                        )
                    else:
                        asset_id_new = st.text_input(
                            "Asset ID *",
                            value=record.get("Asset ID", ""),
                        )

                    assignment_date_new = st.date_input(
                        "Assignment Date *",
                        value=parse_date_value(record.get("Assignment Date")),
                    )
                    if issued_by_options:
                        try:
                            default_issued_idx = issued_by_options.index(record.get("Issued By", ""))
                        except ValueError:
                            default_issued_idx = 0
                        issued_by_new = st.selectbox(
                            "Issued By *",
                            issued_by_options,
                            index=default_issued_idx,
                        )
                    else:
                        issued_by_new = st.text_input(
                            "Issued By *",
                            value=record.get("Issued By", ""),
                        )

                    expected_return_new = st.date_input(
                        "Expected Return Date",
                        value=parse_date_value(record.get("Expected Return Date")),
                    )
                    return_date_new = st.date_input(
                        "Return Date",
                        value=parse_date_value(record.get("Return Date")) or parse_date_value(record.get("Assignment Date")),
                    )

                    status_new = st.selectbox(
                        "Status",
                        ["Assigned", "Returned", "Under Repair"],
                        index={
                            "assigned": 0,
                            "returned": 1,
                            "under repair": 2,
                        }.get(str(record.get("Status", "Assigned")).strip().lower(), 0),
                    )
                    condition_new = st.selectbox(
                        "Condition on Issue",
                        ["Working", "Damaged", "Used"],
                        index={
                            "working": 0,
                            "damaged": 1,
                            "used": 2,
                        }.get(str(record.get("Condition on Issue", "Working")).strip().lower(), 0),
                    )
                    remarks_new = st.text_area(
                        "Remarks",
                        value=record.get("Remarks", ""),
                    )

                    col_update, col_cancel = st.columns(2)
                    with col_update:
                        if st.form_submit_button("Update", use_container_width=True):
                            if user_options and username_new == "Select user":
                                st.error("Please select a Username")
                            elif not username_new:
                                st.error("Please provide a Username")
                            elif asset_options and asset_id_new == "Select asset":
                                st.error("Please select an Asset")
                            elif not asset_id_new:
                                st.error("Please provide an Asset ID")
                            elif issued_by_options and issued_by_new == "Select user":
                                st.error("Please select Issued By")
                            elif not issued_by_new:
                                st.error("Please provide Issued By")
                            else:
                                old_asset_id = record.get("Asset ID", "")
                                old_status = str(record.get("Status", "")).strip()
                                update_map = {
                                    "Assignment ID": edit_id,
                                    "Username": username_new,
                                    "Asset ID": asset_id_new,
                                    "Issued By": issued_by_new,
                                    "Assignment Date": assignment_date_new.strftime("%Y-%m-%d"),
                                    "Expected Return Date": expected_return_new.strftime("%Y-%m-%d") if expected_return_new else "",
                                    "Return Date": return_date_new.strftime("%Y-%m-%d") if return_date_new else "",
                                    "Status": status_new,
                                    "Condition on Issue": condition_new,
                                    "Remarks": remarks_new,
                                }
                                column_order = list(assignments_df.columns)
                                updated_row = [update_map.get(col, record.get(col, "")) for col in column_order]
                                if update_data(SHEETS["assignments"], int(edit_idx), updated_row):
                                    st.session_state["assignment_success_message"] = (
                                        f"✅ Assignment '{edit_id}' updated successfully!"
                                    )
                                    new_assignee = username_new if status_new == "Assigned" else ""
                                    update_asset_assignment(asset_id_new, new_assignee, status_new)
                                    if asset_id_new != old_asset_id or (old_status.lower() == "assigned" and status_new != "Assigned"):
                                        old_status_value = "" if old_status.lower() == "assigned" else old_status
                                        update_asset_assignment(old_asset_id, "", status_new if asset_id_new == old_asset_id else old_status_value)
                                    st.session_state["refresh_asset_users"] = True
                                    st.session_state.pop("edit_assignment_id", None)
                                    st.session_state.pop("edit_assignment_idx", None)
                                    st.rerun()
                                else:
                                    st.error("Failed to update assignment")
                    with col_cancel:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop("edit_assignment_id", None)
                            st.session_state.pop("edit_assignment_idx", None)
                            st.rerun()


def user_management_form():
    """User Management Form"""
    st.header("👥 User Management")

    # Only admins can manage users
    user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
    if str(user_role).lower() != "admin":
        st.warning("Only administrators can view or modify users.")
        return

    users_df = read_data(SHEETS["users"])

    tab1, tab2 = st.tabs(["Add User", "View/Edit Users"])

    with tab1:
        if "user_success_message" in st.session_state:
            st.success(st.session_state["user_success_message"])
            del st.session_state["user_success_message"]

        if "user_form_key" not in st.session_state:
            st.session_state["user_form_key"] = 0

        form_key = st.session_state["user_form_key"]

        with st.form(f"add_user_form_{form_key}"):
            username = st.text_input("Username *")
            password = st.text_input("Password *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")
            email = st.text_input("Email *")
            role = st.selectbox("Role *", ["admin", "user"], index=1)

            submitted = st.form_submit_button("Add User", use_container_width=True)

            if submitted:
                if not username or not password or not confirm_password or not email:
                    st.error("Please fill in all required fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif not users_df.empty and "Username" in users_df.columns and username in users_df["Username"].astype(str).values:
                    st.error("Username already exists")
                else:
                    hashed_password = hash_password(password)
                    success = append_data(SHEETS["users"], [username, hashed_password, email, role])
                    if success:
                        st.session_state["user_success_message"] = f"✅ User '{username}' added successfully!"
                        st.session_state["user_form_key"] += 1
                        if "user_search" in st.session_state:
                            del st.session_state["user_search"]
                        st.rerun()
                    else:
                        st.error("Failed to add user")

    with tab2:
        if "user_success_message" in st.session_state:
            st.success(st.session_state["user_success_message"])
            del st.session_state["user_success_message"]

        if users_df.empty:
            st.info("No users found. Add a new user using the 'Add User' tab.")
            return

        st.subheader("Existing Users")

        search_term = st.text_input(
            "🔍 Search Users",
            placeholder="Search by Username, Email, or Role...",
            key="user_search",
        )

        if search_term:
            mask = (
                users_df["Username"].astype(str).str.contains(search_term, case=False, na=False)
                | users_df["Email"].astype(str).str.contains(search_term, case=False, na=False)
                | users_df["Role"].astype(str).str.contains(search_term, case=False, na=False)
            )
            filtered_df = users_df[mask]
            if filtered_df.empty:
                st.info(f"No users found matching '{search_term}'")
                return
        else:
            filtered_df = users_df

        st.caption(f"Showing {len(filtered_df)} of {len(users_df)} user(s)")

        header_username, header_email, header_role, header_edit, header_delete = st.columns([2, 3, 2, 1, 1])
        with header_username:
            st.write("**Username**")
        with header_email:
            st.write("**Email**")
        with header_role:
            st.write("**Role**")
        with header_edit:
            st.write("**Edit**")
        with header_delete:
            st.write("**Delete**")

        st.divider()

        for idx, row in filtered_df.iterrows():
            user_name = row.get("Username")
            matching_rows = users_df[users_df["Username"].astype(str) == str(user_name)]
            original_idx = int(matching_rows.index[0]) if not matching_rows.empty else int(idx)

            col_username, col_email, col_role, col_edit, col_delete = st.columns([2, 3, 2, 1, 1])
            with col_username:
                st.write(user_name or "-")
            with col_email:
                st.write(row.get("Email", "-"))
            with col_role:
                st.write(row.get("Role", "-"))
            with col_edit:
                if st.button("✏️", key=f"user_edit_{user_name}", use_container_width=True, help="Edit this user"):
                    st.session_state["edit_user_username"] = user_name
                    st.session_state["edit_user_idx"] = original_idx
                    st.rerun()
            with col_delete:
                if st.button("🗑️", key=f"user_delete_{user_name}", use_container_width=True, help="Delete this user"):
                    if delete_data(SHEETS["users"], original_idx):
                        st.session_state["user_success_message"] = f"🗑️ User '{user_name}' deleted."
                        if "user_search" in st.session_state:
                            del st.session_state["user_search"]
                        st.rerun()
                    else:
                        st.error("Failed to delete user")
            st.divider()

        if "edit_user_username" in st.session_state and st.session_state["edit_user_username"]:
            edit_username = st.session_state["edit_user_username"]
            edit_idx = st.session_state.get("edit_user_idx", 0)

            user_rows = users_df[users_df["Username"] == edit_username]
            if not user_rows.empty:
                user_row = user_rows.iloc[0]

                st.subheader(f"Edit User: {edit_username}")
                with st.form("edit_user_form"):
                    st.text_input("Username", value=edit_username, disabled=True)
                    new_email = st.text_input("Email", value=user_row.get("Email", ""))
                    new_role = st.selectbox(
                        "Role",
                        ["admin", "user"],
                        index=0 if str(user_row.get("Role", "user")).lower() == "admin" else 1,
                    )
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Update User", use_container_width=True):
                            if new_password and new_password != confirm_password:
                                st.error("Passwords do not match")
                            else:
                                hashed = user_row.get("Password", "")
                                if new_password:
                                    hashed = hash_password(new_password)
                                updated_data = [
                                    edit_username,
                                    hashed,
                                    new_email,
                                    new_role,
                                ]
                                if update_data(SHEETS["users"], edit_idx, updated_data):
                                    st.session_state["user_success_message"] = f"✅ User '{edit_username}' updated successfully!"
                                    st.session_state.pop("edit_user_username", None)
                                    st.session_state.pop("edit_user_idx", None)
                                    if "user_search" in st.session_state:
                                        del st.session_state["user_search"]
                                    st.rerun()
                                else:
                                    st.error("Failed to update user")
                    with col_cancel:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.pop("edit_user_username", None)
                            st.session_state.pop("edit_user_idx", None)
                            st.rerun()

