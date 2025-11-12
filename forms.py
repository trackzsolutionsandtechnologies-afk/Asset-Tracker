"""
Forms module for Asset Tracker
"""
import base64
from copy import deepcopy
from io import BytesIO
import re
import time
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Any, Dict, List, Optional
from google_sheets import read_data, append_data, update_data, delete_data, find_row, ensure_sheet_headers, get_worksheet
from google_drive import upload_file_to_drive
from google_oauth import get_drive_credentials, disconnect_drive_credentials

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
    retry_flag = "location_data_retry"
    if df.empty and not st.session_state.get(retry_flag, False):
        st.session_state[retry_flag] = True
        read_data.clear()
        st.rerun()
    if not df.empty and st.session_state.get(retry_flag):
        st.session_state.pop(retry_flag, None)
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
        if "location_success_message" in st.session_state:
            st.success(st.session_state["location_success_message"])
            del st.session_state["location_success_message"]
        
        if df.empty or "Location ID" not in df.columns:
            st.info("No locations found. Add a new location using the 'Add New Location' tab.")
            return

        user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
        is_admin = str(user_role).lower() == "admin"

        search_term = st.text_input(
            "🔍 Search Locations",
            placeholder="Search by Location ID or Name...",
            key="location_search",
        )

        filtered_df = df.copy()
        if search_term:
            search_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
            search_mask |= filtered_df["Location ID"].astype(str).str.contains(search_term, case=False, na=False)
            if "Location Name" in filtered_df.columns:
                search_mask |= filtered_df["Location Name"].astype(str).str.contains(search_term, case=False, na=False)
            filtered_df = filtered_df[search_mask]

            if filtered_df.empty:
                st.info(f"No locations found matching '{search_term}'.")
                return
            st.caption(f"Showing {len(filtered_df)} of {len(df)} location(s)")
        else:
            if filtered_df.empty:
                st.info("No locations found. Add a new location using the 'Add New Location' tab.")
                return

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
            </style>
            """,
            unsafe_allow_html=True,
        )

        table_df = filtered_df[["Location ID", "Location Name"]].copy()
        st.data_editor(
            table_df,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="location_table_view",
            column_config={
                "Location ID": st.column_config.TextColumn("Location ID", disabled=True),
                "Location Name": st.column_config.TextColumn("Location Name", help="Edit the name and save your changes."),
            },
        )

        editor_state = st.session_state.get("location_table_view", {})
        edited_rows = deepcopy(editor_state.get("edited_rows", {}))
        edited_cells = deepcopy(editor_state.get("edited_cells", {}))
        deleted_rows = list(editor_state.get("deleted_rows", []))
        added_rows = list(editor_state.get("added_rows", []))

        if deleted_rows and not is_admin:
            st.warning("Only administrators can delete locations. Deletions will be ignored.", icon="⚠️")
            deleted_rows = []
            if isinstance(editor_state, dict):
                editor_state["deleted_rows"] = []

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

        st.session_state.setdefault("location_pending_changes", False)
        st.session_state.setdefault("location_save_success", False)

        has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
        st.session_state["location_pending_changes"] = has_changes
        if has_changes:
            st.session_state["location_save_success"] = False

        action_cols = st.columns([1, 1], gap="small")
        with action_cols[0]:
            save_clicked = st.button(
                "Save Changes",
                type="primary",
                use_container_width=True,
                disabled=not has_changes,
                key="location_save_changes",
            )
        with action_cols[1]:
            discard_clicked = st.button(
                "Discard Changes",
                use_container_width=True,
                disabled=not has_changes,
                key="location_discard_changes",
            )

        if discard_clicked and has_changes:
            table_state = st.session_state.get("location_table_view")
            if isinstance(table_state, dict):
                table_state["edited_rows"] = {}
                table_state["edited_cells"] = {}
                table_state["deleted_rows"] = []
                table_state["added_rows"] = []
            st.session_state.pop("location_table_view", None)
            st.session_state["location_pending_changes"] = False
            st.rerun()

        if save_clicked and has_changes:
            success = True

            if added_rows:
                st.warning("Please add new locations from the 'Add New Location' tab.", icon="ℹ️")
                success = False

            if success and deleted_rows:
                for delete_idx in sorted([_normalize_idx(idx) for idx in deleted_rows], reverse=True):
                    if isinstance(delete_idx, int) and delete_idx < len(filtered_df):
                        target_row = filtered_df.iloc[delete_idx]
                        match_df = df[
                            df["Location ID"].astype(str).str.strip()
                            == str(target_row.get("Location ID", "")).strip()
                        ]
                        if not match_df.empty:
                            original_idx = int(match_df.index[0])
                            if delete_data(SHEETS["locations"], original_idx):
                                st.session_state["location_success_message"] = (
                                    f"🗑️ Location '{target_row.get('Location Name', '')}' "
                                    f"(ID: {target_row.get('Location ID', '')}) deleted."
                                )
                            else:
                                st.error("Failed to delete location.")
                                success = False
                        else:
                            st.error("Unable to find the selected location for deletion.")
                            success = False
                    else:
                        st.error("Unable to resolve the selected row for deletion.")
                        success = False

            rows_to_update: set[int] = set()
            for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                norm_idx = _normalize_idx(idx_key)
                if isinstance(norm_idx, int):
                    rows_to_update.add(norm_idx)

            if success and rows_to_update:
                for idx in rows_to_update:
                    if idx >= len(filtered_df):
                        continue
                    current_row = filtered_df.iloc[idx].copy()
                    edits = dict(_get_edits(edited_rows, idx))
                    cell_changes = _get_edits(edited_cells, idx)
                    if cell_changes:
                        edits.update(cell_changes)
                    if not edits:
                        continue

                    for column, new_value in edits.items():
                        current_row[column] = new_value

                    location_id_value = str(current_row.get("Location ID", "")).strip()
                    location_name_value = str(current_row.get("Location Name", "")).strip()

                    match_df = df[
                        df["Location ID"].astype(str).str.strip() == location_id_value
                    ]
                    if not match_df.empty:
                        original_idx = int(match_df.index[0])
                        column_order = list(df.columns) if not df.empty else expected_headers
                        updated_row = []
                        for col in column_order:
                            if col == "Location ID":
                                updated_row.append(location_id_value)
                            elif col == "Location Name":
                                updated_row.append(location_name_value)
                            else:
                                updated_row.append(match_df.iloc[0].get(col, ""))
                        if update_data(SHEETS["locations"], original_idx, updated_row):
                            st.session_state["location_success_message"] = (
                                f"✅ Location '{location_name_value}' (ID: {location_id_value}) updated successfully!"
                            )
                        else:
                            st.error(f"Failed to update location '{location_id_value}'.")
                            success = False
                    else:
                        st.error("Unable to locate the selected location for updating.")
                        success = False

            if success:
                st.session_state["location_pending_changes"] = False
                st.session_state["location_save_success"] = True
                if "location_search" in st.session_state:
                    del st.session_state["location_search"]
                st.session_state.pop("location_table_view", None)
                st.rerun()

        if (
            st.session_state.get("location_pending_changes", False)
            and not st.session_state.get("location_save_success", False)
        ):
            st.info("You have unsaved location changes. Click 'Save Changes' to apply them.", icon="✏️")

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

            if "depreciation_form_key" not in st.session_state:
                st.session_state["depreciation_form_key"] = 0

            form_key = st.session_state["depreciation_form_key"]

            with st.form(f"depreciation_form_{form_key}"):
                asset_labels = ["Select an asset"] + [option[0] for option in asset_options]
                selection = st.selectbox(
                    "Select Asset",
                    asset_labels,
                    help="Choose the asset to calculate depreciation for.",
                    key=f"depreciation_asset_{form_key}",
                )
                if selection == "Select an asset":
                    selected_asset_id = ""
                    asset_record = {}
                else:
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
                    key=f"depreciation_purchase_date_{form_key}",
                )
                purchase_cost_input = st.number_input(
                    "Purchase Cost",
                    min_value=0.0,
                    value=float(round(default_cost, 2)) if default_cost else 0.0,
                    step=0.01,
                    key=f"depreciation_purchase_cost_{form_key}",
                )
                useful_life_input = st.number_input(
                    "Useful Life (years)",
                    min_value=1,
                    value=5,
                    step=1,
                    key=f"depreciation_useful_life_{form_key}",
                )
                salvage_value_input = st.number_input(
                    "Salvage Value",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    key=f"depreciation_salvage_value_{form_key}",
                )
                st.selectbox(
                    "Depreciation Method",
                    ["Straight-Line"],
                    index=0,
                    help="Straight-line depreciation spreads cost evenly across years.",
                    key=f"depreciation_method_{form_key}",
                )

                submitted = st.form_submit_button(
                    "Calculate Depreciation", use_container_width=True, key=f"depreciation_submit_{form_key}"
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
                        st.session_state["depreciation_form_key"] += 1

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
                    st.session_state.pop("depreciation_form_key", None)
                    st.session_state.pop(state_key, None)
                    st.rerun()
                else:
                    st.error("Failed to save the schedule. Please try again.")

    with tab_view:
        if "depreciation_success_message" in st.session_state:
            st.success(st.session_state["depreciation_success_message"])
            del st.session_state["depreciation_success_message"]

        if depreciation_df.empty:
            st.info("No depreciation schedules found. Generate one to get started.")
            return

        user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
        is_admin = str(user_role).lower() == "admin"

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

        schedule_ids = filtered_df["Schedule ID"].dropna().astype(str).unique().tolist()
        schedule_filter_options = ["All Schedules"] + schedule_ids
        schedule_filter = st.selectbox("Filter by Schedule", schedule_filter_options)

        if schedule_filter != "All Schedules":
            filtered_df = filtered_df[filtered_df["Schedule ID"].astype(str) == schedule_filter]

        if filtered_df.empty:
            st.info("No schedules match the selected filters.")
            return

        st.caption(f"Showing {len(filtered_df)} depreciation row(s).")

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
            </style>
            """,
            unsafe_allow_html=True,
        )

        display_columns = [
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
        display_columns = [col for col in display_columns if col in filtered_df.columns]
        table_df = filtered_df[display_columns].copy()

        st.data_editor(
            table_df,
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="depreciation_table_view",
            column_config={
                "Schedule ID": st.column_config.TextColumn("Schedule ID", disabled=True),
                "Asset ID": st.column_config.TextColumn("Asset ID", disabled=True),
                "Asset Name": st.column_config.TextColumn("Asset Name", disabled=True),
                "Method": st.column_config.TextColumn("Method", disabled=True),
                "Generated On": st.column_config.TextColumn("Generated On", disabled=True),
                "Purchase Date": st.column_config.TextColumn(
                    "Purchase Date", help="Format: YYYY-MM-DD"
                ),
                "Purchase Cost": st.column_config.NumberColumn(
                    "Purchase Cost", format="%.2f", step=0.01
                ),
                "Useful Life (Years)": st.column_config.NumberColumn(
                    "Useful Life (Years)", min_value=1, step=1
                ),
                "Salvage Value": st.column_config.NumberColumn(
                    "Salvage Value", format="%.2f", step=0.01
                ),
                "Period End": st.column_config.TextColumn("Period End", help="Format: YYYY-MM-DD"),
                "Opening Value": st.column_config.NumberColumn(
                    "Opening Value", format="%.2f", step=0.01
                ),
                "Depreciation": st.column_config.NumberColumn(
                    "Depreciation", format="%.2f", step=0.01
                ),
                "Closing Value": st.column_config.NumberColumn(
                    "Closing Value", format="%.2f", step=0.01
                ),
            },
        )

        editor_state = st.session_state.get("depreciation_table_view", {})
        edited_rows = deepcopy(editor_state.get("edited_rows", {}))
        edited_cells = deepcopy(editor_state.get("edited_cells", {}))
        deleted_rows = list(editor_state.get("deleted_rows", []))
        added_rows = list(editor_state.get("added_rows", []))

        if deleted_rows and not is_admin:
            st.warning("Only administrators can delete depreciation schedules. Deletions will be ignored.", icon="⚠️")
            deleted_rows = []
            if isinstance(editor_state, dict):
                editor_state["deleted_rows"] = []

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

        st.session_state.setdefault("depreciation_pending_changes", False)
        st.session_state.setdefault("depreciation_save_success", False)

        has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
        st.session_state["depreciation_pending_changes"] = has_changes
        if has_changes:
            st.session_state["depreciation_save_success"] = False

        action_cols = st.columns([1, 1], gap="small")
        with action_cols[0]:
            save_clicked = st.button(
                "Save Changes",
                use_container_width=True,
                type="primary",
                disabled=not has_changes,
                key="depreciation_save_changes",
            )
        with action_cols[1]:
            discard_clicked = st.button(
                "Discard Changes",
                use_container_width=True,
                disabled=not has_changes,
                key="depreciation_discard_changes",
            )

        if discard_clicked and has_changes:
            table_state = st.session_state.get("depreciation_table_view")
            if isinstance(table_state, dict):
                table_state["edited_rows"] = {}
                table_state["edited_cells"] = {}
                table_state["deleted_rows"] = []
                table_state["added_rows"] = []
            st.session_state.pop("depreciation_table_view", None)
            st.session_state["depreciation_pending_changes"] = False
            st.rerun()

        if save_clicked and has_changes:
            success = True

            if added_rows:
                st.warning("Please generate new schedules from the 'Generate Schedule' tab.", icon="ℹ️")
                success = False

            if success and deleted_rows:
                for delete_idx in sorted([_normalize_idx(idx) for idx in deleted_rows], reverse=True):
                    if isinstance(delete_idx, int) and delete_idx < len(filtered_df):
                        target_row = filtered_df.iloc[delete_idx]
                        original_idx = int(filtered_df.index[delete_idx])
                        if delete_data(SHEETS["depreciation"], original_idx):
                            st.session_state["depreciation_success_message"] = (
                                f"🗑️ Schedule row for '{target_row.get('Schedule ID', '')}' removed."
                            )
                        else:
                            st.error("Failed to delete depreciation row.")
                            success = False
                    else:
                        st.error("Unable to resolve the selected row for deletion.")
                        success = False

            rows_to_update: set[int] = set()
            for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                norm_idx = _normalize_idx(idx_key)
                if isinstance(norm_idx, int):
                    rows_to_update.add(norm_idx)

            if success and rows_to_update:
                column_order = list(depreciation_df.columns)
                for idx in rows_to_update:
                    if idx >= len(filtered_df):
                        continue
                    current_row = filtered_df.iloc[idx].copy()
                    edits = dict(_get_edits(edited_rows, idx))
                    cell_changes = _get_edits(edited_cells, idx)
                    if cell_changes:
                        edits.update(cell_changes)
                    if not edits:
                        continue

                    for column, new_value in edits.items():
                        current_row[column] = new_value

                    update_map = {col: current_row.get(col, "") for col in column_order}

                    for numeric_col in [
                        "Purchase Cost",
                        "Useful Life (Years)",
                        "Salvage Value",
                        "Opening Value",
                        "Depreciation",
                        "Closing Value",
                    ]:
                        if numeric_col in update_map:
                            try:
                                update_map[numeric_col] = f"{float(str(update_map[numeric_col]).replace(',', '')):.2f}"
                            except Exception:
                                update_map[numeric_col] = str(update_map[numeric_col])

                    original_idx = int(filtered_df.index[idx])
                    updated_row = [update_map.get(col, "") for col in column_order]
                    if update_data(SHEETS["depreciation"], original_idx, updated_row):
                        st.session_state["depreciation_success_message"] = "✅ Depreciation data updated successfully!"
                    else:
                        st.error("Failed to update depreciation data.")
                        success = False

            if success:
                st.session_state["depreciation_pending_changes"] = False
                st.session_state["depreciation_save_success"] = True
                st.session_state.pop("depreciation_table_view", None)
                st.rerun()

        if (
            st.session_state.get("depreciation_pending_changes", False)
            and not st.session_state.get("depreciation_save_success", False)
        ):
            st.info("You have unsaved depreciation changes. Click 'Save Changes' to apply them.", icon="✏️")

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

    supplier_headers = ["Supplier ID", "Supplier Name"]
    _ensure_headers_once("suppliers", supplier_headers)

    suppliers_df = read_data(SHEETS["suppliers"])

    tab1, tab2 = st.tabs(["Add Supplier", "View / Edit Suppliers"])

    with tab1:
        if "supplier_success_message" in st.session_state:
            st.success(st.session_state["supplier_success_message"])
            del st.session_state["supplier_success_message"]

        if "supplier_form_key" not in st.session_state:
            st.session_state["supplier_form_key"] = 0
        form_key = st.session_state["supplier_form_key"]

        default_state = {
            "auto_generate": True,
            "supplier_id": generate_supplier_id(),
            "supplier_name": "",
        }

        if "supplier_form_state" not in st.session_state:
            st.session_state["supplier_form_state"] = default_state.copy()

        form_state = st.session_state["supplier_form_state"]
        form_state.setdefault("auto_generate", True)
        form_state.setdefault("supplier_id", generate_supplier_id())
        form_state.setdefault("supplier_name", "")

        st.markdown(
            f"""
            <style>
            div[data-testid="stForm"][aria-label="supplier_form_{form_key}"] {{
                background-color: #ffffff !important;
                padding: 1.5rem !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.form(f"supplier_form_{form_key}"):
            auto_generate = st.checkbox(
                "Auto-generate Supplier ID",
                value=form_state["auto_generate"],
                key=f"supplier_auto_{form_key}",
            )
            if auto_generate and not form_state["auto_generate"]:
                form_state["supplier_id"] = generate_supplier_id()
            if not auto_generate and form_state["auto_generate"]:
                form_state["supplier_id"] = ""
            form_state["auto_generate"] = auto_generate

            if auto_generate:
                supplier_id = st.text_input(
                    "Supplier ID *",
                    value=form_state.get("supplier_id", generate_supplier_id()),
                    disabled=True,
                    help="Auto-generated unique identifier",
                    key=f"supplier_id_auto_{form_key}",
                )
            else:
                supplier_id = st.text_input(
                    "Supplier ID *",
                    value=form_state.get("supplier_id", ""),
                    help="Unique identifier for the supplier",
                    key=f"supplier_id_manual_{form_key}",
                )
            form_state["supplier_id"] = supplier_id.strip()

            supplier_name = st.text_input(
                "Supplier Name *",
                value=form_state.get("supplier_name", ""),
                key=f"supplier_name_{form_key}",
            )
            form_state["supplier_name"] = supplier_name

            submitted = st.form_submit_button("Add Supplier", use_container_width=True, type="primary")

            if submitted:
                supplier_id_value = form_state["supplier_id"].strip()
                supplier_name_value = form_state["supplier_name"].strip()
                if not supplier_id_value or not supplier_name_value:
                    st.error("Please fill in all required fields.")
                elif (
                    not suppliers_df.empty
                    and "Supplier ID" in suppliers_df.columns
                    and supplier_id_value in suppliers_df["Supplier ID"].astype(str).values
                ):
                    st.error("Supplier ID already exists. Please enter a unique ID.")
                else:
                    with st.spinner("Adding supplier..."):
                        if append_data(SHEETS["suppliers"], [supplier_id_value, supplier_name_value]):
                            st.session_state["supplier_success_message"] = (
                                f"✅ Supplier '{supplier_name_value}' (ID: {supplier_id_value}) added successfully!"
                            )
                            st.session_state["supplier_form_state"] = default_state.copy()
                            st.session_state["supplier_form_state"]["supplier_id"] = generate_supplier_id()
                            st.session_state["supplier_form_key"] += 1
                            st.session_state.pop("supplier_search", None)
                            st.session_state.pop("supplier_table_view", None)
                            st.rerun()
                        else:
                            st.error("Failed to add supplier. Please try again.")

    with tab2:
        if "supplier_success_message" in st.session_state:
            st.success(st.session_state["supplier_success_message"])
            del st.session_state["supplier_success_message"]

        user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
        is_admin = str(user_role).lower() == "admin"

        if suppliers_df.empty or "Supplier ID" not in suppliers_df.columns:
            st.info("No suppliers found. Add a supplier using the 'Add Supplier' tab.")
            return

        search_term = st.text_input(
            "🔍 Search Suppliers",
            placeholder="Search by Supplier ID or Name...",
            key="supplier_search",
        ).strip()

        filtered_df = suppliers_df.copy()
        if search_term:
            mask = (
                filtered_df["Supplier ID"].astype(str).str.contains(search_term, case=False, na=False)
                | filtered_df["Supplier Name"].astype(str).str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]

        if filtered_df.empty:
            st.info("No suppliers match the current search. Try adjusting your search terms.")
            return

        st.caption(f"Showing {len(filtered_df)} of {len(suppliers_df)} supplier(s)")

        display_df = filtered_df[["Supplier ID", "Supplier Name"]].copy()

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
            </style>
            """,
            unsafe_allow_html=True,
        )

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

        editor_response = st.data_editor(
            display_df,
            hide_index=True,
            use_container_width=True,
            disabled=False,
            column_config={
                "Supplier ID": st.column_config.TextColumn("Supplier ID", disabled=True),
                "Supplier Name": st.column_config.TextColumn("Supplier Name", disabled=False),
            },
            num_rows="dynamic",
            key="supplier_table_view",
        )

        table_state = st.session_state.get("supplier_table_view")

        def _state_get(state_obj, attr: str, default):
            if state_obj is None:
                return default
            if isinstance(state_obj, dict):
                return deepcopy(state_obj.get(attr) or default)
            return deepcopy(getattr(state_obj, attr, default) or default)

        edited_rows = _state_get(table_state, "edited_rows", {})
        edited_cells = _state_get(table_state, "edited_cells", {})
        deleted_rows = _state_get(table_state, "deleted_rows", [])
        added_rows = _state_get(table_state, "added_rows", [])

        def _normalize_idx(idx_value):
            try:
                return int(idx_value)
            except (TypeError, ValueError):
                return idx_value

        def _get_edits(source_dict, idx_value):
            if not source_dict:
                return {}
            if idx_value in source_dict:
                return source_dict[idx_value]
            return source_dict.get(str(idx_value), {})

        st.session_state.setdefault("supplier_pending_changes", False)
        st.session_state.setdefault("supplier_save_success", False)

        has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
        st.session_state["supplier_pending_changes"] = has_changes
        if has_changes:
            st.session_state["supplier_save_success"] = False

        action_cols = st.columns([1, 1], gap="small")
        with action_cols[0]:
            save_clicked = st.button(
                "Save Changes",
                type="primary",
                use_container_width=True,
                disabled=not has_changes,
                key="supplier_save_changes",
            )
        with action_cols[1]:
            discard_clicked = st.button(
                "Discard Changes",
                use_container_width=True,
                disabled=not has_changes,
                key="supplier_discard_changes",
            )

        if discard_clicked and has_changes:
            if isinstance(table_state, dict):
                table_state["edited_rows"] = {}
                table_state["edited_cells"] = {}
                table_state["deleted_rows"] = []
                table_state["added_rows"] = []
            st.session_state.pop("supplier_table_view", None)
            st.session_state["supplier_pending_changes"] = False
            st.rerun()

        if save_clicked and has_changes:
            success = True
            success_messages: list[str] = []
            warning_messages: list[str] = []

            if added_rows:
                warning_messages.append(
                    "Adding suppliers from this view is not supported. Please use the 'Add Supplier' tab."
                )
                success = False

            if deleted_rows:
                if not is_admin:
                    warning_messages.append("Only administrators can delete suppliers.")
                    success = False
                else:
                    for delete_idx in sorted([_normalize_idx(idx) for idx in deleted_rows], reverse=True):
                        if isinstance(delete_idx, int) and delete_idx < len(filtered_df):
                            target_row = filtered_df.iloc[delete_idx]
                            supplier_id_value = str(target_row.get("Supplier ID", "")).strip()
                            match_df = suppliers_df[
                                suppliers_df["Supplier ID"].astype(str).str.strip() == supplier_id_value
                            ]
                            if not match_df.empty:
                                original_idx = int(match_df.index[0])
                                if delete_data(SHEETS["suppliers"], original_idx):
                                    success_messages.append(
                                        f"🗑️ Supplier '{target_row.get('Supplier Name', '')}' deleted."
                                    )
                                else:
                                    st.error("Failed to delete supplier.")
                                    success = False
                            else:
                                st.error("Unable to locate supplier for deletion.")
                                success = False
                        else:
                            st.error("Unable to resolve supplier row for deletion.")
                            success = False

            rows_to_update: set[int] = set()
            for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                norm_idx = _normalize_idx(idx_key)
                if isinstance(norm_idx, int):
                    rows_to_update.add(norm_idx)

            if success and rows_to_update:
                column_order = list(suppliers_df.columns)
                for idx in sorted(rows_to_update):
                    if idx >= len(filtered_df):
                        continue
                    current_row = filtered_df.iloc[idx].copy()
                    edits = dict(_get_edits(edited_rows, idx))
                    cell_changes = _get_edits(edited_cells, idx)
                    if cell_changes:
                        edits.update(cell_changes)
                    if not edits:
                        continue

                    for column, new_value in edits.items():
                        current_row[column] = new_value

                    supplier_id_value = str(current_row.get("Supplier ID", "")).strip()
                    supplier_name_value = str(current_row.get("Supplier Name", "")).strip()

                    if not supplier_id_value:
                        continue

                    match_df = suppliers_df[
                        suppliers_df["Supplier ID"].astype(str).str.strip() == supplier_id_value
                    ]
                    if match_df.empty:
                        st.error("Unable to locate supplier for update.")
                        success = False
                        continue

                    original_idx = int(match_df.index[0])
                    updated_row: list[str] = []
                    for column in column_order:
                        if column == "Supplier ID":
                            updated_row.append(supplier_id_value)
                        elif column == "Supplier Name":
                            updated_row.append(supplier_name_value)
                        else:
                            value = match_df.iloc[0].get(column, "")
                            if pd.isna(value):
                                value = ""
                            updated_row.append(str(value))

                    if update_data(SHEETS["suppliers"], original_idx, updated_row):
                        success_messages.append(f"✏️ Supplier '{supplier_id_value}' updated.")
                    else:
                        st.error(f"Failed to update supplier '{supplier_id_value}'.")
                        success = False

            if warning_messages:
                for msg in warning_messages:
                    st.warning(msg, icon="ℹ️")

            if success and success_messages:
                st.session_state["supplier_success_message"] = " ".join(success_messages)
                st.session_state["supplier_pending_changes"] = False
                st.session_state["supplier_save_success"] = True
                st.session_state.pop("supplier_table_view", None)
                st.session_state.pop("supplier_search", None)
                st.rerun()
            elif success and not success_messages:
                st.info("No changes were saved.")

        if st.session_state.get("supplier_pending_changes", False) and not st.session_state.get(
            "supplier_save_success", False
        ):
            st.info("You have unsaved supplier changes. Click 'Save Changes' to apply them.", icon="✏️")

def category_form():
    """Asset Category and Sub Category"""
    st.header("📂 Category Management")
    
    _ensure_headers_once("categories", ["Category ID", "Category Name"])
    _ensure_headers_once("subcategories", ["SubCategory ID", "Category ID", "SubCategory Name", "Category Name"])
    
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add Category", "Add Sub Category", "View/Edit Categories", "View/Edit Sub Categories"])
    
    with tab1:
        
        # Show success message if exists
        if "category_success_message" in st.session_state:
            st.success(st.session_state["category_success_message"])
            # Clear message after showing
            del st.session_state["category_success_message"]
        
        if "category_form_state" not in st.session_state:
            st.session_state["category_form_state"] = {
                "auto_generate": True,
                "category_id": generate_category_id(),
                "category_name": "",
            }
        form_state = st.session_state["category_form_state"]

        if "category_form_key" not in st.session_state:
            st.session_state["category_form_key"] = 0
        form_key = st.session_state["category_form_key"]

        form_id = f"category_form_{form_key}"
        auto_key = f"category_form_auto_generate_{form_key}"
        id_auto_key = f"category_form_category_id_auto_{form_key}"
        id_manual_key = f"category_form_category_id_manual_{form_key}"
        name_key = f"category_form_category_name_{form_key}"

        with st.form(form_id):
            auto_generate = st.checkbox(
                "Auto-generate Category ID",
                value=form_state["auto_generate"],
                key=auto_key,
            )
            if auto_generate:
                if not form_state["auto_generate"]:
                    form_state["category_id"] = generate_category_id()
                category_id = st.text_input(
                    "Category ID *",
                    value=form_state["category_id"],
                    disabled=True,
                    help="Auto-generated unique identifier",
                    key=id_auto_key,
                )
            else:
                category_id = st.text_input(
                    "Category ID *",
                    value="" if form_state["auto_generate"] else form_state["category_id"],
                    help="Unique identifier for the category",
                    key=id_manual_key,
                )
            category_name = st.text_input(
                "Category Name *",
                value=form_state["category_name"],
                key=name_key,
            )

            form_state["auto_generate"] = auto_generate
            form_state["category_id"] = category_id
            form_state["category_name"] = category_name
            
            submitted = st.form_submit_button("Add Category", use_container_width=True, type="primary")
            
            if submitted:
                if not category_id or not category_name:
                    st.error("Please fill in all required fields")
                elif not categories_df.empty and "Category ID" in categories_df.columns and category_id in categories_df["Category ID"].values:
                    st.error("Category ID already exists")
                else:
                    with st.spinner("Adding category..."):
                        if append_data(SHEETS["categories"], [category_id, category_name]):
                            st.session_state["category_success_message"] = (
                                f"✅ Category '{category_name}' (ID: {category_id}) added successfully!"
                            )
                            if "category_search" in st.session_state:
                                del st.session_state["category_search"]
                            st.session_state["category_form_state"] = {
                                "auto_generate": auto_generate,
                                "category_id": generate_category_id(),
                                "category_name": "",
                            }
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

        if "subcategory_form_key" not in st.session_state:
            st.session_state["subcategory_form_key"] = 0
        form_key = st.session_state["subcategory_form_key"]

        if "subcategory_form_state" not in st.session_state:
            st.session_state["subcategory_form_state"] = {
                "auto_generate": True,
                "subcategory_id": generate_subcategory_id(),
                "category_name": "Select category",
                "subcategory_name": "",
            }
        sub_form_state = st.session_state["subcategory_form_state"]

        if categories_df.empty:
            st.warning("Please add categories first before adding subcategories")
        else:
            category_names = ["Select category"] + categories_df["Category Name"].tolist()
            with st.form(f"subcategory_form_{form_key}"):
                selected_category_name = st.selectbox(
                    "Category *",
                    category_names,
                    index=category_names.index(sub_form_state["category_name"])
                    if sub_form_state["category_name"] in category_names
                    else 0,
                    key=f"subcategory_category_select_{form_key}",
                )

                if selected_category_name != "Select category":
                    category_id = categories_df[categories_df["Category Name"] == selected_category_name]["Category ID"].iloc[0]
                    category_name = selected_category_name
                else:
                    category_id = "Select category"
                    category_name = ""

                auto_generate = st.checkbox(
                    "Auto-generate Sub Category ID",
                    value=sub_form_state["auto_generate"],
                    key=f"subcategory_form_auto_generate_{form_key}",
                )
                if auto_generate:
                    if not sub_form_state["auto_generate"]:
                        sub_form_state["subcategory_id"] = generate_subcategory_id()
                    subcategory_id = st.text_input(
                        "Sub Category ID *",
                        value=sub_form_state["subcategory_id"],
                        disabled=True,
                        help="Auto-generated unique identifier",
                        key=f"subcategory_form_id_auto_{form_key}",
                    )
                else:
                    subcategory_id = st.text_input(
                        "Sub Category ID *",
                        value="" if sub_form_state["auto_generate"] else sub_form_state["subcategory_id"],
                        help="Unique identifier for the subcategory",
                        key=f"subcategory_form_id_manual_{form_key}",
                    )

                subcategory_name = st.text_input(
                    "Sub Category Name *",
                    value=sub_form_state["subcategory_name"],
                    key=f"subcategory_form_name_{form_key}",
                )

                normalized_category_name = (
                    selected_category_name
                    if selected_category_name in category_names and selected_category_name != "Select category"
                    else "Select category"
                )
                st.session_state["subcategory_form_state"].update(
                    {
                        "auto_generate": auto_generate,
                        "subcategory_id": subcategory_id,
                        "category_name": normalized_category_name,
                        "subcategory_name": subcategory_name,
                    }
                )

                submitted = st.form_submit_button("Add Sub Category", use_container_width=True, type="primary")

                if submitted:
                    if selected_category_name == "Select category" or not subcategory_id or not subcategory_name:
                        st.error("Please fill in all required fields")
                    elif not subcategories_df.empty and "SubCategory ID" in subcategories_df.columns and subcategory_id in subcategories_df["SubCategory ID"].values:
                        st.error("Sub Category ID already exists")
                        if auto_generate:
                            st.session_state["subcategory_form_state"].update(
                                {
                                    "subcategory_id": generate_subcategory_id(),
                                    "subcategory_name": "",
                                }
                            )
                    else:
                        with st.spinner("Adding sub category..."):
                            if append_data(SHEETS["subcategories"], [subcategory_id, category_id, subcategory_name, category_name]):
                                st.session_state["subcategory_success_message"] = (
                                    f"✅ Sub Category '{subcategory_name}' (ID: {subcategory_id}) added successfully!"
                                )
                                if "subcategory_search" in st.session_state:
                                    del st.session_state["subcategory_search"]
                                st.session_state["subcategory_form_state"] = {
                                    "auto_generate": True,
                                    "subcategory_id": generate_subcategory_id(),
                                    "category_name": "Select category",
                                    "subcategory_name": "",
                                }
                                st.session_state["subcategory_form_key"] += 1
                                st.rerun()
                            else:
                                st.error("Failed to add sub category")
    
    with tab3:
        if "category_success_message" in st.session_state:
            st.success(st.session_state["category_success_message"])
            del st.session_state["category_success_message"]
        
        if categories_df.empty or "Category ID" not in categories_df.columns:
            st.info("No categories found. Add a new category using the 'Add Category' tab.")
        else:
            search_term = st.text_input(
                "🔍 Search Categories",
                placeholder="Search by Category ID or Name...",
                key="category_search",
            )

            filtered_df = categories_df.copy()
            if search_term:
                mask = (
                    filtered_df["Category ID"].astype(str).str.contains(search_term, case=False, na=False)
                    | filtered_df["Category Name"].astype(str).str.contains(search_term, case=False, na=False)
                )
                filtered_df = filtered_df[mask]

                if filtered_df.empty:
                    st.info(f"No categories found matching '{search_term}'.")
                    return
                st.caption(f"Showing {len(filtered_df)} of {len(categories_df)} category(ies)")
            else:
                if filtered_df.empty:
                    st.info("No categories found. Add a new category using the 'Add Category' tab.")
                    return
                
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = str(user_role).lower() == "admin"

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
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                table_df = filtered_df[["Category ID", "Category Name"]].copy()
                st.data_editor(
                    table_df,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="category_table_view",
                    column_config={
                        "Category ID": st.column_config.TextColumn("Category ID", disabled=True),
                        "Category Name": st.column_config.TextColumn("Category Name"),
                    },
                )

                editor_state = st.session_state.get("category_table_view")
                if not isinstance(editor_state, dict):
                    editor_state = {}
                edited_rows = deepcopy(editor_state.get("edited_rows", {}))
                edited_cells = deepcopy(editor_state.get("edited_cells", {}))
                deleted_rows = list(editor_state.get("deleted_rows", []))
                added_rows = list(editor_state.get("added_rows", []))

                if deleted_rows and not is_admin:
                    st.warning("Only administrators can delete categories. Deletions will be ignored.", icon="⚠️")
                    deleted_rows = []
                    if isinstance(editor_state, dict):
                        editor_state["deleted_rows"] = []

                def _normalize_idx(idx_value):
                    try:
                        return int(idx_value)
                    except (TypeError, ValueError):
                        return idx_value

                def _get_edits(source_dict, idx_value):
                    if idx_value in source_dict:
                        return source_dict[idx_value]
                    return source_dict.get(str(idx_value), {})

                st.session_state.setdefault("category_pending_changes", False)
                st.session_state.setdefault("category_save_success", False)

                has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
                st.session_state["category_pending_changes"] = has_changes
                if has_changes:
                    st.session_state["category_save_success"] = False

                save_clicked = False
                discard_clicked = False

                action_cols = st.columns([1, 1], gap="small")
                with action_cols[0]:
                    save_clicked = st.button(
                        "Save Changes",
                        type="primary",
                        use_container_width=True,
                        disabled=not has_changes,
                        key="category_save_changes",
                    )
                with action_cols[1]:
                    discard_clicked = st.button(
                        "Discard Changes",
                        use_container_width=True,
                        disabled=not has_changes,
                        key="category_discard_changes",
                    )

        if "discard_clicked" in locals() and discard_clicked and has_changes:
            table_state = st.session_state.get("category_table_view")
            if isinstance(table_state, dict):
                table_state["edited_rows"] = {}
                table_state["edited_cells"] = {}
                table_state["deleted_rows"] = []
                table_state["added_rows"] = []
            st.session_state.pop("category_table_view", None)
            st.session_state["category_pending_changes"] = False
            st.rerun()

        if "save_clicked" in locals() and save_clicked and has_changes:
            success = True
            success_messages: list[str] = []

            if added_rows:
                st.warning(
                    "Please add new categories from the 'Add Category' tab.",
                    icon="ℹ️",
                )
                success = False

            if success and deleted_rows:
                for delete_idx in sorted([_normalize_idx(idx) for idx in deleted_rows], reverse=True):
                    if isinstance(delete_idx, int) and delete_idx < len(filtered_df):
                        target_row = filtered_df.iloc[delete_idx]
                        cat_id = str(target_row.get("Category ID", "")).strip()
                        match_df = categories_df[
                            categories_df["Category ID"].astype(str).str.strip() == cat_id
                        ]
                        if not match_df.empty:
                            original_idx = int(match_df.index[0])
                            if delete_data(SHEETS["categories"], original_idx):
                                success_messages.append(
                                    f"🗑️ Category '{target_row.get('Category Name', '')}' deleted."
                                )
                            else:
                                st.error("Failed to delete category.")
                                success = False
                        else:
                            st.error("Unable to locate category to delete.")
                            success = False
                    else:
                        st.error("Unable to resolve category row for deletion.")
                        success = False

            rows_to_update: set[int] = set()
            for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                norm_idx = _normalize_idx(idx_key)
                if isinstance(norm_idx, int):
                    rows_to_update.add(norm_idx)

            if success and rows_to_update:
                for idx in rows_to_update:
                    if idx >= len(filtered_df):
                        continue
                    current_row = filtered_df.iloc[idx].copy()
                    edits = dict(_get_edits(edited_rows, idx))
                    edits.update(_get_edits(edited_cells, idx))
                    if not edits:
                        continue

                    for column, new_value in edits.items():
                        current_row[column] = new_value

                    category_id_value = str(current_row.get("Category ID", "")).strip()
                    category_name_value = str(current_row.get("Category Name", "")).strip()
                    match_df = categories_df[
                        categories_df["Category ID"].astype(str).str.strip() == category_id_value
                    ]
                    if not match_df.empty:
                        original_idx = int(match_df.index[0])
                        updated_row = [category_id_value, category_name_value]
                        if update_data(SHEETS["categories"], original_idx, updated_row):
                            success_messages.append(
                                f"✏️ Category '{category_id_value}' updated."
                            )
                        else:
                            st.error(f"Failed to update category '{category_id_value}'.")
                            success = False
                    else:
                        st.error("Unable to locate category to update.")
                        success = False

            if success:
                if success_messages:
                    st.session_state["category_success_message"] = " ".join(success_messages)
                    if "category_search" in st.session_state:
                        del st.session_state["category_search"]
                st.session_state["category_pending_changes"] = False
                st.session_state["category_save_success"] = True
                st.session_state.pop("category_table_view", None)
                st.rerun()

        if (
            st.session_state.get("category_pending_changes", False)
            and not st.session_state.get("category_save_success", False)
        ):
            st.info("You have unsaved category changes. Click 'Save Changes' to apply them.", icon="✏️")
    
    with tab4:
        if "subcategory_success_message" in st.session_state:
            st.success(st.session_state["subcategory_success_message"])
            del st.session_state["subcategory_success_message"]
        
        if subcategories_df.empty or "SubCategory ID" not in subcategories_df.columns:
            st.info("No subcategories found. Add a new subcategory using the 'Add Sub Category' tab.")
        else:
            search_term = st.text_input(
                "🔍 Search Sub Categories",
                placeholder="Search by Sub Category ID, Name, Category ID, or Category Name...",
                key="subcategory_search",
            )

            filtered_df = subcategories_df.copy()
            if search_term:
                mask = (
                    filtered_df["SubCategory ID"].astype(str).str.contains(search_term, case=False, na=False)
                    | filtered_df["SubCategory Name"].astype(str).str.contains(search_term, case=False, na=False)
                    | filtered_df["Category ID"].astype(str).str.contains(search_term, case=False, na=False)
                )
                if "Category Name" in filtered_df.columns:
                    mask = mask | filtered_df["Category Name"].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = filtered_df[mask]

                if filtered_df.empty:
                    st.info(f"No subcategories found matching '{search_term}'.")
                    return
                st.caption(f"Showing {len(filtered_df)} of {len(subcategories_df)} subcategory(ies)")
            else:
                if filtered_df.empty:
                    st.info("No subcategories found. Add a new subcategory using the 'Add Sub Category' tab.")
                    return
                
                user_role = st.session_state.get(SESSION_KEYS.get("user_role", "user_role"), "user")
                is_admin = str(user_role).lower() == "admin"

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
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                table_df = filtered_df[
                    ["SubCategory ID", "Category ID", "Category Name", "SubCategory Name"]
                ].copy()

                st.data_editor(
                    table_df,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="subcategory_table_view",
                    column_config={
                        "SubCategory ID": st.column_config.TextColumn("Sub Category ID", disabled=True),
                        "Category ID": st.column_config.TextColumn("Category ID"),
                        "Category Name": st.column_config.TextColumn("Category Name"),
                        "SubCategory Name": st.column_config.TextColumn("Sub Category Name"),
                    },
                )

                editor_state = st.session_state.get("subcategory_table_view", {})
                edited_rows = deepcopy(editor_state.get("edited_rows", {}))
                edited_cells = deepcopy(editor_state.get("edited_cells", {}))
                deleted_rows = list(editor_state.get("deleted_rows", []))
                added_rows = list(editor_state.get("added_rows", []))

                if deleted_rows and not is_admin:
                    st.warning("Only administrators can delete subcategories. Deletions will be ignored.", icon="⚠️")
                    deleted_rows = []
                    if isinstance(editor_state, dict):
                        editor_state["deleted_rows"] = []

                def _normalize_idx(idx_value):
                    try:
                        return int(idx_value)
                    except (TypeError, ValueError):
                        return idx_value

                def _get_edits(source_dict, idx_value):
                    if idx_value in source_dict:
                        return source_dict[idx_value]
                    return source_dict.get(str(idx_value), {})

                st.session_state.setdefault("subcategory_pending_changes", False)
                st.session_state.setdefault("subcategory_save_success", False)

                has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
                st.session_state["subcategory_pending_changes"] = has_changes
                if has_changes:
                    st.session_state["subcategory_save_success"] = False

                action_cols = st.columns([1, 1], gap="small")
                with action_cols[0]:
                    save_clicked = st.button(
                        "Save Changes",
                        type="primary",
                        use_container_width=True,
                        disabled=not has_changes,
                        key="subcategory_save_changes",
                    )
                with action_cols[1]:
                    discard_clicked = st.button(
                        "Discard Changes",
                        use_container_width=True,
                        disabled=not has_changes,
                        key="subcategory_discard_changes",
                    )

                if discard_clicked and has_changes:
                    table_state = st.session_state.get("subcategory_table_view")
                    if isinstance(table_state, dict):
                        table_state["edited_rows"] = {}
                        table_state["edited_cells"] = {}
                        table_state["deleted_rows"] = []
                        table_state["added_rows"] = []
                    st.session_state.pop("subcategory_table_view", None)
                    st.session_state["subcategory_pending_changes"] = False
                    st.rerun()

                if save_clicked and has_changes:
                    success = True
                    success_messages: list[str] = []

                    if added_rows:
                        st.warning(
                            "Please add new subcategories from the 'Add Sub Category' tab.",
                            icon="ℹ️",
                        )
                        success = False

                    if success and deleted_rows:
                        for delete_idx in sorted([_normalize_idx(idx) for idx in deleted_rows], reverse=True):
                            if isinstance(delete_idx, int) and delete_idx < len(filtered_df):
                                target_row = filtered_df.iloc[delete_idx]
                                subcat_id = str(target_row.get("SubCategory ID", "")).strip()
                                match_df = subcategories_df[
                                    subcategories_df["SubCategory ID"].astype(str).str.strip() == subcat_id
                                ]
                                if not match_df.empty:
                                    original_idx = int(match_df.index[0])
                                    if delete_data(SHEETS["subcategories"], original_idx):
                                        success_messages.append(
                                            f"🗑️ Sub Category '{target_row.get('SubCategory Name', '')}' deleted."
                                        )
                                    else:
                                        st.error("Failed to delete subcategory.")
                                        success = False
                                else:
                                    st.error("Unable to locate subcategory to delete.")
                                    success = False
                            else:
                                st.error("Unable to resolve subcategory row for deletion.")
                                success = False

                    rows_to_update: set[int] = set()
                    for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                        norm_idx = _normalize_idx(idx_key)
                        if isinstance(norm_idx, int):
                            rows_to_update.add(norm_idx)

                    if success and rows_to_update:
                        for idx in rows_to_update:
                            if idx >= len(filtered_df):
                                continue
                            current_row = filtered_df.iloc[idx].copy()
                            edits = dict(_get_edits(edited_rows, idx))
                            edits.update(_get_edits(edited_cells, idx))
                            if not edits:
                                continue

                            for column, new_value in edits.items():
                                current_row[column] = new_value

                            subcat_id_value = str(current_row.get("SubCategory ID", "")).strip()
                            category_id_value = str(current_row.get("Category ID", "")).strip()
                            category_name_value = str(current_row.get("Category Name", "")).strip()
                            subcat_name_value = str(current_row.get("SubCategory Name", "")).strip()

                            match_df = subcategories_df[
                                subcategories_df["SubCategory ID"].astype(str).str.strip() == subcat_id_value
                            ]
                            if not match_df.empty:
                                original_idx = int(match_df.index[0])
                                updated_row = [
                                    subcat_id_value,
                                    category_id_value,
                                    subcat_name_value,
                                    category_name_value,
                                ]
                                if update_data(SHEETS["subcategories"], original_idx, updated_row):
                                    success_messages.append(
                                        f"✏️ Sub Category '{subcat_id_value}' updated."
                                    )
                                else:
                                    st.error(f"Failed to update subcategory '{subcat_id_value}'.")
                                    success = False
                            else:
                                st.error("Unable to locate subcategory to update.")
                                success = False

                    if success:
                        if success_messages:
                            st.session_state["subcategory_success_message"] = " ".join(success_messages)
                            if "subcategory_search" in st.session_state:
                                del st.session_state["subcategory_search"]
                        st.session_state["subcategory_pending_changes"] = False
                        st.session_state["subcategory_save_success"] = True
                        st.session_state.pop("subcategory_table_view", None)
                        st.rerun()

                if (
                    st.session_state.get("subcategory_pending_changes", False)
                    and not st.session_state.get("subcategory_save_success", False)
                ):
                    st.info(
                        "You have unsaved subcategory changes. Click 'Save Changes' to apply them.",
                        icon="✏️",
                    )

def generate_asset_id() -> str:
    """Generate a unique Asset ID/Barcode"""
    import uuid
    # Generate a short unique ID
    return f"AST-{uuid.uuid4().hex[:8].upper()}"

def asset_master_form():
    """Asset Master Form"""
    st.header("📦 Asset Master Management")
    
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
                    purchase_date_default = st.session_state.get(
                        asset_form_keys["purchase_date"], datetime.now().date()
                    )
                    purchase_date = st.date_input(
                        "Purchase Date",
                        value=purchase_date_default,
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
                            "Assigned",
                            "Maintenance",
                            "Disposed",
                        ],
                        key=asset_form_keys["status"],
                    )
                with fifth_cols[1]:
                    st.empty()
                with fifth_cols[2]:
                    st.empty()

                remarks = st.text_area("Remarks", key=asset_form_keys["remarks"])
                submitted = st.form_submit_button("Add Asset", use_container_width=True)

                if submitted:
                    if not asset_id or not asset_name:
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
                            "",
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

    with tab2:
        st.subheader("View / Edit Assets")
        if assets_df.empty:
            st.info("No assets found. Add assets using the 'Add New Asset' tab.")
        else:
            status_filter_options = ["All Status"] + sorted(
                {str(val).strip() for val in assets_df.get("Status", pd.Series()).dropna()}
            )
            location_filter_options = ["All Locations"] + sorted(
                {str(val).strip() for val in assets_df.get("Location", pd.Series()).dropna()}
            )
            condition_filter_options = ["All Conditions"] + sorted(
                {str(val).strip() for val in assets_df.get("Condition", pd.Series()).dropna()}
            )

            filter_cols = st.columns(3, gap="medium")
            with filter_cols[0]:
                selected_status_filter = st.selectbox(
                    "Filter by Status",
                    status_filter_options,
                    key="asset_status_filter",
                )
            with filter_cols[1]:
                selected_location_filter = st.selectbox(
                    "Filter by Location",
                    location_filter_options,
                    key="asset_location_filter",
                )
            with filter_cols[2]:
                selected_condition_filter = st.selectbox(
                    "Filter by Condition",
                    condition_filter_options,
                    key="asset_condition_filter",
                )

            search_term = st.text_input(
                "🔍 Search assets",
                placeholder="Search by Asset ID, Name, Category, or Assigned To...",
                key="asset_search",
            )

            filtered_df = assets_df.copy()
            if selected_status_filter != "All Status":
                filtered_df = filtered_df[
                    filtered_df.get("Status", "").astype(str).str.strip().str.lower()
                    == selected_status_filter.strip().lower()
                ]
            if selected_location_filter != "All Locations":
                filtered_df = filtered_df[
                    filtered_df.get("Location", "").astype(str).str.strip().str.lower()
                    == selected_location_filter.strip().lower()
                ]
            if selected_condition_filter != "All Conditions":
                filtered_df = filtered_df[
                    filtered_df.get("Condition", "").astype(str).str.strip().str.lower()
                    == selected_condition_filter.strip().lower()
                ]
            if search_term:
                term = search_term.strip().lower()
                filtered_df = filtered_df[
                    filtered_df.apply(
                        lambda row: term in " ".join(row.astype(str).str.lower()),
                        axis=1,
                    )
                ]

            if filtered_df.empty:
                st.info("No assets match the current filters.")
            else:
                save_result = st.session_state.pop("asset_save_result", None)
                if save_result:
                    updated_count = int(save_result.get("updated", 0) or 0)
                    failed_assets = save_result.get("failed") or []
                    missing_assets = save_result.get("missing") or []

                    if updated_count:
                        st.success(f"Saved {updated_count} asset record(s).")
                    if failed_assets:
                        asset_list = ", ".join(map(str, failed_assets))
                        st.error(f"Failed to update {len(failed_assets)} asset(s): {asset_list}.")
                    if missing_assets:
                        missing_list = ", ".join(map(str, missing_assets))
                        st.warning(
                            f"Unable to locate {len(missing_assets)} asset(s) while saving: {missing_list}."
                        )

                editor_columns = [
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
                ]
                available_columns = [col for col in editor_columns if col in filtered_df.columns]
                if not available_columns:
                    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
                else:
                    working_df = filtered_df.copy()
                    if "Purchase Cost" in available_columns:
                        working_df["Purchase Cost"] = pd.to_numeric(
                            working_df["Purchase Cost"].replace("", 0).astype(str).str.replace(",", ""),
                            errors="coerce",
                        ).fillna(0.0)
                    if "Purchase Date" in available_columns:
                        working_df["Purchase Date"] = pd.to_datetime(
                            working_df["Purchase Date"], errors="coerce"
                        ).dt.date

                    display_df = working_df[available_columns].copy()

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
                        [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Status"] div,
                        [data-testid="stDataEditor"] [role="gridcell"][data-columnid="Condition"] div {
                            border-radius: 20px;
                            padding: 0.1rem 0.65rem;
                            text-align: center;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    column_config: dict[str, st.column_config.BaseColumn] = {
                        "Asset ID": st.column_config.TextColumn("Asset ID", disabled=True),
                        "Purchase Date": st.column_config.DateColumn(
                            "Purchase Date", format="YYYY-MM-DD", disabled=False
                        ),
                        "Purchase Cost": st.column_config.NumberColumn(
                            "Purchase Cost", format="%.2f", step=0.01, disabled=False
                        ),
                        "Warranty": st.column_config.TextColumn("Warranty"),
                        "Condition": st.column_config.SelectboxColumn(
                            "Condition",
                            options=ASSET_CONDITION_OPTIONS,
                        ),
                        "Status": st.column_config.SelectboxColumn(
                            "Status",
                            options=ASSET_STATUS_OPTIONS,
                        ),
                    }

                    edited_df = st.data_editor(
                        display_df,
                        hide_index=True,
                        use_container_width=True,
                        disabled=False,
                        column_config=column_config,
                        num_rows="dynamic",
                        key="asset_table_editor",
                    )

                    editor_state = st.session_state.get("asset_table_editor")

                    def _state_get(state_obj, attr: str, default):
                        if state_obj is None:
                            return default
                        if isinstance(state_obj, dict):
                            return state_obj.get(attr) or default
                        return getattr(state_obj, attr, default) or default

                    edited_rows = _state_get(editor_state, "edited_rows", {})
                    edited_cells = _state_get(editor_state, "edited_cells", {})
                    deleted_rows = _state_get(editor_state, "deleted_rows", [])
                    added_rows = _state_get(editor_state, "added_rows", [])

                    def _normalize_idx(idx_value):
                        try:
                            return int(idx_value)
                        except (TypeError, ValueError):
                            return idx_value

                    def _get_edits(source_dict, idx_value):
                        if not source_dict:
                            return {}
                        if idx_value in source_dict:
                            return source_dict[idx_value]
                        return source_dict.get(str(idx_value), {})

                    has_changes = bool(edited_rows or edited_cells or deleted_rows or added_rows)
                    if not has_changes:
                        has_changes = not edited_df.equals(display_df)

                    st.session_state["asset_pending_changes"] = has_changes

                    button_cols = st.columns(2, gap="medium")
                    with button_cols[0]:
                        save_clicked = st.button(
                            "Save Changes",
                            type="primary",
                            use_container_width=True,
                            key="asset_save_button",
                            disabled=not has_changes,
                        )
                    with button_cols[1]:
                        discard_clicked = st.button(
                            "Discard Changes",
                            use_container_width=True,
                            key="asset_discard_button",
                            disabled=not has_changes,
                        )

                    if discard_clicked:
                        st.session_state.pop("asset_table_editor", None)
                        st.session_state["asset_pending_changes"] = False
                        st.rerun()

                    if save_clicked:
                        if not has_changes or edited_df.equals(display_df):
                            st.info("No changes detected.")
                        else:
                            if added_rows:
                                st.warning(
                                    "Adding new assets from this view is not supported. Please use the 'Add New Asset' tab.",
                                    icon="ℹ️",
                                )
                            if deleted_rows:
                                st.warning(
                                    "Deleting assets from this view is not supported yet.",
                                    icon="ℹ️",
                                )

                            editable_columns = [
                                col for col in editor_columns if col != "Asset ID" and col in assets_df.columns
                            ]
                            if not editable_columns or "Asset ID" not in assets_df.columns or "Asset ID" not in display_df.columns:
                                st.warning("Asset updates are unavailable because required columns are missing.")
                            else:
                                rows_to_update: set[int] = set()
                                for idx_key in list(edited_rows.keys()) + list(edited_cells.keys()):
                                    norm_idx = _normalize_idx(idx_key)
                                    if isinstance(norm_idx, int):
                                        rows_to_update.add(norm_idx)

                                if not rows_to_update:
                                    st.info("No changes were detected in editable columns.")
                                else:
                                    updates_applied = 0
                                    failed_updates: list[str] = []
                                    missing_assets: list[str] = []

                                    for idx in sorted(rows_to_update):
                                        if idx >= len(display_df):
                                            continue
                                        source_row = display_df.iloc[idx]
                                        asset_id_value = str(source_row.get("Asset ID", "")).strip()
                                        if not asset_id_value:
                                            continue

                                        match_rows = assets_df[
                                            assets_df["Asset ID"].astype(str).str.strip()
                                            == asset_id_value
                                        ]
                                        if match_rows.empty:
                                            missing_assets.append(asset_id_value)
                                            continue

                                        row_index = int(match_rows.index[0])
                                        updated_series = match_rows.iloc[0].copy()

                                        edits = dict(_get_edits(edited_rows, idx))
                                        cell_edits = _get_edits(edited_cells, idx)
                                        if cell_edits:
                                            edits.update(cell_edits)

                                        if not edits:
                                            continue

                                        for column, new_value in edits.items():
                                            if column not in editable_columns:
                                                continue
                                            value = new_value
                                            if isinstance(value, datetime):
                                                value = value.date()
                                            if isinstance(value, pd.Timestamp):
                                                value = value.date()
                                            updated_series.loc[column] = value

                                        column_order = list(assets_df.columns)
                                        row_data: list[Any] = []
                                        for column in column_order:
                                            val = updated_series.get(column, "")
                                            if isinstance(val, pd.Timestamp):
                                                val = val.date()
                                            if hasattr(val, "isoformat"):
                                                val = val.isoformat()
                                            if isinstance(val, float):
                                                val = round(val, 2)
                                            if pd.isna(val):
                                                val = ""
                                            row_data.append(val)

                                        if update_data(SHEETS["assets"], row_index, row_data):
                                            updates_applied += 1
                                        else:
                                            failed_updates.append(asset_id_value)

                                    if updates_applied or failed_updates or missing_assets:
                                        st.session_state["asset_save_result"] = {
                                            "updated": updates_applied,
                                            "failed": sorted(set(failed_updates)),
                                            "missing": sorted(set(missing_assets)),
                                        }
                                        if updates_applied and not failed_updates and not missing_assets:
                                            st.session_state.pop("asset_table_editor", None)
                                            st.session_state["asset_pending_changes"] = False
                                        else:
                                            st.session_state["asset_pending_changes"] = bool(
                                                failed_updates or missing_assets
                                            )
                                        st.rerun()
                                    else:
                                        st.info("No changes were saved.")

    with tab3:
        if assets_df.empty:
            st.info("No assets available for reporting.")
            return

        st.subheader("Asset Reports")

        status_filter_options = ["All Status"] + sorted(
            {str(val).strip() for val in assets_df.get("Status", pd.Series()).dropna()}
        )
        location_filter_options = ["All Locations"] + sorted(
            {str(val).strip() for val in assets_df.get("Location", pd.Series()).dropna()}
        )
        assigned_filter_options = ["All Assignees"] + sorted(
            {str(val).strip() for val in assets_df.get("Assigned To", pd.Series()).dropna()}
        )

        filter_cols = st.columns(3, gap="medium")
        with filter_cols[0]:
            report_status_filter = st.selectbox(
                "Filter by Status",
                status_filter_options,
                key="asset_report_status_filter",
            )
        with filter_cols[1]:
            report_location_filter = st.selectbox(
                "Filter by Location",
                location_filter_options,
                key="asset_report_location_filter",
            )
        with filter_cols[2]:
            report_assigned_filter = st.selectbox(
                "Filter by Assigned To",
                assigned_filter_options,
                key="asset_report_assigned_filter",
            )

        report_search_term = st.text_input(
            "🔍 Search assets in reports",
            placeholder="Search by Asset ID, Name, Category, or any column...",
            key="asset_report_search",
        )

        report_df = assets_df.copy()
        if report_status_filter != "All Status":
            report_df = report_df[
                report_df.get("Status", "").astype(str).str.strip().str.lower()
                == report_status_filter.strip().lower()
            ]
        if report_location_filter != "All Locations":
            report_df = report_df[
                report_df.get("Location", "").astype(str).str.strip().str.lower()
                == report_location_filter.strip().lower()
            ]
        if report_assigned_filter != "All Assignees":
            report_df = report_df[
                report_df.get("Assigned To", "").astype(str).str.strip().str.lower()
                == report_assigned_filter.strip().lower()
            ]
        if report_search_term:
            report_term = report_search_term.strip().lower()
            report_df = report_df[
                report_df.apply(
                    lambda row: report_term in " ".join(row.astype(str).str.lower()),
                    axis=1,
                )
            ]

        if report_df.empty:
            st.info("No assets match the current report filters.")
            return

        summary_df = (
            report_df.groupby("Status", dropna=False)["Asset ID"]
            .count()
            .reset_index()
            .rename(columns={"Asset ID": "Count"})
        )
        st.markdown("**Summary by Status**")
        st.dataframe(summary_df, hide_index=True, use_container_width=True)

        st.markdown("**Detailed Asset Report**")
        st.dataframe(report_df, hide_index=True, use_container_width=True)

        st.download_button(
            "Download filtered report (CSV)",
            data=report_df.to_csv(index=False).encode("utf-8"),
            file_name="asset_report.csv",
            mime="text/csv",
            key="download_asset_report_csv",
        )


def attachments_form():
    """Upload files to Google Drive and record the link in Google Sheets."""
    st.header("📎 Asset Attachments")
    attachment_headers = [
        "Timestamp",
        "Asset ID",
        "Asset Name",
        "File Name",
        "Drive URL",
        "Uploaded By",
        "Notes",
    ]
    _ensure_headers_once("attachments", attachment_headers)

    assets_df = read_data(SHEETS["assets"])
    attachments_df = read_data(SHEETS["attachments"])

    username = st.session_state.get(SESSION_KEYS.get("username", "username"), "default")
    user_key = str(username or "default")

    try:
        drive_creds = get_drive_credentials(user_key)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    if drive_creds is None:
        return

    st.markdown(
        "Upload supporting documents or photos for an asset."
    )

    tab_upload, tab_recent = st.tabs(["Upload Attachment", "Recent Attachments"])

    with tab_upload:
        if "attachment_success_message" in st.session_state:
            st.success(st.session_state["attachment_success_message"])
            del st.session_state["attachment_success_message"]

        form_key = st.session_state.setdefault("attachment_form_key", 0)
        asset_select_key = f"attachment_asset_select_{form_key}"
        file_key = f"attachment_file_{form_key}"
        notes_key = f"attachment_notes_{form_key}"

        form_css = f"""
        <style>
        div[data-testid="stForm"][aria-label="attachment_upload_form_{form_key}"] {{
            background-color: #ffffff !important;
            padding: 1.5rem !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        }}
        div[data-testid="stForm"][aria-label="attachment_upload_form_{form_key}"] label {{
            font-weight: 600 !important;
        }}
        </style>
        """
        st.markdown(form_css, unsafe_allow_html=True)

        with st.form(f"attachment_upload_form_{form_key}"):
            top_cols = st.columns([3, 2], gap="medium")
            if assets_df.empty:
                with top_cols[0]:
                    st.selectbox(
                        "Choose an asset *",
                        ["No assets available"],
                        key=asset_select_key,
                        disabled=True,
                    )
                    st.warning("No assets found. Attachments can only be uploaded once assets exist.")
                selected_option = ""
            else:
                asset_options = ["-- Select Asset --"] + [
                    f"{row.get('Asset ID', '').strip()} - {row.get('Asset Name', '').strip()}"
                    for _, row in assets_df.iterrows()
                    if str(row.get("Asset ID", "")).strip()
                ]
                with top_cols[0]:
                    selected_option = st.selectbox(
                        "Choose an asset *",
                        asset_options,
                        index=0,
                        key=asset_select_key,
                    )
            with top_cols[1]:
                uploaded_file = st.file_uploader(
                    "Attachment *",
                    type=["png", "jpg", "jpeg", "pdf", "doc", "docx", "xls", "xlsx"],
                    accept_multiple_files=False,
                    key=file_key,
                )

            add_notes = st.text_area(
                "Notes (optional)",
                placeholder="Describe the attachment...",
                key=notes_key,
            )

            submitted = st.form_submit_button(
                "Upload Attachment",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if assets_df.empty:
                st.error("Cannot upload attachments because no assets are available.")
                return
            if selected_option == "" or selected_option == "-- Select Asset --":
                st.error("Please choose an asset before uploading.")
                return
            if uploaded_file is None:
                st.error("Please choose a file to upload.")
                return

            file_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type or "application/octet-stream"
            parts = selected_option.split(" - ", 1)
            asset_id = parts[0].strip()
            asset_name = parts[1].strip() if len(parts) > 1 else ""
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            safe_asset = asset_id.replace(" ", "_")
            drive_filename = f"{safe_asset}_{timestamp}_{uploaded_file.name}"

            with st.spinner("Uploading to Google Drive..."):
                drive_file = upload_file_to_drive(
                    file_bytes,
                    drive_filename,
                    mime_type,
                    credentials=drive_creds,
                )

            if not drive_file:
                return

            drive_url = drive_file.get("webViewLink", "")
            uploaded_by = st.session_state.get(SESSION_KEYS.get("username", "username"), "Unknown")
            sheet_row = [
                datetime.utcnow().isoformat(),
                asset_id.strip(),
                asset_name.strip(),
                drive_file.get("name", uploaded_file.name),
                drive_url,
                uploaded_by,
                add_notes.strip() if add_notes else "",
            ]

            success = append_data(SHEETS["attachments"], sheet_row)
            if success:
                st.session_state["attachment_success_message"] = "Attachment uploaded successfully!"
                for state_key in (asset_select_key, file_key, notes_key):
                    st.session_state.pop(state_key, None)
                st.session_state["attachment_form_key"] = form_key + 1
                st.rerun()
            else:
                st.error("Failed to record attachment in Google Sheets.")

    with tab_recent:
        st.subheader("Recent Attachments")
        if attachments_df.empty:
            st.info("No attachments uploaded yet.")
        else:
            display_df = attachments_df.copy()
            if "Timestamp" in display_df.columns:
                display_df["Timestamp"] = pd.to_datetime(display_df["Timestamp"], errors="coerce")
                display_df = display_df.sort_values("Timestamp", ascending=False)
            display_df = display_df.head(50)

            search_query = st.text_input(
                "Search attachments",
                placeholder="Search by asset, file name, or notes...",
                key="attachments_search",
            )

            if search_query:
                q = search_query.strip().lower()
                def _row_matches(row):
                    for col in ("Asset ID", "Asset Name", "File Name", "Notes", "Uploaded By"):
                        if col in row and q in str(row[col]).lower():
                            return True
                    return False
                display_df = display_df[display_df.apply(_row_matches, axis=1)]

            augmented_df = _augment_attachments_display(display_df)
            for col in ("View", "Download"):
                if col in augmented_df.columns:
                    augmented_df[col] = augmented_df[col].astype(str)

            columns_to_show = [
                col
                for col in augmented_df.columns
                if col not in {"File Name", "Drive URL"}
            ]

            st.markdown(
                augmented_df[columns_to_show].to_html(escape=False, index=False),
                unsafe_allow_html=True,
            )

    st.button(
        "Disconnect Google Drive",
        on_click=disconnect_drive_credentials,
        args=(user_key,),
        key="disconnect_drive",
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

    def _get_sheet_cached(sheet_key: str, ttl_seconds: float = 20.0) -> pd.DataFrame:
        cache_key = f"cached_sheet_{sheet_key}"
        ts_key = f"{cache_key}_ts"
        current_ts = time.time()
        cached_df = st.session_state.get(cache_key)
        cached_ts = float(st.session_state.get(ts_key, 0.0) or 0.0)
        if cached_df is None or (current_ts - cached_ts) > ttl_seconds:
            st.session_state[cache_key] = read_data(SHEETS[sheet_key])
            st.session_state[ts_key] = current_ts
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

        default_service_date = datetime.now().date()
        default_supplier_option = supplier_options[0] if supplier_options else ""
        if default_supplier_option == "Select supplier":
            default_supplier_option = "Select supplier"

        default_form_state = {
            "auto_generate": True,
            "maintenance_id": generate_maintenance_id(),
            "asset_label": asset_option_labels[0],
            "asset_id_text": "",
            "maintenance_type": "Preventive",
            "service_date": default_service_date,
            "description": "",
            "cost": 0.0,
            "supplier_selection": default_supplier_option,
            "supplier_text": "",
            "next_due_date": default_service_date,
            "status": "Pending",
        }

        if "maintenance_form_state" not in st.session_state:
            st.session_state["maintenance_form_state"] = default_form_state.copy()

        form_state = st.session_state["maintenance_form_state"]
        form_state.setdefault("auto_generate", True)
        if form_state["auto_generate"] and not form_state.get("maintenance_id"):
            form_state["maintenance_id"] = generate_maintenance_id()
        form_state.setdefault("asset_label", asset_option_labels[0])
        if form_state["asset_label"] not in asset_option_labels:
            form_state["asset_label"] = asset_option_labels[0]
        form_state.setdefault("asset_id_text", "")
        form_state.setdefault("maintenance_type", "Preventive")
        form_state.setdefault("service_date", default_service_date)
        form_state.setdefault("description", "")
        form_state.setdefault("cost", 0.0)
        form_state.setdefault("supplier_selection", default_supplier_option)
        if supplier_options and form_state["supplier_selection"] not in supplier_options:
            form_state["supplier_selection"] = supplier_options[0]
        form_state.setdefault("supplier_text", "")
        form_state.setdefault("next_due_date", form_state["service_date"])
        form_state.setdefault("status", "Pending")

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
                value=form_state["auto_generate"],
                key=f"maintenance_auto_{form_key}",
            )
            if auto_generate and not form_state["auto_generate"]:
                form_state["maintenance_id"] = generate_maintenance_id()
            if not auto_generate and form_state["auto_generate"]:
                form_state["maintenance_id"] = ""
            form_state["auto_generate"] = auto_generate

            if auto_generate:
                maintenance_id = st.text_input(
                    "Maintenance ID *",
                    value=form_state.get("maintenance_id", generate_maintenance_id()),
                    disabled=True,
                    key=f"maintenance_id_{form_key}",
                )
            else:
                maintenance_id = st.text_input(
                    "Maintenance ID *",
                    value=form_state.get("maintenance_id", ""),
                    key=f"maintenance_manual_id_{form_key}",
                )
            form_state["maintenance_id"] = maintenance_id

            asset_col, type_col, date_col = st.columns(3, gap="medium")
            if len(asset_option_labels) > 1:
                with asset_col:
                    asset_index = (
                        asset_option_labels.index(form_state["asset_label"])
                        if form_state["asset_label"] in asset_option_labels
                        else 0
                    )
                    asset_label_selected = st.selectbox(
                        "Asset *",
                        asset_option_labels,
                        index=asset_index,
                        key=f"maintenance_asset_{form_key}",
                    )
                    asset_id = asset_label_to_id.get(asset_label_selected, "")
                    form_state["asset_label"] = asset_label_selected
                    form_state["asset_id_text"] = ""
            else:
                asset_label_selected = None
                with asset_col:
                    asset_id = st.text_input(
                        "Asset ID *",
                        value=form_state.get("asset_id_text", ""),
                        key=f"maintenance_asset_text_{form_key}",
                    )
                    st.warning("No assets found. Please add assets first.")
                    form_state["asset_id_text"] = asset_id
                    form_state["asset_label"] = asset_option_labels[0]

            with type_col:
                type_options = ["Preventive", "Breakdown", "Calibration"]
                type_index = (
                    type_options.index(form_state.get("maintenance_type", "Preventive"))
                    if form_state.get("maintenance_type", "Preventive") in type_options
                    else 0
                )
                maintenance_type = st.selectbox(
                    "Maintenance Type *",
                    type_options,
                    index=type_index,
                    key=f"maintenance_type_{form_key}",
                )
                form_state["maintenance_type"] = maintenance_type

            with date_col:
                service_date = st.date_input(
                    "Maintenance Date *",
                    value=form_state.get("service_date", default_service_date),
                    key=f"maintenance_service_{form_key}",
                )
                form_state["service_date"] = service_date

            description = st.text_area(
                "Description",
                value=form_state.get("description", ""),
                key=f"maintenance_description_{form_key}",
            )
            form_state["description"] = description

            cost_col, supplier_col, next_due_col = st.columns(3, gap="medium")
            with cost_col:
                cost = st.number_input(
                    "Cost",
                    min_value=0.0,
                    value=float(form_state.get("cost", 0.0) or 0.0),
                    step=0.01,
                    key=f"maintenance_cost_{form_key}",
                )
                form_state["cost"] = cost
            with supplier_col:
                if supplier_options:
                    supplier_index = (
                        supplier_options.index(form_state.get("supplier_selection", supplier_options[0]))
                        if form_state.get("supplier_selection", supplier_options[0]) in supplier_options
                        else 0
                    )
                    supplier_name = st.selectbox(
                        "Supplier",
                        supplier_options,
                        index=supplier_index,
                        key=f"maintenance_supplier_{form_key}",
                    )
                    form_state["supplier_selection"] = supplier_name
                    form_state["supplier_text"] = ""
                    supplier_value = "" if supplier_name in ("", "Select supplier") else supplier_name
                else:
                    supplier_name = st.text_input(
                        "Supplier",
                        value=form_state.get("supplier_text", ""),
                        key=f"maintenance_supplier_text_{form_key}",
                    )
                    form_state["supplier_text"] = supplier_name
                    form_state["supplier_selection"] = ""
                    supplier_value = supplier_name
            with next_due_col:
                next_due_date = st.date_input(
                    "Next Due Date",
                    value=form_state.get("next_due_date", form_state.get("service_date", default_service_date)),
                    key=f"maintenance_next_due_{form_key}",
                )
                form_state["next_due_date"] = next_due_date

            status_options = ["Pending", "In Progress", "Completed", "Disposed"]
            status_index = (
                status_options.index(form_state.get("status", "Pending"))
                if form_state.get("status", "Pending") in status_options
                else 0
            )
            maintenance_status = st.selectbox(
                "Status *",
                status_options,
                index=status_index,
                key=f"maintenance_status_{form_key}",
            )
            form_state["status"] = maintenance_status

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
                    if supplier_options and supplier_value == "":
                        st.error("Please select a Supplier")
                    else:
                        data_map = {
                            "Maintenance ID": maintenance_id,
                            "Asset ID": asset_id,
                            "Maintenance Type": maintenance_type,
                            "Maintenance Date": service_date.strftime("%Y-%m-%d"),
                            "Description": description,
                            "Cost": f"{cost:.2f}",
                            "Supplier": supplier_value,
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
                                if asset_status_col:
                                    if maintenance_status == "In Progress":
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id, "Maintenance")
                                    elif maintenance_status == "Completed":
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id, "Active")
                                    elif maintenance_status == "Disposed":
                                        _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id, "Disposed")
                                st.session_state["maintenance_success_message"] = (
                                    f"✅ Maintenance record '{maintenance_id}' added successfully!"
                                )
                                st.session_state.pop("cached_sheet_maintenance", None)
                                st.session_state.pop("cached_sheet_maintenance_ts", None)
                                st.session_state.pop("cached_sheet_assets", None)
                                st.session_state.pop("cached_sheet_assets_ts", None)
                                if "maintenance_search" in st.session_state:
                                    del st.session_state["maintenance_search"]
                                st.session_state["maintenance_form_state"] = default_form_state.copy()
                                st.session_state["maintenance_form_state"]["maintenance_id"] = generate_maintenance_id()
                                st.session_state["maintenance_form_state"]["service_date"] = default_service_date
                                st.session_state["maintenance_form_state"]["next_due_date"] = default_service_date
                                st.session_state["maintenance_form_key"] += 1
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
            status_filter_options = ["All Status"] + ["Pending", "In Progress", "Completed", "Disposed"]
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
                status_options_select = ["Pending", "In Progress", "Completed", "Disposed"]
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
                            options=["Pending", "In Progress", "Completed", "Disposed"],
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
                                    if asset_status_col:
                                        if update_map["Status"] == "In Progress":
                                            _update_asset_status_for_maintenance(
                                                assets_df, asset_status_col, update_map["Asset ID"], "Maintenance"
                                            )
                                        elif update_map["Status"] == "Completed":
                                            _update_asset_status_for_maintenance(
                                                assets_df, asset_status_col, update_map["Asset ID"], "Active"
                                            )
                                        elif update_map["Status"] == "Disposed":
                                            _update_asset_status_for_maintenance(
                                                assets_df, asset_status_col, update_map["Asset ID"], "Disposed"
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

                    status_choices = ["Pending", "In Progress", "Completed", "Disposed"]
                    status_new = st.selectbox(
                        "Status *",
                        status_choices,
                        index={
                            "pending": 0,
                            "in progress": 1,
                            "completed": 2,
                            "disposed": 3,
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
                                    if asset_status_col:
                                        if status_new == "In Progress":
                                            _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id_new, "Maintenance")
                                        elif status_new == "Completed":
                                            _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id_new, "Active")
                                        elif status_new == "Disposed":
                                            _update_asset_status_for_maintenance(assets_df, asset_status_col, asset_id_new, "Disposed")
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


def _extract_drive_file_id(url: str) -> str:
    if not url:
        return ""
    patterns = [
        r"/d/([a-zA-Z0-9_-]+)/",
        r"/d/([a-zA-Z0-9_-]+)$",
        r"id=([a-zA-Z0-9_-]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def _augment_attachments_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    view_links = []
    download_links = []

    for drive_url in result.get("Drive URL", []):
        file_id = _extract_drive_file_id(drive_url)
        if drive_url:
            view_links.append(
                f'<a href="{drive_url}" target="_blank">View</a>'
            )
        else:
            view_links.append("")

        if file_id:
            dl_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            download_links.append(
                f'<a href="{dl_url}" target="_blank">Download</a>'
            )
        else:
            download_links.append("")

    result["View"] = view_links
    result["Download"] = download_links
    return result

