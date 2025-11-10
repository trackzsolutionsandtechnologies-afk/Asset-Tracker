"""
Forms module for Asset Tracker
"""
import base64
from copy import deepcopy
from io import BytesIO
import time
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional
from google_sheets import read_data, append_data, update_data, delete_data, find_row, ensure_sheet_headers, get_worksheet
def _ensure_headers_once(sheet_key: str, headers: list[str]) -> None:
    """
    Ensure Google Sheet headers only once per session to reduce API calls.

    Args:
        sheet_key: Key used in SHEETS mapping.
        headers: Expected header list.
    """
    state_key = f"headers_ensured_{sheet_key}"
    if st.session_state.get(state_key):
        return
    ensure_sheet_headers(SHEETS[sheet_key], headers)
    st.session_state[state_key] = True

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

ASSET_CONDITION_OPTIONS = ["Excellent", "Good", "Fair", "Poor", "Damaged"]
ASSET_STATUS_OPTIONS = [
    "Active",
    "Inactive",
    "Maintenance",
    "Retired",
    "Assigned",
    "Returned",
    "Under Repair",
]

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

    expected_headers = ["Location ID", "Location Name"]
    ensure_sheet_headers(SHEETS["locations"], expected_headers)

    worksheet = get_worksheet(SHEETS["locations"])
    if worksheet is not None:
        try:
            header_row = worksheet.row_values(1)
            normalized_header = [str(h).strip().lower() for h in header_row]
            if len(normalized_header) > len(expected_headers) or "department" in normalized_header:
                worksheet.update("1:1", [expected_headers])
                read_data.clear()
        except Exception:
            pass

    df = read_data(SHEETS["locations"])
    if not df.empty:
        column_map = {}
        for col in df.columns:
            normalized = str(col).strip().lower()
            if normalized == "location id":
                column_map[col] = "Location ID"
            elif normalized in {"location name", "location"}:
                column_map[col] = "Location Name"
        if column_map:
            df = df.rename(columns=column_map)
        df = df.reindex(columns=expected_headers)
    
    tab1, tab2 = st.tabs(["Add New Location", "View/Edit Locations"])
    
    with tab1:

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
            
            submitted = st.form_submit_button("Add Location", use_container_width=True, type="primary")
            
            if submitted:
                if not location_id or not location_name:
                    st.error("Please fill in all required fields")
                elif not df.empty and "Location ID" in df.columns and location_id in df["Location ID"].values:
                    st.error("Location ID already exists")
                else:
                    with st.spinner("Adding location..."):
                        column_order = list(df.columns) if not df.empty else expected_headers
                        if not column_order:
                            column_order = expected_headers
                        data_map = {
                            "Location ID": location_id,
                            "Location Name": location_name,
                        }
                        data_row = [data_map.get(col, "") for col in column_order]
                        if append_data(SHEETS["locations"], data_row):
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
            search_term = st.text_input("🔍 Search Locations", placeholder="Search by Location ID or Name...", key="location_search")
            
            # Filter data based on search
            if search_term and not df.empty:
                search_mask = pd.Series([False] * len(df), index=df.index)
                if "Location ID" in df.columns:
                    search_mask = search_mask | df["Location ID"].astype(str).str.contains(search_term, case=False, na=False)
                if "Location Name" in df.columns:
                    search_mask = search_mask | df["Location Name"].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = df[search_mask] if not df.empty else pd.DataFrame()
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
                    header_cols = st.columns([4, 4, 1, 1, 1])
                else:
                    header_cols = st.columns([4, 4, 1, 1])

                header_labels = ["**Location ID**", "**Location Name**", "**View**", "**Edit**"]
                if is_admin:
                    header_labels.append("**Delete**")

                for col_widget, label in zip(header_cols, header_labels):
                    with col_widget:
                        st.markdown(f"<div style='text-align: left;'>{label}</div>", unsafe_allow_html=True)
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
                        col1, col2, col_view, col_edit, col_delete = st.columns([4, 4, 1, 1, 1])
                    else:
                        col1, col2, col_view, col_edit = st.columns([4, 4, 1, 1])

                    with col1:
                        st.write(row.get("Location ID", "N/A"))
                    with col2:
                        st.write(row.get("Location Name", "N/A"))
                    with col_view:
                        if st.button("👁️", key=f"location_view_{unique_suffix}", use_container_width=True, help="View details"):
                            record = {
                                "Location ID": location_id_value,
                                "Location Name": row.get("Location Name", ""),
                            }
                            _open_view_modal(
                                "location",
                                f"Location Details: {row.get('Location Name', '')}",
                                record,
                                ["Location ID", "Location Name"],
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
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Update Location", use_container_width=True):
                                    with st.spinner("Updating location..."):
                                        column_order = list(df.columns) if not df.empty else expected_headers
                                        if not column_order:
                                            column_order = expected_headers
                                        data_map = {
                                            "Location ID": new_location_id,
                                            "Location Name": new_location_name,
                                        }
                                        row_data = [data_map.get(col, "") for col in column_order]
                                        if update_data(SHEETS["locations"], edit_idx, row_data):
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
    
    ensure_sheet_headers(SHEETS["categories"], ["Category ID", "Category Name"])
    ensure_sheet_headers(SHEETS["subcategories"], ["SubCategory ID", "Category ID", "SubCategory Name", "Category Name"])
    
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add Category", "Add Sub Category", "View/Edit Categories", "View/Edit Sub Categories"])
    
    with tab1:
        
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
                            # Save: SubCategory ID, Category ID, SubCategory Name, Category Name
                            if append_data(SHEETS["subcategories"], [subcategory_id, category_id, subcategory_name, category_name]):
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
                                        # Update: SubCategory ID, Category ID, SubCategory Name, Category Name
                                        if update_data(SHEETS["subcategories"], edit_idx, [new_subcategory_id, new_category_id, new_subcategory_name, new_category_name]):
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

    condition_options = ASSET_CONDITION_OPTIONS
    status_options = ASSET_STATUS_OPTIONS

    tab1, tab2, tab3 = st.tabs(["Add New Asset", "View/Edit Assets", "Reports"])
    
    with tab1:
        
        if "asset_form_version" not in st.session_state:
            st.session_state["asset_form_version"] = 0
        form_version = st.session_state["asset_form_version"]

        def _key(name: str) -> str:
            return f"{name}_{form_version}"

        asset_form_keys = {
            "auto_generate": _key("asset_auto_generate"),
            "asset_id": _key("asset_id_input"),
            "asset_name": _key("asset_name_input"),
            "category_select": _key("asset_category_select"),
            "subcategory_select": _key("asset_subcategory_select"),
            "model_serial": _key("asset_model_serial"),
            "purchase_date": _key("asset_purchase_date"),
            "purchase_cost": _key("asset_purchase_cost"),
            "warranty": _key("asset_warranty"),
            "supplier": _key("asset_supplier"),
            "location": _key("asset_location"),
            "assigned_to": _key("asset_assigned_to"),
            "condition": _key("asset_condition"),
            "status": _key("asset_status"),
            "remarks": _key("asset_remarks"),
            "attachment": _key("asset_attachment"),
        }

        st.session_state.setdefault(asset_form_keys["auto_generate"], True)
        st.session_state.setdefault(asset_form_keys["purchase_date"], datetime.now().date())
        st.session_state.setdefault(asset_form_keys["purchase_cost"], 0.0)

        category_placeholder = "Select category"
        subcategory_placeholder = "Select sub category"
        if not categories_df.empty and category_name_col:
            category_options = unique_clean(categories_df[category_name_col])
        else:
            category_options = []

        if not subcategories_df.empty and subcat_name_col:
            subcategory_options = unique_clean(subcategories_df[subcat_name_col])
        else:
            subcategory_options = []

        st.markdown(
            """
            <style>
            .asset-form-card {
                background-color: #ffffff;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.04);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            st.markdown('<div class="asset-form-card">', unsafe_allow_html=True)

            with st.form(f"asset_form_{form_version}"):
                top_cols = st.columns(3, gap="medium")
                with top_cols[0]:
                    auto_generate = st.checkbox(
                        "Auto-generate Asset ID",
                        key=asset_form_keys["auto_generate"],
                    )
                    asset_id_key = asset_form_keys["asset_id"]
                    if auto_generate:
                        if "generated_asset_id" not in st.session_state:
                            st.session_state["generated_asset_id"] = generate_asset_id()
                        st.session_state[asset_id_key] = st.session_state["generated_asset_id"]
                    else:
                        if st.session_state.get(asset_id_key) == st.session_state.get("generated_asset_id"):
                            st.session_state[asset_id_key] = ""
                        if "generated_asset_id" in st.session_state:
                            del st.session_state["generated_asset_id"]
                    asset_id_label = "Asset ID / Barcode" if auto_generate else "Asset ID / Barcode *"
                    asset_id = st.text_input(
                        asset_id_label,
                        key=asset_id_key,
                        disabled=auto_generate,
                    )
                with top_cols[1]:
                    asset_name = st.text_input("Asset Name *", key=asset_form_keys["asset_name"])
                with top_cols[2]:
                    if category_options:
                        category = st.selectbox(
                            "Category *",
                            [category_placeholder] + category_options,
                            key=asset_form_keys["category_select"],
                        )
                    else:
                        category = st.selectbox(
                            "Category *",
                            ["No categories available"],
                            disabled=True,
                            key=asset_form_keys["category_select"],
                        )
                        category = ""

                second_cols = st.columns(3, gap="medium")
                with second_cols[0]:
                    if subcategory_options:
                        subcategory = st.selectbox(
                            "Sub Category *",
                            [subcategory_placeholder] + subcategory_options,
                            key=asset_form_keys["subcategory_select"],
                        )
                    else:
                        subcategory = st.selectbox(
                            "Sub Category *",
                            ["No sub categories available"],
                            disabled=True,
                            key=asset_form_keys["subcategory_select"],
                        )
                        subcategory = ""
                with second_cols[1]:
                    model_serial = st.text_input("Model / Serial No", key=asset_form_keys["model_serial"])
                with second_cols[2]:
                    purchase_date = st.date_input(
                        "Purchase Date",
                        value=st.session_state.get(asset_form_keys["purchase_date"], datetime.now().date()),
                        key=asset_form_keys["purchase_date"],
                    )

                third_cols = st.columns(3, gap="medium")
                with third_cols[0]:
                    purchase_cost = st.number_input(
                        "Purchase Cost",
                        min_value=0.0,
                        value=st.session_state.get(asset_form_keys["purchase_cost"], 0.0),
                        step=0.01,
                        key=asset_form_keys["purchase_cost"],
                    )
                with third_cols[1]:
                    warranty = st.selectbox("Warranty", ["No", "Yes"], key=asset_form_keys["warranty"])
                with third_cols[2]:
                    if not suppliers_df.empty:
                        supplier_options = suppliers_df["Supplier Name"].tolist()
                        supplier = st.selectbox("Supplier", ["None"] + supplier_options, key=asset_form_keys["supplier"])
                    else:
                        supplier = st.text_input("Supplier", key=asset_form_keys["supplier"])

                refresh_key = st.session_state.pop("refresh_asset_users", False)
                if refresh_key:
                    users_df = read_data(SHEETS["users"])

                fourth_cols = st.columns(3, gap="medium")
                with fourth_cols[0]:
                    if not locations_df.empty:
                        location_options = locations_df["Location Name"].tolist()
                        location = st.selectbox("Location", ["None"] + location_options, key=asset_form_keys["location"])
                    else:
                        location = st.text_input("Location", key=asset_form_keys["location"])
                with fourth_cols[1]:
                    if not users_df.empty and user_username_col and user_username_col in users_df.columns:
                        user_options = ["None"] + users_df[user_username_col].dropna().astype(str).tolist()
                        assigned_to = st.selectbox("Assigned To", user_options, key=asset_form_keys["assigned_to"])
                    else:
                        assigned_to = st.text_input("Assigned To", key=asset_form_keys["assigned_to"])
                with fourth_cols[2]:
                    condition = st.selectbox(
                        "Condition",
                        ["Excellent", "Good", "Fair", "Poor", "Damaged"],
                        key=asset_form_keys["condition"],
                    )

                fifth_cols = st.columns(3, gap="medium")
                with fifth_cols[0]:
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
                        key=asset_form_keys["status"],
                    )
                with fifth_cols[1]:
                    st.empty()
                with fifth_cols[2]:
                    st.empty()

                remarks = st.text_area("Remarks", key=asset_form_keys["remarks"])
                attachment_file = st.file_uploader(
                    "Attachment (Image or File)",
                    type=None,
                    help="Upload related documents or images.",
                    key=asset_form_keys["attachment"],
                )

                attachment = ""
                attachment_too_large = False
                if attachment_file is not None:
                    file_content = attachment_file.getvalue()
                    encoded = base64.b64encode(file_content).decode("utf-8")
                    if len(encoded) > MAX_ATTACHMENT_CHARS:
                        st.warning(
                            "Attachment is too large to store. Please upload a smaller file (approx. < 35 KB).",
                            icon="⚠️",
                        )
                        attachment = ""
                        attachment_too_large = True
                    else:
                        attachment = f"data:{attachment_file.type};name={attachment_file.name};base64,{encoded}"

                submitted = st.form_submit_button("Add Asset", use_container_width=True)

                if submitted:
                    if attachment_file is not None and attachment == "" and attachment_too_large:
                        st.error(
                            "Attachment was not uploaded because it exceeds the allowed size. Please upload a smaller file."
                        )
                    elif not asset_id or not asset_name:
                        st.error("Please fill in Asset ID and Asset Name")
                    elif not assets_df.empty and asset_id in assets_df["Asset ID"].values:
                        st.error("Asset ID already exists")
                    elif category in ("", category_placeholder):
                        st.error("Please select a category")
                    elif subcategory in ("", subcategory_placeholder):
                        st.error("Please select a sub category")
                    else:
                        data = [
                            asset_id,
                            asset_name,
                            category if category not in ("", category_placeholder) else "",
                            subcategory if subcategory not in ("", subcategory_placeholder) else "",
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
                            if "generated_asset_id" in st.session_state:
                                del st.session_state["generated_asset_id"]

                            st.session_state["asset_success_message"] = "Asset added successfully!"
                            reset_keys = list(asset_form_keys.values())
                            for state_key in reset_keys:
                                st.session_state.pop(state_key, None)
                            st.session_state["asset_form_version"] = form_version + 1
                            st.rerun()
                        else:
                            st.error("Failed to add asset")

            st.markdown("</div>", unsafe_allow_html=True)
    
    with tab2:
        if "asset_success_message" in st.session_state:
            st.success(st.session_state["asset_success_message"])
            del st.session_state["asset_success_message"]

        if not assets_df.empty:
            st.subheader("All Assets")

            filter_cols = st.columns([2, 1, 1, 1])
            with filter_cols[0]:
                search_term = st.text_input(
                    "🔍 Search Assets",
                    placeholder="Search by Asset ID, Name, or Location...",
                    key="asset_search",
                )
            with filter_cols[1]:
                status_filter_options = ["All Status"] + sorted(
                    {str(val).strip() for val in assets_df.get("Status", pd.Series()).dropna()}
                )
                selected_status = st.selectbox("Status Filter", status_filter_options, key="asset_status_filter")
            with filter_cols[2]:
                location_filter_options = ["All Locations"] + sorted(
                    {str(val).strip() for val in assets_df.get("Location", pd.Series()).dropna()}
                )
                selected_location = st.selectbox("Location Filter", location_filter_options, key="asset_location_filter")
            with filter_cols[3]:
                assigned_filter_options = ["All Assignees"] + sorted(
                    {str(val).strip() for val in assets_df.get("Assigned To", pd.Series()).dropna()}
                )
                selected_assigned = st.selectbox("Assigned To Filter", assigned_filter_options, key="asset_assigned_filter")

            filtered_df = assets_df.copy()
            if search_term:
                mask = (
                    filtered_df["Asset ID"].astype(str).str.contains(search_term, case=False, na=False)
                    | filtered_df["Asset Name"].astype(str).str.contains(search_term, case=False, na=False)
                    | filtered_df.get("Location", pd.Series(dtype=str)).astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]

            if selected_status != "All Status":
                filtered_df = filtered_df[
                    filtered_df["Status"].astype(str).str.strip().str.lower()
                    == selected_status.strip().lower()
                ]

            if selected_location != "All Locations":
                filtered_df = filtered_df[
                    filtered_df["Location"].astype(str).str.strip().str.lower()
                    == selected_location.strip().lower()
                ]

            if selected_assigned != "All Assignees":
                filtered_df = filtered_df[
                    filtered_df["Assigned To"].astype(str).str.strip().str.lower()
                    == selected_assigned.strip().lower()
                ]

            if filtered_df.empty:
                st.info("No assets match the current filters.")
            else:
                st.caption(f"Showing {len(filtered_df)} of {len(assets_df)} asset(s)")

                desired_columns = [
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
                    "Model/Serial No",
                    "Purchase Date",
                    "Purchase Cost",
                    "Warranty",
                    "Remarks",
                ]
                available_columns = [col for col in desired_columns if col in filtered_df.columns]

                if not available_columns:
                    st.warning("No displayable columns found for the current asset data.")
                    return

                asset_display_df = filtered_df[available_columns].copy()

                # ensure we only keep one of model serial columns if both exist
                if "Model / Serial No" in asset_display_df.columns and "Model/Serial No" in asset_display_df.columns:
                    asset_display_df["Model / Serial No"] = asset_display_df["Model / Serial No"].where(
                        asset_display_df["Model / Serial No"].astype(str).str.strip() != "",
                        asset_display_df["Model/Serial No"],
                    )
                    asset_display_df = asset_display_df.drop(columns=["Model/Serial No"])
                    available_columns = [col for col in available_columns if col != "Model/Serial No"]

                st.markdown(
                    """
                    <style>
                    .asset-editor-container [data-testid="stDataEditor"] thead th,
                    .asset-editor-container [data-testid="stDataEditor"] div[role="columnheader"] {
                        background-color: #BF092F !important;
                        color: #1A202C !important;
                        font-weight: 600 !important;
                    }
                    .asset-editor-container [data-testid="stDataEditor"] div[role="columnheader"] * {
                        color: #1A202C !important;
                    }
                    .asset-editor-container [data-testid="stDataEditor"] tbody td {
                        border-right: 1px solid #f0f0f0 !important;
                    }
                    .asset-editor-container [data-testid="stDataEditor"] tbody td:last-child {
                        border-right: none !important;
                    }
                    .asset-editor-container [data-testid="stDataEditor"] div[data-testid="stDataEditorPrimaryToolbar"] button[title*="Add row"] {
                        display: none !important;
                    }
                    .asset-editor-container div[data-testid="stButton"] button:disabled,
                    .asset-editor-container div[data-testid="stButton"] button:disabled:hover,
                    .asset-editor-container div[data-testid="stButton"] button:disabled:focus {
                        background-color: #cbd5e0 !important;
                        color: #4a5568 !important;
                        border-color: #cbd5e0 !important;
                        cursor: not-allowed !important;
                        opacity: 1 !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                with st.container():
                    st.markdown('<div class="asset-editor-container">', unsafe_allow_html=True)

                    column_config_map: dict[str, st.column_config.BaseColumn] = {}
                    if "Asset ID" in available_columns:
                        column_config_map["Asset ID"] = st.column_config.TextColumn("Asset ID", disabled=True)
                    if "Asset Name" in available_columns:
                        column_config_map["Asset Name"] = st.column_config.TextColumn("Asset Name")
                    if "Category" in available_columns:
                        column_config_map["Category"] = st.column_config.TextColumn("Category")
                    if "Sub Category" in available_columns:
                        column_config_map["Sub Category"] = st.column_config.TextColumn("Sub Category")
                    if "Location" in available_columns:
                        column_config_map["Location"] = st.column_config.TextColumn("Location")
                    if "Assigned To" in available_columns:
                        column_config_map["Assigned To"] = st.column_config.TextColumn("Assigned To")
                    if "Status" in available_columns:
                        column_config_map["Status"] = st.column_config.TextColumn("Status")
                    if "Condition" in available_columns:
                        column_config_map["Condition"] = st.column_config.TextColumn("Condition")
                    if "Supplier" in available_columns:
                        column_config_map["Supplier"] = st.column_config.TextColumn("Supplier")
                    if "Model / Serial No" in available_columns:
                        column_config_map["Model / Serial No"] = st.column_config.TextColumn("Model / Serial No")
                    if "Purchase Date" in available_columns:
                        column_config_map["Purchase Date"] = st.column_config.TextColumn("Purchase Date")
                    if "Purchase Cost" in available_columns:
                        column_config_map["Purchase Cost"] = st.column_config.TextColumn("Purchase Cost")
                    if "Warranty" in available_columns:
                        column_config_map["Warranty"] = st.column_config.TextColumn("Warranty")
                    if "Remarks" in available_columns:
                        column_config_map["Remarks"] = st.column_config.TextColumn("Remarks")

                    editor_response = st.data_editor(
                        asset_display_df,
                        hide_index=True,
                        use_container_width=True,
                        disabled=False,
                        column_config=column_config_map,
                        num_rows="dynamic",
                        key="assets_table_view",
                    )

                    st.markdown("<hr style='margin: 0.75rem 0; border: 0; border-top: 1px solid #d0d0d0;' />", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                editor_state = st.session_state.get("assets_table_view", {})
                edited_rows = deepcopy(editor_state.get("edited_rows", {}))
                edited_cells = deepcopy(editor_state.get("edited_cells", {}))
                deleted_rows = list(editor_state.get("deleted_rows", []))
                added_rows = list(editor_state.get("added_rows", []))

                st.session_state.setdefault("assets_save_success", False)
                st.session_state.setdefault("assets_pending_changes", False)
                st.session_state.setdefault("assets_last_save_ts", 0.0)

                has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
                if has_changes:
                    st.session_state["assets_pending_changes"] = True
                    st.session_state["assets_save_success"] = False
                else:
                    st.session_state["assets_pending_changes"] = False

                cooldown_seconds = 10
                current_ts = time.time()
                last_save_ts = float(st.session_state.get("assets_last_save_ts", 0.0) or 0.0)
                cooldown_remaining = max(0.0, cooldown_seconds - (current_ts - last_save_ts))

                if st.session_state.get("assets_pending_changes", False) and not st.session_state.get("assets_save_success", False):
                    st.info("You have unsaved asset changes. Click 'Save Changes' to apply them.", icon="✏️")
                if cooldown_remaining > 0:
                    st.warning(
                        f"Please wait {cooldown_remaining:.0f} second(s) before saving again to avoid hitting Google Sheets limits.",
                        icon="⏳",
                    )

                action_cols = st.columns([1, 1], gap="small")
                with action_cols[0]:
                    save_clicked = st.button(
                        "Save Changes",
                        type="primary",
                        use_container_width=True,
                        disabled=(not st.session_state.get("assets_pending_changes", False)) or (cooldown_remaining > 0),
                        key="assets_save_changes",
                    )
                with action_cols[1]:
                    discard_clicked = st.button(
                        "Discard Changes",
                        use_container_width=True,
                        disabled=not st.session_state.get("assets_pending_changes", False),
                        key="assets_discard_changes",
                    )

                if discard_clicked and st.session_state.get("assets_pending_changes", False):
                    st.session_state.pop("assets_table_view", None)
                    st.session_state["assets_pending_changes"] = False
                    st.session_state["assets_save_success"] = False
                    st.rerun()

                # existing modal/edit handling below remains

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

                                category_placeholder = "Select category"
                                if not categories_df.empty and category_name_col:
                                    edit_category_options = unique_clean(categories_df[category_name_col])
                                else:
                                    edit_category_options = []

                                current_category_value = row.get("Category", row.get("Category Name", ""))
                                if current_category_value and current_category_value not in edit_category_options:
                                    edit_category_options.append(current_category_value)
                                edit_category_options = sorted(dict.fromkeys(edit_category_options))

                                if edit_category_options:
                                    category_choices = [category_placeholder] + edit_category_options
                                    try:
                                        default_cat_index = (
                                            category_choices.index(current_category_value)
                                            if current_category_value in category_choices
                                            else 0
                                        )
                                    except ValueError:
                                        default_cat_index = 0
                                    selected_category = st.selectbox(
                                        "Category *",
                                        category_choices,
                                        index=default_cat_index,
                                        key=f"asset_edit_category_{edit_id}",
                                    )
                                else:
                                    selected_category = st.selectbox(
                                        "Category *",
                                        ["No categories available"],
                                        disabled=True,
                                        key=f"asset_edit_category_{edit_id}",
                                    )
                                    selected_category = ""

                                subcategory_placeholder = "Select sub category"
                                edit_subcategory_options = []
                                if not subcategories_df.empty and subcat_name_col:
                                    edit_subcategory_options = unique_clean(subcategories_df[subcat_name_col])

                                current_subcategory_value = row.get(
                                    "Sub Category",
                                    row.get("SubCategory Name", row.get("Sub Category Name", "")),
                                )
                                if current_subcategory_value and current_subcategory_value not in edit_subcategory_options:
                                    edit_subcategory_options.append(current_subcategory_value)
                                edit_subcategory_options = sorted(dict.fromkeys(edit_subcategory_options))

                                if edit_subcategory_options:
                                    subcategory_choices = [subcategory_placeholder] + edit_subcategory_options
                                    try:
                                        default_subcat_index = (
                                            subcategory_choices.index(current_subcategory_value)
                                            if current_subcategory_value in subcategory_choices
                                            else 0
                                        )
                                    except ValueError:
                                        default_subcat_index = 0
                                    selected_subcategory = st.selectbox(
                                        "Sub Category *",
                                        subcategory_choices,
                                        index=default_subcat_index,
                                        key=f"asset_edit_subcategory_{edit_id}",
                                    )
                                else:
                                    selected_subcategory = st.selectbox(
                                        "Sub Category *",
                                        ["No sub categories available"],
                                        disabled=True,
                                        key=f"asset_edit_subcategory_{edit_id}",
                                    )
                                    selected_subcategory = ""

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
                                        selected_category if selected_category not in ("", category_placeholder) else row.get("Category", ""),
                                        selected_subcategory if selected_subcategory not in ("", subcategory_placeholder) else row.get("Sub Category", ""),
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
        "Maintenance Type",
        "Maintenance Date",
        "Description",
        "Cost",
        "Supplier",
        "Next Due Date",
        "Status",
    ]
    _ensure_headers_once("maintenance", maintenance_headers)

    def _get_sheet_cached(sheet_key: str) -> pd.DataFrame:
        cache_key = f"cached_sheet_{sheet_key}"
        if cache_key not in st.session_state:
            st.session_state[cache_key] = read_data(SHEETS[sheet_key])
        return st.session_state[cache_key]

    maintenance_df = _get_sheet_cached("maintenance")
    assets_df = _get_sheet_cached("assets")
    suppliers_df = _get_sheet_cached("suppliers")
    asset_status_col = None
    asset_name_col = None
    asset_option_labels = ["Select asset"]
    asset_label_to_id: dict[str, str] = {}
    asset_id_to_label: dict[str, str] = {}
    asset_id_to_name: dict[str, str] = {}

    if not assets_df.empty:
        assets_df = assets_df.copy()
        for col in assets_df.columns:
            col_norm = str(col).strip().lower()
            if col_norm == "status":
                asset_status_col = col
            if col_norm in {"asset name", "name"} and asset_name_col is None:
                asset_name_col = col

        if "Asset ID" in assets_df.columns:
            for _, row in assets_df.iterrows():
                asset_id_value = str(row.get("Asset ID", "")).strip()
                if not asset_id_value:
                    continue
                asset_name_value = (
                    str(row.get(asset_name_col, "")).strip() if asset_name_col else ""
                )
                label = asset_id_value if not asset_name_value else f"{asset_id_value} - {asset_name_value}"
                asset_option_labels.append(label)
                asset_label_to_id[label] = asset_id_value
                asset_id_to_label[asset_id_value.lower()] = label
                asset_id_to_name[asset_id_value.lower()] = asset_name_value

    tab1, tab2, tab3 = st.tabs(["Add Maintenance Record", "View/Edit Maintenance", "Cumulative Cost"])

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

    def _update_asset_status_for_maintenance(
        assets_df_ref: pd.DataFrame,
        status_column: str | None,
        asset_id_value: str,
        new_status_value: str,
    ) -> None:
        if (
            status_column is None
            or assets_df_ref.empty
            or "Asset ID" not in assets_df_ref.columns
        ):
            return
        try:
            match_rows = assets_df_ref[
                assets_df_ref["Asset ID"].astype(str).str.strip().str.lower()
                == str(asset_id_value).strip().lower()
            ]
            if match_rows.empty:
                return
            row_index = int(match_rows.index[0])
            updated_row = match_rows.iloc[0].copy()
            updated_row.loc[status_column] = new_status_value
            column_order = list(assets_df_ref.columns)
            row_data = []
            for col in column_order:
                val = updated_row.get(col, "")
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
                assets_df_ref.at[row_index, status_column] = new_status_value
        except Exception as err:
            st.warning(f"Unable to update asset status: {err}")

    with tab1:

        if "maintenance_success_message" in st.session_state:
            st.success(st.session_state["maintenance_success_message"])
            del st.session_state["maintenance_success_message"]

        if "maintenance_form_key" not in st.session_state:
            st.session_state["maintenance_form_key"] = 0

        form_key = st.session_state["maintenance_form_key"]

        supplier_options: list[str] = []
        if not suppliers_df.empty and "Supplier Name" in suppliers_df.columns:
            supplier_options = ["Select supplier"] + (
                suppliers_df["Supplier Name"].dropna().astype(str).str.strip().tolist()
            )

        form_css = f"""
        <style>
        div[data-testid="stForm"][aria-label="maintenance_form_{form_key}"] {{
            background-color: #ffffff !important;
            padding: 1.5rem !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        }}
        </style>
        """
        st.markdown(form_css, unsafe_allow_html=True)

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

            asset_col, type_col, date_col = st.columns(3, gap="medium")
            if len(asset_option_labels) > 1:
                with asset_col:
                    asset_label_selected = st.selectbox(
                        "Asset *",
                        asset_option_labels,
                        key=f"maintenance_asset_{form_key}",
                    )
                    asset_id = asset_label_to_id.get(asset_label_selected, "")
            else:
                asset_label_selected = None
                with asset_col:
                    asset_id = st.text_input(
                        "Asset ID *",
                        key=f"maintenance_asset_text_{form_key}",
                    )
                    st.warning("No assets found. Please add assets first.")

            with type_col:
                maintenance_type = st.selectbox(
                    "Maintenance Type *",
                    ["Preventive", "Breakdown", "Calibration"],
                    key=f"maintenance_type_{form_key}",
                )

            with date_col:
                service_date = st.date_input(
                    "Maintenance Date *",
                    value=datetime.now().date(),
                    key=f"maintenance_service_{form_key}",
                )

            description = st.text_area("Description", key=f"maintenance_description_{form_key}")

            cost_col, supplier_col, next_due_col = st.columns(3, gap="medium")
            with cost_col:
                cost = st.number_input(
                    "Cost",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    key=f"maintenance_cost_{form_key}",
                )
            with supplier_col:
                supplier_name = None
                if supplier_options:
                    supplier_name = st.selectbox(
                        "Supplier",
                        supplier_options,
                        key=f"maintenance_supplier_{form_key}",
                    )
                    if supplier_name == "Select supplier":
                        supplier_name = ""
                else:
                    supplier_name = st.text_input(
                        "Supplier",
                        key=f"maintenance_supplier_text_{form_key}",
                    )
            with next_due_col:
                next_due_date = st.date_input(
                    "Next Due Date",
                    value=service_date,
                    key=f"maintenance_next_due_{form_key}",
                )

            maintenance_status = st.selectbox(
                "Status *",
                ["Pending", "In Progress", "Completed"],
                key=f"maintenance_status_{form_key}",
            )

            submitted = st.form_submit_button(
                "Add Maintenance Record",
                use_container_width=True,
                type="primary",
            )

            if submitted:
                if not maintenance_id:
                    st.error("Please provide a Maintenance ID")
                elif len(asset_option_labels) > 1 and asset_label_selected == "Select asset":
                    st.error("Please select an Asset")
                elif not asset_id:
                    st.error("Please provide an Asset ID")
                else:
                    if supplier_options and supplier_name == "":
                        st.error("Please select a Supplier")
                    else:
                        data_map = {
                            "Maintenance ID": maintenance_id,
                            "Asset ID": asset_id,
                            "Maintenance Type": maintenance_type,
                            "Maintenance Date": service_date.strftime("%Y-%m-%d"),
                            "Description": description,
                            "Cost": f"{cost:.2f}",
                            "Supplier": supplier_name,
                            "Next Due Date": next_due_date.strftime("%Y-%m-%d") if next_due_date else "",
                            "Status": maintenance_status,
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
                                    if maintenance_status == "In Progress" and asset_status_col:
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id, "Maintenance")
                                    elif maintenance_status == "Completed" and asset_status_col:
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id, "Active")
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
            asset_id_filter_options = ["All Asset IDs"] + sorted(
                maintenance_df["Asset ID"].dropna().astype(str).str.strip().unique().tolist()
            )
            asset_name_filter_options = ["All Asset Names"] + sorted(
                maintenance_df["Asset ID"]
                .dropna()
                .astype(str)
                .str.strip()
                .map(lambda aid: asset_id_to_name.get(aid.lower(), ""))
                .unique()
                .tolist()
            )
            status_filter_options = ["All Status"] + ["Pending", "In Progress", "Completed"]
            filter_cols = st.columns(3, gap="medium")
            with filter_cols[0]:
                selected_status_filter = st.selectbox(
                    "Filter by Status",
                    status_filter_options,
                    key="maintenance_status_filter",
                )
            with filter_cols[1]:
                selected_asset_id_filter = st.selectbox(
                    "Filter by Asset ID",
                    asset_id_filter_options,
                    key="maintenance_asset_id_filter",
                )
            with filter_cols[2]:
                selected_asset_name_filter = st.selectbox(
                    "Filter by Asset Name",
                    asset_name_filter_options,
                    key="maintenance_asset_name_filter",
                )

            filtered_df = maintenance_df.copy()
            if selected_status_filter != "All Status":
                filtered_df = filtered_df[
                    filtered_df["Status"].astype(str).str.strip().str.lower()
                    == selected_status_filter.strip().lower()
                ]
            if selected_asset_id_filter != "All Asset IDs":
                filtered_df = filtered_df[
                    filtered_df["Asset ID"].astype(str).str.strip() == selected_asset_id_filter
                ]
            if selected_asset_name_filter != "All Asset Names":
                filtered_df = filtered_df[
                    filtered_df["Asset ID"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map(lambda aid: asset_id_to_name.get(aid, ""))
                    == selected_asset_name_filter
                ]

            if filtered_df.empty:
                if selected_status_filter != "All Status":
                    st.warning("No maintenance records match your filters.")
                else:
                    st.info("No maintenance records found. Add one using the 'Add Maintenance Record' tab.")
            else:
                asset_label_list = asset_option_labels[1:] if len(asset_option_labels) > 1 else []
                display_df = filtered_df.copy()
                display_df["Asset Name"] = display_df["Asset ID"].astype(str).str.strip().str.lower().map(asset_id_to_name).fillna("")
                display_df["Cost"] = pd.to_numeric(
                    display_df["Cost"].replace("", 0).astype(str).str.replace(",", ""),
                    errors="coerce",
                ).fillna(0.0)
                display_df["Maintenance Date"] = pd.to_datetime(
                    display_df["Maintenance Date"], errors="coerce"
                ).dt.date
                display_df["Next Due Date"] = pd.to_datetime(
                    display_df["Next Due Date"], errors="coerce"
                ).dt.date
                table_df = display_df[
                    [
                        "Maintenance ID",
                        "Asset ID",
                        "Asset Name",
                        "Maintenance Type",
                        "Maintenance Date",
                        "Description",
                        "Cost",
                        "Supplier",
                        "Status",
                        "Next Due Date",
                    ]
                ]

                st.markdown(
                    """
                    <style>
                    [data-testid="stDataEditor"] thead th,
                    [data-testid="stDataEditor"] div[role="columnheader"] {
                        background-color: #BF092F !important;
                        color: #1A202C !important;
                        font-weight: 600 !important;
                    }
                    [data-testid="stDataEditor"] div[role="columnheader"] * {
                        color: #1A202C !important;
                    }
                    [data-testid="stDataEditor"] tbody td {
                        border-right: 1px solid #f0f0f0 !important;
                    }
                    [data-testid="stDataEditor"] tbody td:last-child {
                        border-right: none !important;
                    }
                    [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div[title="Completed"] {
                        background-color: transparent !important;
                        color: #2f855a !important;
                        font-weight: 600 !important;
                        border-radius: 20px;
                        padding: 0.1rem 0.65rem;
                        text-align: center;
                    }
                    [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div[title="In Progress"] {
                        background-color: #BF092F !important;
                        color: #ffffff !important;
                        border-radius: 20px;
                        padding: 0.1rem 0.65rem;
                        text-align: center;
                    }
                    [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div[title="Pending"] {
                        background-color: #BF092F !important;
                        color: #ffffff !important;
                        border-radius: 20px;
                        padding: 0.1rem 0.65rem;
                        text-align: center;
                    }
                    [data-testid="stDataEditor"] div[data-baseweb="select"] > div {
                        background-color: #ffffff !important;
                    }
                    [data-testid="stDataEditor"] div[data-testid="stDataEditorPrimaryToolbar"] button[title*="Add row"] {
                        display: none !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                editor_response = st.data_editor(
                    table_df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=False,
                    column_config={
                        "Maintenance ID": st.column_config.TextColumn("Maintenance ID", disabled=True),
                        "Asset ID": st.column_config.TextColumn("Asset ID", disabled=True),
                        "Asset Name": st.column_config.TextColumn("Asset Name", disabled=True),
                        "Maintenance Type": st.column_config.TextColumn("Type", disabled=True),
                        "Maintenance Date": st.column_config.DateColumn(
                            "Maintenance Date", format="YYYY-MM-DD", disabled=False
                        ),
                        "Description": st.column_config.TextColumn("Description", disabled=False),
                        "Cost": st.column_config.NumberColumn(
                            "Cost", format="%.2f", step=0.01, disabled=False
                        ),
                        "Supplier": st.column_config.TextColumn("Supplier", disabled=True),
                        "Status": st.column_config.SelectboxColumn(
                            "Status",
                            options=["Pending", "In Progress", "Completed"],
                            disabled=False,
                        ),
                        "Next Due Date": st.column_config.DateColumn(
                            "Next Due Date", format="YYYY-MM-DD", disabled=False
                        ),
                    },
                    num_rows="dynamic",
                    key="maintenance_table_view",
                )

                st.markdown("<hr style='margin: 0.75rem 0; border: 0; border-top: 1px solid #d0d0d0;' />", unsafe_allow_html=True)
                st.markdown(
                    """
                    <style>
                    div[data-testid="stButton"] button:disabled,
                    div[data-testid="stButton"] button:disabled:hover,
                    div[data-testid="stButton"] button:disabled:focus {
                        background-color: #cbd5e0 !important;
                        color: #4a5568 !important;
                        border-color: #cbd5e0 !important;
                        cursor: not-allowed !important;
                        opacity: 1 !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                editor_state = st.session_state.get("maintenance_table_view", {})
                edited_df = deepcopy(editor_state.get("edited_rows", {}))
                edited_cells = deepcopy(editor_state.get("edited_cells", {}))
                deleted_rows = list(editor_state.get("deleted_rows", []))
                added_rows = list(editor_state.get("added_rows", []))

                def _normalize_idx(idx_value):
                    try:
                        return int(idx_value)
                    except (TypeError, ValueError):
                        return idx_value

                def _get_edits(source_dict, idx_value):
                    if idx_value in source_dict:
                        return source_dict[idx_value]
                    idx_str = str(idx_value)
                    return source_dict.get(idx_str, {})

                st.session_state.setdefault("maintenance_save_success", False)
                st.session_state.setdefault("maintenance_pending_changes", False)

                has_changes = bool(edited_df or edited_cells or deleted_rows or added_rows)
                st.session_state["maintenance_pending_changes"] = has_changes
                if has_changes:
                    st.session_state["maintenance_save_success"] = False
                pending_changes = st.session_state.get("maintenance_pending_changes", False)
                success = False
                cooldown_seconds = 10
                current_ts = time.time()
                last_save_ts = float(st.session_state.get("maintenance_last_save_ts", 0.0) or 0.0)
                cooldown_remaining = max(0.0, cooldown_seconds - (current_ts - last_save_ts))
                if cooldown_remaining > 0:
                    st.warning(
                        f"Please wait {cooldown_remaining:.0f} second(s) before saving again to avoid hitting Google Sheets limits.",
                        icon="⏳",
                    )

                action_cols = st.columns([1, 1], gap="small")
                with action_cols[0]:
                    save_clicked = st.button(
                        "Save Changes",
                        type="primary",
                        use_container_width=True,
                        disabled=(not pending_changes) or (cooldown_remaining > 0),
                        key="maintenance_save_changes",
                    )
                with action_cols[1]:
                    discard_clicked = st.button(
                        "Discard Changes",
                        use_container_width=True,
                        disabled=not has_changes,
                        key="maintenance_discard_changes",
                    )

                if discard_clicked and has_changes:
                    table_state = st.session_state.get("maintenance_table_view")
                    if isinstance(table_state, dict):
                        table_state["edited_rows"] = {}
                        table_state["edited_cells"] = {}
                        table_state["deleted_rows"] = []
                        table_state["added_rows"] = []
                    st.session_state.pop("maintenance_table_view", None)
                    st.session_state["maintenance_pending_changes"] = False

                if save_clicked and has_changes:
                    success = True
                    st.session_state["maintenance_save_success"] = False
                    if cooldown_remaining > 0:
                        st.warning("Please wait for the save cooldown before saving again.", icon="⏱️")
                        success = False

                    if deleted_rows and save_clicked:
                        for delete_idx in sorted([_normalize_idx(idx) for idx in deleted_rows], reverse=True):
                            if isinstance(delete_idx, int) and delete_idx < len(filtered_df):
                                target_row = filtered_df.iloc[delete_idx]
                                match_df = maintenance_df[
                                    maintenance_df["Maintenance ID"].astype(str).str.strip()
                                    == str(target_row.get("Maintenance ID", "")).strip()
                                ]
                                if not match_df.empty:
                                    original_idx = int(match_df.index[0])
                                    if delete_data(SHEETS["maintenance"], original_idx):
                                        st.session_state["maintenance_success_message"] = (
                                            f"🗑️ Maintenance record '{target_row.get('Maintenance ID', '')}' deleted."
                                        )
                                        maintenance_df = maintenance_df.drop(index=original_idx)
                                    else:
                                        st.error("Failed to delete maintenance record.")
                                        success = False
                            else:
                                st.error("Unable to resolve maintenance row for deletion.")
                                success = False

                    rows_to_update: set[int] = set()
                    for idx_key in list(edited_df.keys()) + list(edited_cells.keys()):
                        norm_idx = _normalize_idx(idx_key)
                        if isinstance(norm_idx, int):
                            rows_to_update.add(norm_idx)

                    if rows_to_update:
                        for idx in rows_to_update:
                            if idx >= len(filtered_df):
                                continue
                            current_row = filtered_df.iloc[idx].copy()
                            edits = dict(_get_edits(edited_df, idx))
                            cell_changes = _get_edits(edited_cells, idx)
                            if cell_changes:
                                edits.update(cell_changes)
                            if not edits:
                                continue
                            for column, new_value in edits.items():
                                current_row[column] = new_value

                            maintenance_date_value = current_row.get("Maintenance Date", "")
                            if isinstance(maintenance_date_value, datetime):
                                maintenance_date_str = maintenance_date_value.strftime("%Y-%m-%d")
                            elif hasattr(maintenance_date_value, "isoformat"):
                                try:
                                    maintenance_date_str = maintenance_date_value.isoformat()
                                except Exception:
                                    maintenance_date_str = str(maintenance_date_value)
                            else:
                                maintenance_date_str = str(maintenance_date_value)
                            if str(maintenance_date_str).lower() in ("nat", "nan", "none"):
                                maintenance_date_str = ""

                            next_due_value = current_row.get("Next Due Date", "")
                            if isinstance(next_due_value, datetime):
                                next_due_str = next_due_value.strftime("%Y-%m-%d")
                            elif hasattr(next_due_value, "isoformat"):
                                try:
                                    next_due_str = next_due_value.isoformat()
                                except Exception:
                                    next_due_str = str(next_due_value)
                            else:
                                next_due_str = str(next_due_value)
                            if str(next_due_str).lower() in ("nat", "nan", "none"):
                                next_due_str = ""

                            update_map = {
                                "Maintenance ID": current_row.get("Maintenance ID", ""),
                                "Asset ID": current_row.get("Asset ID", ""),
                                "Maintenance Type": current_row.get("Maintenance Type", ""),
                                "Maintenance Date": maintenance_date_str,
                                "Description": current_row.get("Description", ""),
                                "Cost": f"{pd.to_numeric(str(current_row.get('Cost', 0)).replace(',', ''), errors='coerce') or 0:.2f}",
                                "Supplier": current_row.get("Supplier", ""),
                                "Next Due Date": next_due_str,
                                "Status": current_row.get("Status", ""),
                            }
                            match_df = maintenance_df[
                                maintenance_df["Maintenance ID"].astype(str).str.strip()
                                == str(current_row.get("Maintenance ID", "")).strip()
                            ]
                            if not match_df.empty:
                                original_idx = int(match_df.index[0])
                                column_order = list(maintenance_df.columns)
                                updated_row = [update_map.get(col, match_df.iloc[0].get(col, "")) for col in column_order]
                                if update_data(SHEETS["maintenance"], original_idx, updated_row):
                                    st.session_state["maintenance_success_message"] = (
                                        f"✅ Maintenance record '{current_row.get('Maintenance ID', '')}' updated successfully!"
                                    )
                                    maintenance_df.loc[original_idx, column_order] = updated_row
                                    for col_name, val in zip(column_order, updated_row):
                                        if col_name in filtered_df.columns and idx < len(filtered_df):
                                            filtered_df.at[filtered_df.index[idx], col_name] = val
                                    if update_map["Status"] == "In Progress" and asset_status_col:
                                        _update_asset_status_for_maintenance(
                                            assets_df, asset_status_col, update_map["Asset ID"], "Maintenance"
                                        )
                                    elif update_map["Status"] == "Completed" and asset_status_col:
                                        _update_asset_status_for_maintenance(
                                            assets_df, asset_status_col, update_map["Asset ID"], "Active"
                                        )
                                else:
                                    st.error("Failed to update maintenance record")
                                    success = False

                    if added_rows:
                        st.warning("New rows must be added from the 'Add Maintenance Record' tab.")

                if success and save_clicked and has_changes:
                    st.success("Changes saved successfully! Refresh if the table doesn't update automatically.", icon="✅")
                    st.session_state["maintenance_save_success"] = True
                    st.session_state["maintenance_pending_changes"] = False
                if success:
                    st.session_state["cached_sheet_maintenance"] = read_data(SHEETS["maintenance"])
                    st.session_state["cached_sheet_assets"] = read_data(SHEETS["assets"])
                    table_state = st.session_state.get("maintenance_table_view")
                    if isinstance(table_state, dict):
                        table_state["edited_rows"] = {}
                        table_state["edited_cells"] = {}
                        table_state["deleted_rows"] = []
                        table_state["added_rows"] = []
                    st.session_state.pop("maintenance_table_view", None)
                    st.session_state["maintenance_last_save_ts"] = time.time()
                    st.rerun()

                if (
                    st.session_state.get("maintenance_pending_changes", False)
                    and not st.session_state.get("maintenance_save_success", False)
                ):
                    st.info("You have unsaved maintenance changes. Click 'Save Changes' to apply them.", icon="✏️")

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
                    asset_options_edit = ["Select asset"] + asset_label_list if asset_label_list else []
                    if asset_options_edit:
                        current_label = asset_id_to_label.get(str(record.get("Asset ID", "")).strip().lower(), "Select asset")
                        try:
                            default_asset_idx = asset_options_edit.index(current_label)
                        except ValueError:
                            default_asset_idx = 0
                        asset_label_new = st.selectbox(
                            "Asset *",
                            asset_options_edit,
                            index=default_asset_idx,
                        )
                        asset_id_new = asset_label_to_id.get(asset_label_new, "")
                    else:
                        asset_id_new = st.text_input(
                            "Asset ID *",
                            value=record.get("Asset ID", ""),
                        )

                    maintenance_type_new = st.selectbox(
                        "Maintenance Type *",
                        ["Preventive", "Breakdown", "Calibration"],
                        index={
                            "preventive": 0,
                            "breakdown": 1,
                            "calibration": 2,
                        }.get(str(record.get("Maintenance Type", "Preventive")).strip().lower(), 0),
                    )
                    service_date_new = st.date_input(
                        "Maintenance Date *",
                        value=parse_date_value(record.get("Maintenance Date")),
                    )
                    description_new = st.text_area(
                        "Description",
                        value=record.get("Description", ""),
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
                    if not suppliers_df.empty and "Supplier Name" in suppliers_df.columns:
                        supplier_options_edit = ["Select supplier"] + suppliers_df["Supplier Name"].dropna().astype(str).str.strip().tolist()
                        try:
                            default_supplier_idx = supplier_options_edit.index(record.get("Supplier", ""))
                        except ValueError:
                            default_supplier_idx = 0
                        supplier_new = st.selectbox(
                            "Supplier",
                            supplier_options_edit,
                            index=default_supplier_idx,
                        )
                        if supplier_new == "Select supplier":
                            supplier_new = ""
                    else:
                        supplier_new = st.text_input(
                            "Supplier",
                            value=record.get("Supplier", ""),
                        )

                    next_due_new = st.date_input(
                        "Next Due Date",
                        value=parse_date_value(record.get("Next Due Date")),
                    )

                    status_new = st.selectbox(
                        "Status *",
                        ["Pending", "In Progress", "Completed"],
                        index={
                            "pending": 0,
                            "in progress": 1,
                            "completed": 2,
                        }.get(str(record.get("Status", "Pending")).strip().lower(), 0),
                    )

                    col_update, col_cancel = st.columns(2)
                    with col_update:
                        if st.form_submit_button("Update", use_container_width=True):
                            if asset_options_edit and asset_label_new == "Select asset":
                                st.error("Please select an Asset")
                            elif not asset_id_new:
                                st.error("Please provide an Asset ID")
                            else:
                                update_map = {
                                    "Maintenance ID": edit_id,
                                    "Asset ID": asset_id_new,
                                    "Maintenance Type": maintenance_type_new,
                                    "Maintenance Date": service_date_new.strftime("%Y-%m-%d"),
                                    "Description": description_new,
                                    "Cost": f"{cost_new:.2f}",
                                    "Supplier": supplier_new,
                                    "Next Due Date": next_due_new.strftime("%Y-%m-%d") if next_due_new else "",
                                    "Status": status_new,
                                }
                                column_order = list(maintenance_df.columns)
                                updated_row = [update_map.get(col, record.get(col, "")) for col in column_order]
                                if update_data(SHEETS["maintenance"], int(edit_idx), updated_row):
                                    st.session_state["maintenance_success_message"] = (
                                        f"✅ Maintenance record '{edit_id}' updated successfully!"
                                    )
                                    if status_new == "In Progress" and asset_status_col:
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id_new, "Maintenance")
                                    elif status_new == "Completed" and asset_status_col:
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id_new, "Active")
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

    with tab3:
        st.subheader("Cumulative Maintenance Cost")
        if maintenance_df.empty:
            st.info("No maintenance records available.")
        else:
            cost_series = (
                maintenance_df["Cost"].replace("", 0).astype(str).str.replace(",", "").astype(float)
                if "Cost" in maintenance_df.columns
                else pd.Series(dtype=float)
            )
            maintenance_df_with_cost = maintenance_df.copy()
            maintenance_df_with_cost["Cost_numeric"] = cost_series if not cost_series.empty else 0.0
            summary_df = (
                maintenance_df_with_cost.groupby(["Maintenance ID", "Asset ID"], dropna=False)[["Cost_numeric"]]
                .sum()
                .reset_index()
            )
            summary_df = summary_df.rename(columns={"Cost_numeric": "Total Cost"})
            if "Next Due Date" in maintenance_df.columns:
                next_due_map = maintenance_df.set_index("Maintenance ID")["Next Due Date"].to_dict()
                summary_df["Next Due Date"] = summary_df["Maintenance ID"].map(next_due_map).fillna("")
            else:
                summary_df["Next Due Date"] = ""
            summary_df["Asset"] = summary_df.apply(
                lambda row: asset_id_to_label.get(str(row["Asset ID"]).strip().lower(), str(row["Asset ID"])),
                axis=1
            )
            aggregated = (
                summary_df.groupby("Asset ID", dropna=False)["Total Cost"]
                .sum()
                .reset_index()
            )
            aggregated["Asset ID"] = aggregated["Asset ID"].astype(str).str.strip()
            aggregated["Asset Name"] = aggregated["Asset ID"].str.lower().map(asset_id_to_name).fillna("")
            aggregated["Total Cost"] = aggregated["Total Cost"].map(lambda v: f"{v:.2f}")

            asset_filter_options = ["All Assets"] + sorted(aggregated["Asset ID"].unique().tolist())
            selected_filter = st.selectbox(
                "Filter by Asset",
                asset_filter_options,
                key="maintenance_cost_asset_filter",
            )
            filtered_aggregated = aggregated
            if selected_filter != "All Assets":
                filtered_aggregated = aggregated[aggregated["Asset ID"] == selected_filter]

            display_df = filtered_aggregated[["Asset ID", "Asset Name", "Total Cost"]]
            st.dataframe(
                display_df,
                use_container_width=True,
            )


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

    # Styles are applied globally via styles/main.css

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

    assignment_asset_option_labels: list[str] = ["Select asset"]
    assignment_asset_label_to_id: dict[str, str] = {}
    asset_id_col = None
    asset_assigned_col = None
    asset_status_col = None
    assignment_asset_name_col = None
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
            elif col_norm in {"asset name", "name"} and assignment_asset_name_col is None:
                assignment_asset_name_col = col

        asset_id_source = asset_id_col or ("Asset ID" if "Asset ID" in assets_df.columns else None)
        if asset_id_source:
            for _, row in assets_df.iterrows():
                asset_id_value = str(row.get(asset_id_source, "")).strip()
                if not asset_id_value:
                    continue
                asset_name_value = (
                    str(row.get(assignment_asset_name_col, "")).strip()
                    if assignment_asset_name_col
                    else ""
                )
                asset_label = asset_id_value if not asset_name_value else f"{asset_id_value} - {asset_name_value}"
                assignment_asset_option_labels.append(asset_label)
                assignment_asset_label_to_id[asset_label] = asset_id_value

    asset_options = assignment_asset_option_labels.copy()

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
        if "assignment_success_message" in st.session_state:
            st.success(st.session_state["assignment_success_message"])
            del st.session_state["assignment_success_message"]

        if "assignment_form_key" not in st.session_state:
            st.session_state["assignment_form_key"] = 0

        form_key = st.session_state["assignment_form_key"]

        assignment_form_css = f"""
        <style>
        div[data-testid="stForm"][aria-label="assignment_form_{form_key}"] {{
            background-color: #ffffff !important;
            padding: 1.5rem !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        }}
        </style>
        """
        st.markdown(assignment_form_css, unsafe_allow_html=True)

        with st.form(f"assignment_form_{form_key}"):
            auto_generate = st.checkbox(
                "Auto-generate Assignment ID",
                value=True,
                key=f"assignment_auto_{form_key}",
            )

            id_col, user_col, asset_col = st.columns(3, gap="medium")
            with id_col:
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

            with user_col:
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

            asset_label_selected: str | None = None
            with asset_col:
                if len(asset_options) > 1:
                    asset_label_selected = st.selectbox(
                        "Asset *",
                        asset_options,
                        key=f"assignment_asset_{form_key}",
                    )
                    asset_id = assignment_asset_label_to_id.get(asset_label_selected or "", "")
                else:
                    asset_id = st.text_input(
                        "Asset ID *",
                        key=f"assignment_asset_text_{form_key}",
                    )
                    if assets_df.empty:
                        st.warning("No assets found. Please add assets first.")

            issued_col, assign_date_col, expected_return_col = st.columns(3, gap="medium")
            with issued_col:
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

            with assign_date_col:
                assignment_date = st.date_input(
                    "Assignment Date *",
                    value=datetime.now().date(),
                    key=f"assignment_date_{form_key}",
                )

            with expected_return_col:
                expected_return_date = st.date_input(
                    "Expected Return Date",
                    value=assignment_date,
                    key=f"assignment_expected_return_{form_key}",
                )

            return_col, status_col, condition_col = st.columns(3, gap="medium")
            with return_col:
                return_date = st.date_input(
                    "Return Date",
                    value=assignment_date,
                    key=f"assignment_return_date_{form_key}",
                )

            with status_col:
                status = st.selectbox(
                    "Status",
                    ["Assigned", "Returned", "Under Repair"],
                    key=f"assignment_status_{form_key}",
                )

            with condition_col:
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
                elif (
                    len(asset_options) > 1
                    and (asset_label_selected == "Select asset" or not asset_id)
                ):
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
        if "assignment_success_message" in st.session_state:
            st.success(st.session_state["assignment_success_message"])
            del st.session_state["assignment_success_message"]

        st.session_state.pop("edit_assignment_id", None)
        st.session_state.pop("edit_assignment_idx", None)

        if assignments_df.empty:
            st.info("No assignments found. Add one using the 'Add Assignment' tab.")
        else:
            st.subheader("View / Edit Assignments")

            filter_cols = st.columns([2, 1, 1, 1])
            with filter_cols[0]:
                search_term = st.text_input(
                    "🔍 Search Assignments",
                    placeholder="Search by assignment ID, username, or asset...",
                    key="assignment_search",
                )
            with filter_cols[1]:
                status_options = ["All Status"] + sorted(
                    {str(val).strip() for val in assignments_df.get("Status", pd.Series()).dropna()}
                )
                selected_status = st.selectbox("Status Filter", status_options, key="assignment_status_filter")
            with filter_cols[2]:
                username_filter_options = ["All Users"] + sorted(
                    {str(val).strip() for val in assignments_df.get("Username", pd.Series()).dropna()}
                )
                selected_username = st.selectbox("User Filter", username_filter_options, key="assignment_user_filter")
            with filter_cols[3]:
                asset_filter_options = ["All Assets"] + sorted(
                    {str(val).strip() for val in assignments_df.get("Asset ID", pd.Series()).dropna()}
                )
                selected_asset = st.selectbox("Asset Filter", asset_filter_options, key="assignment_asset_filter")

            filtered_df = assignments_df.copy()
            if search_term:
                term = search_term.strip().lower()
                filtered_df = filtered_df[
                    filtered_df.apply(
                        lambda row: term in " ".join(row.astype(str).str.lower()),
                        axis=1,
                    )
                ]

            if selected_status != "All Status":
                filtered_df = filtered_df[
                    filtered_df["Status"].astype(str).str.strip().str.lower()
                    == selected_status.strip().lower()
                ]

            if selected_username != "All Users":
                filtered_df = filtered_df[
                    filtered_df["Username"].astype(str).str.strip().str.lower()
                    == selected_username.strip().lower()
                ]

            if selected_asset != "All Assets":
                filtered_df = filtered_df[
                    filtered_df["Asset ID"].astype(str).str.strip().str.lower()
                    == selected_asset.strip().lower()
                ]

            if filtered_df.empty:
                st.info("No assignments match the current filters.")
                st.session_state["assignments_pending_changes"] = False
            else:
                st.caption(f"Showing {len(filtered_df)} of {len(assignments_df)} assignment(s)")

                base_df = filtered_df.reset_index(drop=True).copy()
                editor_df = base_df[
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
                    ]
                ].copy()
                date_columns = ["Assignment Date", "Expected Return Date", "Return Date"]
                for date_col in date_columns:
                    editor_df[date_col] = pd.to_datetime(editor_df[date_col], errors="coerce").dt.date

                editor_df = editor_df.fillna("")

                st.markdown(
                    """
                    <style>
                    [data-testid="stDataEditor"] thead th,
                    [data-testid="stDataEditor"] div[role="columnheader"] {
                        background-color: #BF092F !important;
                        color: #1A202C !important;
                        font-weight: 600 !important;
                    }
                    [data-testid="stDataEditor"] div[role="columnheader"] * {
                        color: #1A202C !important;
                    }
                    [data-testid="stDataEditor"] tbody td {
                        border-right: 1px solid #f0f0f0 !important;
                    }
                    [data-testid="stDataEditor"] tbody td:last-child {
                        border-right: none !important;
                    }
                    [data-testid="stDataEditor"] div[data-testid="stDataEditorPrimaryToolbar"] button[title*="Add row"] {
                        display: none !important;
                    }
                    [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div[title="Assigned"] {
                        background-color: #BF092F !important;
                        color: #ffffff !important;
                        border-radius: 20px;
                        padding: 0.1rem 0.65rem;
                        text-align: center;
                    }
                    [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div[title="Returned"] {
                        background-color: transparent !important;
                        color: #2f855a !important;
                        font-weight: 600 !important;
                        border-radius: 20px;
                        padding: 0.1rem 0.65rem;
                        text-align: center;
                    }
                    [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div[title="Under Repair"] {
                        background-color: #ecc94b !important;
                        color: #1A202C !important;
                        border-radius: 20px;
                        padding: 0.1rem 0.65rem;
                        text-align: center;
                    }
                    div[data-testid="stButton"] button:disabled,
                    div[data-testid="stButton"] button:disabled:hover,
                    div[data-testid="stButton"] button:disabled:focus {
                        background-color: #cbd5e0 !important;
                        color: #4a5568 !important;
                        border-color: #cbd5e0 !important;
                        cursor: not-allowed !important;
                        opacity: 1 !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                username_options_select = sorted(
                    {str(val).strip() for val in users_df.get("Username", pd.Series()).dropna()}
                    if "users_df" in locals()
                    else {str(val).strip() for val in base_df.get("Username", pd.Series()).dropna()}
                )
                if not username_options_select:
                    username_options_select = sorted(
                        {str(val).strip() for val in base_df.get("Username", pd.Series()).dropna()}
                    )
                asset_options_select = sorted(
                    {str(val).strip() for val in assets_df.get("Asset ID", pd.Series()).dropna()}
                    if "assets_df" in locals()
                    else {str(val).strip() for val in base_df.get("Asset ID", pd.Series()).dropna()}
                )
                issued_by_options_select = sorted(
                    {str(val).strip() for val in issued_by_options}
                    if issued_by_options
                    else {str(val).strip() for val in base_df.get("Issued By", pd.Series()).dropna()}
                )

                status_options_select = ["Assigned", "Returned", "Under Repair"]
                condition_options_select = ["Working", "Damaged", "Used"]

                editor_response = st.data_editor(
                    editor_df,
                    hide_index=True,
                    use_container_width=True,
                    disabled=False,
                    column_config={
                        "Assignment ID": st.column_config.TextColumn("Assignment ID", disabled=True),
                        "Username": st.column_config.SelectboxColumn(
                            "Username",
                            options=username_options_select or [""],
                        ),
                        "Asset ID": st.column_config.SelectboxColumn(
                            "Asset ID",
                            options=asset_options_select or [""],
                        ),
                        "Issued By": st.column_config.SelectboxColumn(
                            "Issued By",
                            options=issued_by_options_select or [""],
                        ),
                        "Assignment Date": st.column_config.DateColumn("Assignment Date", format="YYYY-MM-DD"),
                        "Expected Return Date": st.column_config.DateColumn("Expected Return Date", format="YYYY-MM-DD"),
                        "Return Date": st.column_config.DateColumn("Return Date", format="YYYY-MM-DD"),
                        "Status": st.column_config.SelectboxColumn("Status", options=status_options_select),
                        "Condition on Issue": st.column_config.SelectboxColumn(
                            "Condition on Issue", options=condition_options_select
                        ),
                        "Remarks": st.column_config.TextColumn("Remarks"),
                    },
                    num_rows="dynamic",
                    key="assignments_table_view",
                )

                st.markdown("<hr style='margin: 0.75rem 0; border: 0; border-top: 1px solid #d0d0d0;' />", unsafe_allow_html=True)

                editor_state = st.session_state.get("assignments_table_view", {})
                edited_rows = deepcopy(editor_state.get("edited_rows", {}))
                edited_cells = deepcopy(editor_state.get("edited_cells", {}))
                deleted_rows = list(editor_state.get("deleted_rows", []))
                added_rows = list(editor_state.get("added_rows", []))

                st.session_state.setdefault("assignments_save_success", False)
                st.session_state.setdefault("assignments_pending_changes", False)
                st.session_state.setdefault("assignments_last_save_ts", 0.0)

                pending_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
                if pending_changes:
                    st.session_state["assignments_pending_changes"] = True
                    st.session_state["assignments_save_success"] = False
                else:
                    st.session_state["assignments_pending_changes"] = False

                cooldown_seconds = 10
                current_ts = time.time()
                last_save_ts = float(st.session_state.get("assignments_last_save_ts", 0.0) or 0.0)
                cooldown_remaining = max(0.0, cooldown_seconds - (current_ts - last_save_ts))

                if st.session_state.get("assignments_pending_changes", False) and not st.session_state.get(
                    "assignments_save_success", False
                ):
                    st.info("You have unsaved assignment changes. Click 'Save Changes' to apply them.", icon="✏️")
                if cooldown_remaining > 0:
                    st.warning(
                        f"Please wait {cooldown_remaining:.0f} second(s) before saving again to avoid hitting Google Sheets limits.",
                        icon="⏳",
                    )

                action_cols = st.columns([1, 1], gap="small")
                with action_cols[0]:
                    save_clicked = st.button(
                        "Save Changes",
                        type="primary",
                        use_container_width=True,
                        disabled=(not st.session_state.get("assignments_pending_changes", False)) or (cooldown_remaining > 0),
                        key="assignments_save_changes",
                    )
                with action_cols[1]:
                    discard_clicked = st.button(
                        "Discard Changes",
                        use_container_width=True,
                        disabled=not st.session_state.get("assignments_pending_changes", False),
                        key="assignments_discard_changes",
                    )

                success = False
                messages: list[str] = []

                if discard_clicked and st.session_state.get("assignments_pending_changes", False):
                    st.session_state.pop("assignments_table_view", None)
                    st.session_state["assignments_pending_changes"] = False
                    st.session_state["assignments_save_success"] = False
                    st.rerun()

                if save_clicked and st.session_state.get("assignments_pending_changes", False):
                    success = True
                    st.session_state["assignments_save_success"] = False
                    if cooldown_remaining > 0:
                        st.warning("Please wait for the save cooldown before saving again.", icon="⏱️")
                        success = False

                    if added_rows:
                        st.warning("Please use the 'Add Assignment' tab to create new assignments.", icon="ℹ️")

                    deleted_set = set()
                    if deleted_rows and success:
                        for delete_idx in sorted(deleted_rows, reverse=True):
                            try:
                                normalized_idx = int(delete_idx)
                            except (TypeError, ValueError):
                                normalized_idx = delete_idx
                            if isinstance(normalized_idx, int) and normalized_idx < len(base_df):
                                row = base_df.iloc[normalized_idx]
                                assignment_id_value = str(row.get("Assignment ID", "")).strip()
                                match_df = assignments_df[
                                    assignments_df["Assignment ID"].astype(str).str.strip().str.lower()
                                    == assignment_id_value.lower()
                                ]
                                if not match_df.empty:
                                    original_idx = int(match_df.index[0])
                                    if delete_data(SHEETS["assignments"], original_idx):
                                        messages.append(f"🗑️ Assignment '{assignment_id_value}' deleted.")
                                        status_after_delete = str(row.get("Status", "")).strip()
                                        if status_after_delete.lower() == "assigned":
                                            status_after_delete = ""
                                        update_asset_assignment(row.get("Asset ID", ""), "", status_after_delete)
                                        assignments_df = assignments_df.drop(index=original_idx)
                                        deleted_set.add(normalized_idx)
                                        st.session_state["refresh_asset_users"] = True
                                    else:
                                        st.error(f"Failed to delete assignment '{assignment_id_value}'.")
                                        success = False
                                else:
                                    st.error(f"Unable to locate assignment '{assignment_id_value}' for deletion.")
                                    success = False
                            else:
                                st.error("Unable to resolve assignment row for deletion.")
                                success = False

                    if success:
                        rows_to_update: set[int] = set()
                        for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                            try:
                                norm_idx = int(idx_key)
                            except (TypeError, ValueError):
                                try:
                                    norm_idx = int(str(idx_key))
                                except ValueError:
                                    norm_idx = idx_key
                            if isinstance(norm_idx, int) and norm_idx not in deleted_set:
                                rows_to_update.add(norm_idx)

                        if isinstance(editor_response, pd.DataFrame):
                            for idx in range(len(editor_response)):
                                row = editor_response.iloc[idx]
                                original_row = base_df.iloc[idx] if idx < len(base_df) else None
                                if original_row is None:
                                    continue
                                has_diff = False
                                for column_name in editor_df.columns:
                                    if str(row.get(column_name, "")).strip() != str(original_row.get(column_name, "")).strip():
                                        has_diff = True
                                        break
                                if has_diff and idx not in deleted_set:
                                    rows_to_update.add(idx)

                        for idx in sorted(rows_to_update):
                            if not isinstance(idx, int) or idx >= len(editor_response):
                                continue

                            current_row = editor_response.iloc[idx]
                            original_row = base_df.iloc[idx]

                            assignment_id_value = str(current_row.get("Assignment ID", "")).strip()
                            username_value = str(current_row.get("Username", "")).strip()
                            asset_id_value = str(current_row.get("Asset ID", "")).strip()
                            issued_by_value = str(current_row.get("Issued By", "")).strip()
                            status_value = str(current_row.get("Status", "")).strip() or "Assigned"
                            condition_value = str(current_row.get("Condition on Issue", "")).strip() or "Working"
                            remarks_value = str(current_row.get("Remarks", "")).strip()

                            if not assignment_id_value:
                                continue
                            if not username_value:
                                st.error(f"Username is required for assignment '{assignment_id_value}'.")
                                success = False
                                continue
                            if not asset_id_value:
                                st.error(f"Asset ID is required for assignment '{assignment_id_value}'.")
                                success = False
                                continue
                            if not issued_by_value:
                                st.error(f"Issued By is required for assignment '{assignment_id_value}'.")
                                success = False
                                continue

                            def _date_to_string(value: Any) -> str:
                                if isinstance(value, datetime):
                                    return value.strftime("%Y-%m-%d")
                                if isinstance(value, pd.Timestamp):
                                    return value.strftime("%Y-%m-%d")
                                if hasattr(value, "isoformat"):
                                    try:
                                        return value.isoformat()
                                    except Exception:
                                        return str(value)
                                value_str = str(value).strip()
                                if value_str.lower() in ("nat", "nan", "none", ""):
                                    return ""
                                return value_str

                            assignment_date_str = _date_to_string(current_row.get("Assignment Date", ""))
                            expected_return_str = _date_to_string(current_row.get("Expected Return Date", ""))
                            return_date_str = _date_to_string(current_row.get("Return Date", ""))

                            match_df = assignments_df[
                                assignments_df["Assignment ID"].astype(str).str.strip().str.lower()
                                == assignment_id_value.lower()
                            ]
                            if match_df.empty:
                                st.error(f"Unable to locate assignment '{assignment_id_value}' for update.")
                                success = False
                                continue

                            original_idx = int(match_df.index[0])
                            old_asset_id = str(original_row.get("Asset ID", "")).strip()
                            old_status = str(original_row.get("Status", "")).strip()

                            updated_row = [
                                assignment_id_value,
                                username_value,
                                asset_id_value,
                                issued_by_value,
                                assignment_date_str,
                                expected_return_str,
                                return_date_str,
                                status_value,
                                condition_value,
                                remarks_value,
                            ]

                            if update_data(SHEETS["assignments"], original_idx, updated_row):
                                messages.append(f"✅ Assignment '{assignment_id_value}' updated successfully!")
                                assignments_df.loc[original_idx, assignments_df.columns] = updated_row

                                new_assignee = username_value if status_value == "Assigned" else ""
                                update_asset_assignment(asset_id_value, new_assignee, status_value)
                                if (
                                    asset_id_value != old_asset_id
                                    or (old_status.lower() == "assigned" and status_value != "Assigned")
                                ):
                                    old_status_value = "" if old_status.lower() == "assigned" else old_status
                                    update_asset_assignment(old_asset_id, "", old_status_value)
                                st.session_state["refresh_asset_users"] = True
                            else:
                                st.error(f"Failed to update assignment '{assignment_id_value}'.")
                                success = False

                if success and save_clicked and st.session_state.get("assignments_pending_changes", False):
                    st.session_state["assignments_save_success"] = True
                    st.session_state["assignments_pending_changes"] = False
                    st.session_state["assignments_last_save_ts"] = time.time()
                    st.session_state.pop("assignments_table_view", None)
                    st.session_state["assignment_success_message"] = (
                        " ".join(messages) if messages else "✅ Assignment changes saved successfully!"
                    )
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

        filter_cols = st.columns([2, 1, 1])
        with filter_cols[0]:
            search_term = st.text_input(
                "🔍 Search Users",
                placeholder="Search by Username, Email, or Role...",
                key="user_search",
            )
        with filter_cols[1]:
            role_filter_options = ["All Roles"] + sorted(
                {str(role).strip() for role in users_df.get("Role", pd.Series()).dropna()}
            )
            selected_role = st.selectbox("Role Filter", role_filter_options, key="user_role_filter")
        with filter_cols[2]:
            st.write("")

        filtered_df = users_df.copy()
        if search_term:
            mask = (
                filtered_df["Username"].astype(str).str.contains(search_term, case=False, na=False)
                | filtered_df["Email"].astype(str).str.contains(search_term, case=False, na=False)
                | filtered_df["Role"].astype(str).str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        if selected_role != "All Roles":
            filtered_df = filtered_df[
                filtered_df["Role"].astype(str).str.strip().str.lower()
                == selected_role.strip().lower()
            ]

        if filtered_df.empty:
            st.info("No users match the current filters.")
            return

        st.caption(f"Showing {len(filtered_df)} of {len(users_df)} user(s)")

        display_df = filtered_df[["Username", "Email", "Role"]].copy()
        display_df = display_df.fillna("")
        display_df["New Password"] = ""
        display_df["Confirm Password"] = ""
        base_df = display_df.copy()

        editor_response = st.data_editor(
            display_df,
            hide_index=True,
            use_container_width=True,
            disabled=False,
            column_config={
                "Username": st.column_config.TextColumn("Username", disabled=True),
                "Email": st.column_config.TextColumn("Email"),
                "Role": st.column_config.SelectboxColumn(
                    "Role",
                    options=sorted({str(role).strip() or "user" for role in users_df.get("Role", pd.Series()).dropna()} | {"admin", "user"}),
                ),
                "New Password": st.column_config.TextColumn(
                    "New Password",
                    help="Enter to reset password (leave blank to keep current)",
                ),
                "Confirm Password": st.column_config.TextColumn(
                    "Confirm Password",
                    help="Re-enter new password",
                ),
            },
            num_rows="dynamic",
            key="users_table_view",
        )

        st.markdown("<hr style='margin: 0.75rem 0; border: 0; border-top: 1px solid #d0d0d0;' />", unsafe_allow_html=True)

        editor_state = st.session_state.get("users_table_view", {})
        edited_df = deepcopy(editor_state.get("edited_rows", {}))
        edited_cells = deepcopy(editor_state.get("edited_cells", {}))
        deleted_rows = list(editor_state.get("deleted_rows", []))
        added_rows = list(editor_state.get("added_rows", []))

        st.session_state.setdefault("users_save_success", False)
        st.session_state.setdefault("users_pending_changes", False)
        st.session_state.setdefault("users_last_save_ts", 0.0)

        has_password_input = False
        if isinstance(editor_response, pd.DataFrame) and not editor_response.empty:
            has_password_input = (
                editor_response["New Password"].fillna("").str.strip().ne("").any()
                or editor_response["Confirm Password"].fillna("").str.strip().ne("").any()
            )

        has_changes = bool(edited_df or edited_cells or deleted_rows or added_rows or has_password_input)
        if has_changes:
            st.session_state["users_pending_changes"] = True
            st.session_state["users_save_success"] = False
        else:
            st.session_state["users_pending_changes"] = False
        pending_changes = st.session_state.get("users_pending_changes", False)

        cooldown_seconds = 10
        current_ts = time.time()
        last_save_ts = float(st.session_state.get("users_last_save_ts", 0.0) or 0.0)
        cooldown_remaining = max(0.0, cooldown_seconds - (current_ts - last_save_ts))

        if pending_changes and not st.session_state.get("users_save_success", False):
            st.info("You have unsaved user changes. Click 'Save Changes' to apply them.", icon="✏️")
        if cooldown_remaining > 0:
            st.warning(
                f"Please wait {cooldown_remaining:.0f} second(s) before saving again to avoid hitting Google Sheets limits.",
                icon="⏳",
            )

        action_cols = st.columns([1, 1], gap="small")
        with action_cols[0]:
            save_clicked = st.button(
                "Save Changes",
                type="primary",
                use_container_width=True,
                disabled=(not pending_changes) or (cooldown_remaining > 0),
                key="users_save_changes",
            )
        with action_cols[1]:
            discard_clicked = st.button(
                "Discard Changes",
                use_container_width=True,
                disabled=not pending_changes,
                key="users_discard_changes",
            )

        success = False
        messages: list[str] = []

        if discard_clicked and pending_changes:
            st.session_state.pop("users_table_view", None)
            st.session_state["users_pending_changes"] = False
            st.session_state["users_save_success"] = False
            st.rerun()

        if save_clicked and pending_changes:
            success = True
            st.session_state["users_save_success"] = False
            if cooldown_remaining > 0:
                st.warning("Please wait for the save cooldown before saving again.", icon="⏱️")
                success = False

            if added_rows:
                st.warning("Please use the 'Add User' tab to create new users.", icon="ℹ️")

            if deleted_rows and success:
                for delete_idx in sorted(deleted_rows, reverse=True):
                    try:
                        normalized_idx = int(delete_idx)
                    except (TypeError, ValueError):
                        normalized_idx = delete_idx
                    if isinstance(normalized_idx, int) and normalized_idx < len(base_df):
                        row = base_df.iloc[normalized_idx]
                        username_value = row.get("Username", "")
                        match_df = users_df[
                            users_df["Username"].astype(str).str.strip().str.lower()
                            == str(username_value).strip().lower()
                        ]
                        if not match_df.empty:
                            original_idx = int(match_df.index[0])
                            if delete_data(SHEETS["users"], original_idx):
                                messages.append(f"🗑️ User '{username_value}' deleted.")
                                users_df = users_df.drop(index=original_idx)
                            else:
                                st.error(f"Failed to delete user '{username_value}'.")
                                success = False
                        else:
                            st.error(f"Unable to locate user '{username_value}' for deletion.")
                            success = False
                    else:
                        st.error("Unable to resolve user row for deletion.")
                        success = False

            if success:
                rows_to_update: set[int] = set()
                for idx_key in list(edited_df.keys()) + list(edited_cells.keys()):
                    try:
                        norm_idx = int(idx_key)
                    except (TypeError, ValueError):
                        try:
                            norm_idx = int(str(idx_key))
                        except ValueError:
                            norm_idx = idx_key
                    if isinstance(norm_idx, int):
                        rows_to_update.add(norm_idx)

                if isinstance(editor_response, pd.DataFrame):
                    for idx, row in editor_response.reset_index(drop=True).iterrows():
                        if str(row.get("New Password", "")).strip() or str(row.get("Confirm Password", "")).strip():
                            rows_to_update.add(idx)

                for idx in sorted(rows_to_update):
                    if not isinstance(idx, int) or idx >= len(editor_response):
                        continue
                    current_row = editor_response.iloc[idx]
                    username_value = str(current_row.get("Username", "")).strip()
                    if not username_value:
                        continue

                    new_email = str(current_row.get("Email", "")).strip()
                    new_role = str(current_row.get("Role", "")).strip() or "user"
                    new_password = str(current_row.get("New Password", "")).strip()
                    confirm_password = str(current_row.get("Confirm Password", "")).strip()

                    if new_password or confirm_password:
                        if new_password != confirm_password:
                            st.error(f"Passwords do not match for user '{username_value}'.")
                            success = False
                            continue

                    match_df = users_df[
                        users_df["Username"].astype(str).str.strip().str.lower()
                        == username_value.lower()
                    ]
                    if match_df.empty:
                        st.error(f"Unable to locate user '{username_value}' for update.")
                        success = False
                        continue

                    original_idx = int(match_df.index[0])
                    hashed_password = match_df.iloc[0].get("Password", "")
                    if new_password:
                        hashed_password = hash_password(new_password)

                    updated_payload = [
                        username_value,
                        hashed_password,
                        new_email,
                        new_role,
                    ]

                    if update_data(SHEETS["users"], original_idx, updated_payload):
                        messages.append(f"✅ User '{username_value}' updated successfully!")
                        users_df.loc[original_idx, "Email"] = new_email
                        users_df.loc[original_idx, "Role"] = new_role
                        users_df.loc[original_idx, "Password"] = hashed_password
                    else:
                        st.error(f"Failed to update user '{username_value}'.")
                        success = False

            if success:
                st.session_state["users_save_success"] = True
                st.session_state["users_pending_changes"] = False
                st.session_state["users_last_save_ts"] = time.time()
                st.session_state.pop("users_table_view", None)
                st.session_state["user_success_message"] = (
                    " ".join(messages) if messages else "✅ User changes saved successfully!"
                )
                st.rerun()

