"""Barcode utilities for scanning and printing."""

import base64
import io
from datetime import datetime

import barcode
import pandas as pd
import qrcode
import streamlit as st
import streamlit.components.v1 as components
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from streamlit_qrcode_scanner import qrcode_scanner
from config import SHEETS
from google_sheets import read_data, update_data

def generate_barcode_image(asset_id: str, format_type: str = "code128") -> Image.Image:
    """Generate a barcode image for an asset ID"""
    try:
        if format_type == "qr":
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(asset_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            return img
        else:
            # Generate Code128 barcode
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(asset_id, writer=ImageWriter())
            img = barcode_instance.render()
            return img
    except Exception as e:
        st.error(f"Error generating barcode: {str(e)}")
        return None

def barcode_scanner_page():
    """Display the streamlit-qrcode-scanner component and enable asset editing."""
    st.header("📸 Live Barcode Scanner")

    scanned_code = qrcode_scanner(key="live_barcode_scanner")
    if scanned_code:
        st.session_state["scanned_barcode"] = scanned_code
        st.success(f"Detected code: {scanned_code}")

    detected_code = st.session_state.get("scanned_barcode")
    if not detected_code:
        st.info("Point the camera at a barcode to scan and edit the matching asset.")
        return

    st.caption(f"Last scanned code: `{detected_code}`")

    assets_df = read_data(SHEETS["assets"])
    if assets_df.empty:
        st.warning("No assets found. Please add assets first.")
        return

    asset_id_col = next(
        (
            col
            for col in assets_df.columns
            if str(col).strip().lower()
            in {
                "asset id",
                "asset id / barcode",
                "asset id/barcode",
                "asset id barcode",
                "barcode",
            }
        ),
        None,
    )

    if not asset_id_col:
        st.error("Could not identify the Asset ID column in the Assets sheet.")
        return

    assets_df = assets_df.copy()
    assets_df[asset_id_col] = assets_df[asset_id_col].astype(str).str.strip()
    matches = assets_df[
        assets_df[asset_id_col].str.contains(detected_code.strip(), case=False, na=False)
    ]

    if matches.empty:
        st.warning("No matching assets found for this barcode.")
        if st.button("Clear scanned code", type="secondary"):
            st.session_state.pop("scanned_barcode", None)
            st.session_state.pop("edit_asset_index", None)
            st.rerun()
        return

    st.success(f"Found {len(matches)} asset(s) matching the scanned code.")

    for idx, asset_row in matches.iterrows():
        asset_id = asset_row.get(asset_id_col, "")
        asset_name = asset_row.get("Asset Name", "N/A")
        with st.expander(f"{asset_id} • {asset_name}", expanded=len(matches) == 1):
            st.write("**Asset Details**")
            for col, value in asset_row.items():
                st.write(f"- **{col}:** {value}")

            if st.button("Edit this asset", key=f"edit_asset_{idx}"):
                st.session_state["edit_asset_index"] = int(idx)
                st.rerun()

    if "edit_asset_index" not in st.session_state:
        if st.button("Clear scanned code", type="secondary"):
            st.session_state.pop("scanned_barcode", None)
            st.rerun()
        return

    edit_index = st.session_state["edit_asset_index"]
    if edit_index not in assets_df.index:
        st.session_state.pop("edit_asset_index", None)
        st.warning("The selected asset is no longer available.")
        return

    asset_series = assets_df.loc[edit_index].copy()
    asset_id_value = asset_series.get(asset_id_col, "")

    locations_df = read_data(SHEETS["locations"])
    suppliers_df = read_data(SHEETS["suppliers"])
    categories_df = read_data(SHEETS["categories"])
    subcategories_df = read_data(SHEETS["subcategories"])

    def _options(df: pd.DataFrame, column: str) -> list[str]:
        if df.empty or column not in df.columns:
            return []
        return sorted(
            {
                str(value).strip()
                for value in df[column].fillna("").astype(str)
                if value
            }
        )

    location_options = _options(locations_df, "Location Name")
    supplier_options = _options(suppliers_df, "Supplier Name")
    category_options = _options(categories_df, "Category Name")

    st.subheader(f"Edit Asset: {asset_id_value}")
    with st.form("edit_scanned_asset"):
        st.text_input("Asset ID", value=asset_id_value, disabled=True)
        asset_name = st.text_input(
            "Asset Name", value=str(asset_series.get("Asset Name", ""))
        )
        category = st.selectbox(
            "Category",
            ["Select category"] + category_options,
            index=(
                category_options.index(asset_series.get("Category", "")) + 1
                if asset_series.get("Category", "") in category_options
                else 0
            ),
        )

        if category != "Select category":
            if (
                not categories_df.empty
                and not subcategories_df.empty
                and "Category Name" in categories_df.columns
                and "Category ID" in categories_df.columns
            ):
                selected_cat = categories_df[
                    categories_df["Category Name"] == category
                ]
                if not selected_cat.empty and "Category ID" in subcategories_df.columns:
                    category_id = selected_cat["Category ID"].iloc[0]
                    subcat_options = _options(
                        subcategories_df[subcategories_df["Category ID"] == category_id],
                        "SubCategory Name",
                    )
                else:
                    subcat_options = []
            else:
                subcat_options = []
        else:
            subcat_options = []

        subcategory = st.selectbox(
            "Sub Category",
            ["None"] + subcat_options,
            index=(
                subcat_options.index(asset_series.get("Sub Category", "")) + 1
                if asset_series.get("Sub Category", "") in subcat_options
                else 0
            ),
        )

        location = st.selectbox(
            "Location",
            ["None"] + location_options,
            index=(
                location_options.index(asset_series.get("Location", "")) + 1
                if asset_series.get("Location", "") in location_options
                else 0
            ),
        )

        supplier = st.selectbox(
            "Supplier",
            ["None"] + supplier_options,
            index=(
                supplier_options.index(asset_series.get("Supplier", "")) + 1
                if asset_series.get("Supplier", "") in supplier_options
                else 0
            ),
        )

        assigned_to = st.text_input(
            "Assigned To", value=str(asset_series.get("Assigned To", ""))
        )
        condition = st.selectbox(
            "Condition",
            ["Excellent", "Good", "Fair", "Poor", "Damaged"],
            index={
                "Excellent": 0,
                "Good": 1,
                "Fair": 2,
                "Poor": 3,
                "Damaged": 4,
            }.get(str(asset_series.get("Condition", "Good")), 1),
        )

        status = st.selectbox(
            "Status",
            ["Active", "Inactive", "Maintenance", "Retired"],
            index={
                "Active": 0,
                "Inactive": 1,
                "Maintenance": 2,
                "Retired": 3,
            }.get(str(asset_series.get("Status", "Active")), 0),
        )

        model_serial = st.text_input(
            "Model / Serial No", value=str(asset_series.get("Model/Serial No", ""))
        )
        purchase_cost = st.number_input(
            "Purchase Cost",
            min_value=0.0,
            value=float(asset_series.get("Purchase Cost", 0) or 0),
            step=0.01,
        )

        purchase_date_raw = str(asset_series.get("Purchase Date", "") or "")
        if purchase_date_raw:
            try:
                purchase_date_default = datetime.strptime(
                    purchase_date_raw, "%Y-%m-%d"
                ).date()
            except Exception:
                purchase_date_default = datetime.today().date()
        else:
            purchase_date_default = datetime.today().date()
        purchase_date = st.date_input("Purchase Date", value=purchase_date_default)

        remarks = st.text_area(
            "Remarks", value=str(asset_series.get("Remarks", ""))
        )
        attachment = st.text_input(
            "Attachment URL", value=str(asset_series.get("Attachment", ""))
        )

        submitted = st.form_submit_button("Update Asset", type="primary")

    if submitted:
        if not asset_name.strip():
            st.error("Asset Name is required.")
            return

        asset_series["Asset Name"] = asset_name.strip()
        asset_series["Category"] = "" if category == "Select category" else category
        asset_series["Sub Category"] = "" if subcategory == "None" else subcategory
        asset_series["Location"] = "" if location == "None" else location
        asset_series["Supplier"] = "" if supplier == "None" else supplier
        asset_series["Assigned To"] = assigned_to.strip()
        asset_series["Condition"] = condition
        asset_series["Status"] = status
        asset_series["Model/Serial No"] = model_serial.strip()
        asset_series["Purchase Cost"] = purchase_cost
        asset_series["Purchase Date"] = purchase_date.strftime("%Y-%m-%d")
        asset_series["Remarks"] = remarks.strip()
        asset_series["Attachment"] = attachment.strip()

        def _sanitise(value):
            if isinstance(value, float) and pd.isna(value):
                return ""
            if pd.isna(value):
                return ""
            return value

        updated_row = [
            _sanitise(asset_series.get(col, "")) for col in assets_df.columns
        ]

        if update_data(SHEETS["assets"], int(edit_index), updated_row):
            st.success("Asset updated successfully.")
            st.session_state.pop("edit_asset_index", None)
            st.session_state.pop("scanned_barcode", None)
            st.rerun()
        else:
            st.error("Failed to update the asset. Please try again.")

    if st.button("Cancel editing", type="secondary"):
        st.session_state.pop("edit_asset_index", None)
        st.rerun()

def barcode_print_page():
    """Multiple barcode printing page"""
    st.header("🖨️ Print Multiple Barcodes")
    
    layout_bytes = st.session_state.get("barcode_layout_bytes")
    if st.button("Create Print Layout", use_container_width=True):
        if layout_bytes:
            encoded = base64.b64encode(layout_bytes).decode()
            components.html(
                f"""
                <script>
                (function() {{
                    const imageData = "data:image/png;base64,{encoded}";
                    const w = window.open("", "_blank");
                    if (w) {{
                        w.document.write('<html><head><title>Print Barcodes</title></head>' +
                                         '<body style="margin:0;display:flex;justify-content:center;align-items:center;background:#fff;">' +
                                         '<img src="' + imageData + '" style="width:100%;height:auto;" onload="window.print();window.onafterprint=function(){{window.close();}}" />' +
                                         '</body></html>');
                        w.document.close();
                    }} else {{
                        alert('Please allow pop-ups to print the barcode layout.');
                    }}
                }})();
                </script>
                """,
                height=0,
            )
        else:
            st.warning("Generate barcodes first to create a print layout.")

    assets_df = read_data(SHEETS["assets"])
    
    if assets_df.empty:
        st.warning("No assets found. Please add assets first.")
        return
    
    st.subheader("Select Assets to Print Barcodes")

    asset_id_col = None
    asset_name_col = None
    asset_location_col = None
    for col in assets_df.columns:
        col_norm = str(col).strip().lower()
        if col_norm in {"asset id", "asset id / barcode", "asset id/barcode", "asset id barcode", "assetid", "barcode"}:
            asset_id_col = col
        elif col_norm in {"asset name", "name"}:
            asset_name_col = col
        elif col_norm in {"location", "location name", "current location", "asset location"} and asset_location_col is None:
            asset_location_col = col
    if asset_id_col is None:
        st.error("Unable to identify the Asset ID column in the Assets sheet.")
        return

    assets_df = assets_df.copy()
    assets_df[asset_id_col] = assets_df[asset_id_col].astype(str).str.strip()
    if asset_name_col:
        assets_df[asset_name_col] = assets_df[asset_name_col].fillna("").astype(str).str.strip()
    else:
        assets_df["__asset_name_placeholder__"] = ""
        asset_name_col = "__asset_name_placeholder__"

    if asset_location_col:
        assets_df[asset_location_col] = assets_df[asset_location_col].fillna("").astype(str).str.strip()
        location_values = sorted(
            {loc for loc in assets_df[asset_location_col].tolist() if loc}
        )
    else:
        location_values = []

    location_choices = ["All Locations"] + location_values
    if "barcode_location_filter_prev" not in st.session_state:
        st.session_state["barcode_location_filter_prev"] = "All Locations"
    if "barcode_asset_selector" not in st.session_state:
        st.session_state["barcode_asset_selector"] = []

    previous_filter = st.session_state.get("barcode_location_filter_prev", "All Locations")
    try:
        default_index = location_choices.index(previous_filter)
    except ValueError:
        default_index = 0

    location_filter = st.selectbox(
        "Filter by Location",
        location_choices,
        index=default_index,
        help="Choose a location to narrow down the assets for barcode printing",
        key="barcode_location_filter",
    )

    filtered_assets_df = assets_df
    if asset_location_col and location_filter != "All Locations":
        filtered_assets_df = assets_df[
            assets_df[asset_location_col].str.lower() == location_filter.lower()
        ]

    asset_option_map: dict[str, tuple[str, str]] = {}
    asset_options: list[str] = []
    for _, row in filtered_assets_df.iterrows():
        asset_id_value = row[asset_id_col]
        asset_name_value = row[asset_name_col]
        label = asset_id_value if not asset_name_value else f"{asset_id_value} - {asset_name_value}"
        asset_options.append(label)
        asset_option_map[label] = (asset_id_value, asset_name_value)

    if location_filter != previous_filter:
        st.session_state["barcode_location_filter_prev"] = location_filter
        if location_filter == "All Locations":
            st.session_state["barcode_asset_selector"] = []
        else:
            st.session_state["barcode_asset_selector"] = asset_options.copy()

    selected_assets = st.multiselect(
        "Select Assets",
        asset_options,
        default=st.session_state.get("barcode_asset_selector", []),
        help="Select multiple assets to generate barcodes for printing",
        key="barcode_asset_selector",
    )

    previous_selection = st.session_state.get("barcode_layout_selection")
    if previous_selection is not None and selected_assets != previous_selection:
        st.session_state.pop("barcode_layout_bytes", None)
    st.session_state["barcode_layout_selection"] = selected_assets
    
    if selected_assets:
        selected_records = [asset_option_map[label] for label in selected_assets if label in asset_option_map]
        
        col1, col2 = st.columns(2)
        with col1:
            barcode_format = st.selectbox("Barcode Format", ["Code128", "QR Code"])
        with col2:
            barcodes_per_row = st.number_input("Barcodes per Row", min_value=1, max_value=5, value=2)
        
        if st.button("Generate Barcodes for Printing", use_container_width=True):
            # Generate barcodes
            barcode_images = []
            for asset_id, asset_name in selected_records:
                img = generate_barcode_image(asset_id, "qr" if barcode_format == "QR Code" else "code128")
                if img:
                    barcode_images.append((asset_id, asset_name, img))
            
            if barcode_images:
                st.success(f"Generated {len(barcode_images)} barcode(s)")
                
                # Display barcodes in grid
                st.subheader("Barcode Preview")
                num_barcodes = len(barcode_images)
                rows = (num_barcodes + barcodes_per_row - 1) // barcodes_per_row
                
                for row in range(rows):
                    cols = st.columns(barcodes_per_row)
                    for col_idx in range(barcodes_per_row):
                        idx = row * barcodes_per_row + col_idx
                        if idx < num_barcodes:
                            asset_id, asset_name, img = barcode_images[idx]
                            caption = asset_id if not asset_name else f"{asset_id} - {asset_name}"
                            with cols[col_idx]:
                                st.image(img, caption=caption, use_container_width=True)
                
                # Download option
                st.subheader("Download Barcodes")
                st.info("Right-click on each barcode image and select 'Save image as...' to download, or use the print function in your browser.")
                
                # Create a combined image for printing automatically
                img_width = 400
                img_height = 240
                combined_width = img_width * barcodes_per_row
                combined_height = img_height * rows
                
                combined_img = Image.new('RGB', (combined_width, combined_height), 'white')
                draw = ImageDraw.Draw(combined_img)
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None

                for idx, (asset_id, asset_name, img) in enumerate(barcode_images):
                    row = idx // barcodes_per_row
                    col = idx % barcodes_per_row
                    
                    # Resize image
                    img_resized = img.resize((img_width - 20, img_height - 80))
                    
                    # Paste image
                    x_offset = col * img_width + 10
                    y_offset = row * img_height + 20
                    combined_img.paste(img_resized, (x_offset, y_offset))

                    label_text = asset_id if not asset_name else f"{asset_id} - {asset_name}"
                    if font:
                        try:
                            bbox = draw.textbbox((0, 0), label_text, font=font)
                            text_width = bbox[2] - bbox[0]
                        except Exception:
                            text_width = 0
                    else:
                        text_width = 0
                    text_x = x_offset
                    if text_width:
                        text_x = x_offset + max((img_resized.width - text_width) // 2, 0)
                    text_y = y_offset + img_resized.height + 10
                    draw.text((text_x, text_y), label_text, fill="black", font=font)
                
                img_buffer = io.BytesIO()
                combined_img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                layout_bytes = img_buffer.getvalue()
                st.session_state["barcode_layout_bytes"] = layout_bytes

                st.image(combined_img, caption="Print Layout Preview", use_container_width=True)
                st.download_button(
                    label="Download Combined Barcode Sheet",
                    data=layout_bytes,
                    file_name="barcodes_print_sheet.png",
                    mime="image/png",
                    use_container_width=True,
                )

                encoded = base64.b64encode(layout_bytes).decode()
                st.markdown(
                    f'<a href="data:image/png;base64,{encoded}" target="_blank">Open Print Layout in New Tab</a>',
                    unsafe_allow_html=True,
                )
                st.info("Use the 'Create Print Layout' button at the top to open the printable view directly.")
