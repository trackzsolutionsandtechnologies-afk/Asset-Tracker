"""
Barcode utilities for scanning and printing
"""
import streamlit as st
import qrcode
from PIL import Image
import io
import pandas as pd
import barcode
from barcode.writer import ImageWriter
import uuid
from google_sheets import read_data, update_data
from config import SHEETS
import numpy as np
from datetime import datetime

# Try to import barcode scanning libraries
try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    try:
        import cv2
        CV2_AVAILABLE = True
    except ImportError:
        CV2_AVAILABLE = False

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

def decode_barcode_from_image(image):
    """Decode barcode from image"""
    try:
        if PYZBAR_AVAILABLE:
            # Convert PIL Image to numpy array
            img_array = np.array(image)
            # Decode barcodes
            decoded_objects = pyzbar_decode(img_array)
            if decoded_objects:
                # Return the first decoded barcode
                return decoded_objects[0].data.decode('utf-8')
        elif CV2_AVAILABLE:
            # Try using OpenCV with barcode detector
            import cv2
            img_array = np.array(image)
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            # Try to decode with OpenCV (basic implementation)
            # Note: OpenCV doesn't have built-in barcode decoder, so we'd need additional library
            pass
    except Exception as e:
        st.error(f"Error decoding barcode: {str(e)}")
    return None

def barcode_scanner_page():
    """Scan Barcode and search page"""
    st.header("🔍 Scan Barcode & Search")
    
    assets_df = read_data(SHEETS["assets"])
    
    if assets_df.empty:
        st.warning("No assets found. Please add assets first.")
        return
    
    tab1, tab2 = st.tabs(["Scan Barcode", "Search Asset"])
    
    with tab1:
        st.subheader("Scan Barcode")
        
        # Option to choose input method
        input_method = st.radio(
            "Input Method",
            ["📷 Camera Scan (Mobile)", "⌨️ Manual Entry"],
            horizontal=True,
            key="barcode_input_method"
        )
        
        scanned_barcode = None
        
        if input_method == "📷 Camera Scan (Mobile)":
            st.info("📱 Use your mobile device camera to scan a barcode. Make sure to grant camera permissions when prompted.")
            
            if not PYZBAR_AVAILABLE:
                st.warning("⚠️ Barcode scanning library (pyzbar) is not installed. Please install it using: `pip install pyzbar`")
                st.info("You can still use manual entry below.")
            else:
                camera_image = st.camera_input("Scan Barcode", key="barcode_camera")
                
                if camera_image:
                    # Convert camera image to PIL Image
                    img = Image.open(camera_image)
                    
                    # Try to decode barcode
                    with st.spinner("Decoding barcode..."):
                        decoded_barcode = decode_barcode_from_image(img)
                        
                        if decoded_barcode:
                            scanned_barcode = decoded_barcode
                            st.success(f"✅ Barcode scanned: {decoded_barcode}")
                            # Store in session state for persistence
                            st.session_state["scanned_barcode"] = decoded_barcode
                        else:
                            st.warning("⚠️ Could not decode barcode. Please try again or use manual entry.")
                            # Show the captured image for debugging
                            st.image(img, caption="Captured Image - Try scanning again", use_container_width=True)
        else:
            # Manual entry
            scanned_barcode = st.text_input(
                "Barcode / Asset ID", 
                value=st.session_state.get("scanned_barcode", ""),
                key="scanned_barcode_manual",
                help="Enter or paste the barcode/Asset ID"
            )
        
        # Use scanned barcode from session state if available
        if not scanned_barcode and "scanned_barcode" in st.session_state:
            scanned_barcode = st.session_state["scanned_barcode"]
        
        if scanned_barcode:
            # Search for asset
            matching_assets = assets_df[
                assets_df["Asset ID"].str.contains(scanned_barcode, case=False, na=False)
            ]
            
            if not matching_assets.empty:
                st.success(f"Found {len(matching_assets)} matching asset(s)")
                
                for idx, asset_row in matching_assets.iterrows():
                    asset_id = asset_row['Asset ID']
                    edit_key = f"edit_asset_{asset_id}_{idx}"
                    
                    with st.expander(f"Asset: {asset_id} - {asset_row.get('Asset Name', 'N/A')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write("**Asset Details:**")
                            st.write(f"**Asset ID:** {asset_id}")
                            st.write(f"**Asset Name:** {asset_row.get('Asset Name', 'N/A')}")
                            st.write(f"**Category:** {asset_row.get('Category', 'N/A')}")
                            st.write(f"**Sub Category:** {asset_row.get('Sub Category', 'N/A')}")
                            st.write(f"**Location:** {asset_row.get('Location', 'N/A')}")
                            st.write(f"**Status:** {asset_row.get('Status', 'N/A')}")
                            st.write(f"**Condition:** {asset_row.get('Condition', 'N/A')}")
                            st.write(f"**Assigned To:** {asset_row.get('Assigned To', 'N/A')}")
                            
                            # Edit button
                            if st.button("✏️ Edit Asset", key=edit_key, use_container_width=True):
                                st.session_state["edit_asset_id"] = asset_id
                                st.session_state["edit_asset_idx"] = int(idx)
                                st.rerun()
                        
                        with col2:
                            # Display barcode
                            barcode_img = generate_barcode_image(asset_id)
                            if barcode_img:
                                st.image(barcode_img, caption=f"Barcode: {asset_id}", use_container_width=True)
                
                # Show edit form if an asset is selected for editing
                if "edit_asset_id" in st.session_state and st.session_state["edit_asset_id"]:
                    edit_asset_id = st.session_state["edit_asset_id"]
                    edit_asset_idx = st.session_state.get("edit_asset_idx", 0)
                    
                    # Find the asset in the dataframe
                    asset_to_edit = assets_df[assets_df["Asset ID"] == edit_asset_id]
                    if not asset_to_edit.empty:
                        asset = asset_to_edit.iloc[0]
                        st.divider()
                        st.subheader(f"✏️ Edit Asset: {edit_asset_id}")
                        
                        # Load reference data
                        locations_df = read_data(SHEETS["locations"])
                        suppliers_df = read_data(SHEETS["suppliers"])
                        categories_df = read_data(SHEETS["categories"])
                        subcategories_df = read_data(SHEETS["subcategories"])
                        
                        with st.form("edit_asset_form_scanner"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Asset ID is read-only
                                st.text_input("Asset ID / Barcode", value=asset.get('Asset ID', ''), disabled=True)
                                asset_name = st.text_input("Asset Name *", value=asset.get('Asset Name', ''))
                                
                                # Category dropdown
                                if not categories_df.empty:
                                    category_options = categories_df["Category Name"].tolist()
                                    current_category = asset.get('Category', '')
                                    if current_category in category_options:
                                        default_cat_idx = category_options.index(current_category) + 1
                                    else:
                                        default_cat_idx = 0
                                    category = st.selectbox("Category *", ["Select category"] + category_options, index=default_cat_idx)
                                else:
                                    category = st.text_input("Category *", value=asset.get('Category', ''))
                                
                                # Sub Category dropdown
                                if category != "Select category" and not subcategories_df.empty and not categories_df.empty:
                                    category_id = categories_df[categories_df["Category Name"] == category]["Category ID"].iloc[0] if category in categories_df["Category Name"].values else None
                                    if category_id:
                                        subcat_options = subcategories_df[subcategories_df["Category ID"] == category_id]["SubCategory Name"].tolist()
                                        current_subcat = asset.get('Sub Category', '')
                                        if current_subcat in subcat_options:
                                            default_subcat_idx = subcat_options.index(current_subcat) + 1
                                        else:
                                            default_subcat_idx = 0
                                        subcategory = st.selectbox("Sub Category", ["None"] + subcat_options, index=default_subcat_idx)
                                    else:
                                        subcategory = st.text_input("Sub Category", value=asset.get('Sub Category', ''))
                                else:
                                    subcategory = st.text_input("Sub Category", value=asset.get('Sub Category', ''))
                                
                                model_serial = st.text_input("Model / Serial No", value=asset.get('Model/Serial No', ''))
                                
                                # Purchase Date
                                purchase_date_str = asset.get('Purchase Date', '')
                                if purchase_date_str:
                                    try:
                                        purchase_date = st.date_input("Purchase Date", value=datetime.strptime(purchase_date_str, "%Y-%m-%d").date())
                                    except:
                                        purchase_date = st.date_input("Purchase Date")
                                else:
                                    purchase_date = st.date_input("Purchase Date")
                            
                            with col2:
                                purchase_cost = st.number_input("Purchase Cost", min_value=0.0, value=float(asset.get('Purchase Cost', 0) or 0), step=0.01)
                                
                                # Supplier dropdown
                                if not suppliers_df.empty:
                                    supplier_options = suppliers_df["Supplier Name"].tolist()
                                    current_supplier = asset.get('Supplier', '')
                                    if current_supplier in supplier_options:
                                        default_supplier_idx = supplier_options.index(current_supplier) + 1
                                    else:
                                        default_supplier_idx = 0
                                    supplier = st.selectbox("Supplier", ["None"] + supplier_options, index=default_supplier_idx)
                                else:
                                    supplier = st.text_input("Supplier", value=asset.get('Supplier', ''))
                                
                                # Location dropdown
                                if not locations_df.empty:
                                    location_options = locations_df["Location Name"].tolist()
                                    current_location = asset.get('Location', '')
                                    if current_location in location_options:
                                        default_location_idx = location_options.index(current_location) + 1
                                    else:
                                        default_location_idx = 0
                                    location = st.selectbox("Location", ["None"] + location_options, index=default_location_idx)
                                else:
                                    location = st.text_input("Location", value=asset.get('Location', ''))
                                
                                assigned_to = st.text_input("Assigned To", value=asset.get('Assigned To', ''))
                                
                                # Condition dropdown
                                condition_options = ["Excellent", "Good", "Fair", "Poor", "Damaged"]
                                current_condition = asset.get('Condition', 'Good')
                                if current_condition in condition_options:
                                    default_condition_idx = condition_options.index(current_condition)
                                else:
                                    default_condition_idx = 1
                                condition = st.selectbox("Condition", condition_options, index=default_condition_idx)
                                
                                # Status dropdown
                                status_options = ["Active", "Inactive", "Maintenance", "Retired"]
                                current_status = asset.get('Status', 'Active')
                                if current_status in status_options:
                                    default_status_idx = status_options.index(current_status)
                                else:
                                    default_status_idx = 0
                                status = st.selectbox("Status", status_options, index=default_status_idx)
                                
                                remarks = st.text_area("Remarks", value=asset.get('Remarks', ''))
                                attachment = st.text_input("Attachment URL", value=asset.get('Attachment', ''))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Update Asset", use_container_width=True, type="primary"):
                                    if not asset_name:
                                        st.error("Asset Name is required")
                                    else:
                                        # Prepare data for update
                                        data = [
                                            asset_id, asset_name, category if category != "Select category" else "",
                                            subcategory if subcategory != "None" else "", model_serial,
                                            purchase_date.strftime("%Y-%m-%d") if purchase_date else "",
                                            purchase_cost, supplier if supplier != "None" else "",
                                            location if location != "None" else "", assigned_to,
                                            condition, status, remarks, attachment
                                        ]
                                        
                                        # Get the original row index from the full assets_df
                                        original_row = assets_df[assets_df["Asset ID"] == edit_asset_id]
                                        if not original_row.empty:
                                            original_idx = int(original_row.index[0])
                                            
                                            with st.spinner("Updating asset..."):
                                                if update_data(SHEETS["assets"], original_idx, data):
                                                    st.success(f"✅ Asset '{asset_name}' (ID: {edit_asset_id}) updated successfully!")
                                                    # Clear edit state
                                                    if "edit_asset_id" in st.session_state:
                                                        del st.session_state["edit_asset_id"]
                                                    if "edit_asset_idx" in st.session_state:
                                                        del st.session_state["edit_asset_idx"]
                                                    # Clear scanned barcode to refresh
                                                    if "scanned_barcode" in st.session_state:
                                                        del st.session_state["scanned_barcode"]
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to update asset")
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    if "edit_asset_id" in st.session_state:
                                        del st.session_state["edit_asset_id"]
                                    if "edit_asset_idx" in st.session_state:
                                        del st.session_state["edit_asset_idx"]
                                    st.rerun()
                    else:
                        st.warning("Selected asset not found in data.")
            else:
                st.error("No asset found with this barcode/ID")
    
    with tab2:
        st.subheader("Search Asset")
        
        search_options = ["Asset ID", "Asset Name", "Category", "Location", "Status"]
        search_by = st.selectbox("Search By", search_options)
        search_term = st.text_input("Search Term")
        
        if search_term:
            if search_by == "Asset ID":
                results = assets_df[assets_df["Asset ID"].str.contains(search_term, case=False, na=False)]
            elif search_by == "Asset Name":
                results = assets_df[assets_df["Asset Name"].str.contains(search_term, case=False, na=False)]
            elif search_by == "Category":
                results = assets_df[assets_df["Category"].str.contains(search_term, case=False, na=False)]
            elif search_by == "Location":
                results = assets_df[assets_df["Location"].str.contains(search_term, case=False, na=False)]
            elif search_by == "Status":
                results = assets_df[assets_df["Status"].str.contains(search_term, case=False, na=False)]
            else:
                results = pd.DataFrame()
            
            if not results.empty:
                st.success(f"Found {len(results)} matching asset(s)")
                
                # Display results with edit option
                for idx, asset_row in results.iterrows():
                    asset_id = asset_row['Asset ID']
                    edit_key_search = f"edit_asset_search_{asset_id}_{idx}"
                    
                    with st.expander(f"Asset: {asset_id} - {asset_row.get('Asset Name', 'N/A')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write("**Asset Details:**")
                            st.write(f"**Asset ID:** {asset_id}")
                            st.write(f"**Asset Name:** {asset_row.get('Asset Name', 'N/A')}")
                            st.write(f"**Category:** {asset_row.get('Category', 'N/A')}")
                            st.write(f"**Sub Category:** {asset_row.get('Sub Category', 'N/A')}")
                            st.write(f"**Location:** {asset_row.get('Location', 'N/A')}")
                            st.write(f"**Status:** {asset_row.get('Status', 'N/A')}")
                            st.write(f"**Condition:** {asset_row.get('Condition', 'N/A')}")
                            st.write(f"**Assigned To:** {asset_row.get('Assigned To', 'N/A')}")
                            
                            # Edit button
                            if st.button("✏️ Edit Asset", key=edit_key_search, use_container_width=True):
                                st.session_state["edit_asset_id"] = asset_id
                                st.session_state["edit_asset_idx"] = int(idx)
                                st.rerun()
                        
                        with col2:
                            # Display barcode
                            barcode_img = generate_barcode_image(asset_id)
                            if barcode_img:
                                st.image(barcode_img, caption=f"Barcode: {asset_id}", use_container_width=True)
                
                # Show edit form if an asset is selected for editing (same form as in scan tab)
                if "edit_asset_id" in st.session_state and st.session_state["edit_asset_id"]:
                    edit_asset_id = st.session_state["edit_asset_id"]
                    edit_asset_idx = st.session_state.get("edit_asset_idx", 0)
                    
                    # Find the asset in the full assets_df
                    asset_to_edit = assets_df[assets_df["Asset ID"] == edit_asset_id]
                    if not asset_to_edit.empty:
                        asset = asset_to_edit.iloc[0]
                        st.divider()
                        st.subheader(f"✏️ Edit Asset: {edit_asset_id}")
                        
                        # Load reference data
                        locations_df = read_data(SHEETS["locations"])
                        suppliers_df = read_data(SHEETS["suppliers"])
                        categories_df = read_data(SHEETS["categories"])
                        subcategories_df = read_data(SHEETS["subcategories"])
                        
                        with st.form("edit_asset_form_search"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Asset ID is read-only
                                st.text_input("Asset ID / Barcode", value=asset.get('Asset ID', ''), disabled=True)
                                asset_name = st.text_input("Asset Name *", value=asset.get('Asset Name', ''))
                                
                                # Category dropdown
                                if not categories_df.empty:
                                    category_options = categories_df["Category Name"].tolist()
                                    current_category = asset.get('Category', '')
                                    if current_category in category_options:
                                        default_cat_idx = category_options.index(current_category) + 1
                                    else:
                                        default_cat_idx = 0
                                    category = st.selectbox("Category *", ["Select category"] + category_options, index=default_cat_idx)
                                else:
                                    category = st.text_input("Category *", value=asset.get('Category', ''))
                                
                                # Sub Category dropdown
                                if category != "Select category" and not subcategories_df.empty and not categories_df.empty:
                                    category_id = categories_df[categories_df["Category Name"] == category]["Category ID"].iloc[0] if category in categories_df["Category Name"].values else None
                                    if category_id:
                                        subcat_options = subcategories_df[subcategories_df["Category ID"] == category_id]["SubCategory Name"].tolist()
                                        current_subcat = asset.get('Sub Category', '')
                                        if current_subcat in subcat_options:
                                            default_subcat_idx = subcat_options.index(current_subcat) + 1
                                        else:
                                            default_subcat_idx = 0
                                        subcategory = st.selectbox("Sub Category", ["None"] + subcat_options, index=default_subcat_idx)
                                    else:
                                        subcategory = st.text_input("Sub Category", value=asset.get('Sub Category', ''))
                                else:
                                    subcategory = st.text_input("Sub Category", value=asset.get('Sub Category', ''))
                                
                                model_serial = st.text_input("Model / Serial No", value=asset.get('Model/Serial No', ''))
                                
                                # Purchase Date
                                purchase_date_str = asset.get('Purchase Date', '')
                                if purchase_date_str:
                                    try:
                                        purchase_date = st.date_input("Purchase Date", value=datetime.strptime(purchase_date_str, "%Y-%m-%d").date())
                                    except:
                                        purchase_date = st.date_input("Purchase Date")
                                else:
                                    purchase_date = st.date_input("Purchase Date")
                            
                            with col2:
                                purchase_cost = st.number_input("Purchase Cost", min_value=0.0, value=float(asset.get('Purchase Cost', 0) or 0), step=0.01)
                                
                                # Supplier dropdown
                                if not suppliers_df.empty:
                                    supplier_options = suppliers_df["Supplier Name"].tolist()
                                    current_supplier = asset.get('Supplier', '')
                                    if current_supplier in supplier_options:
                                        default_supplier_idx = supplier_options.index(current_supplier) + 1
                                    else:
                                        default_supplier_idx = 0
                                    supplier = st.selectbox("Supplier", ["None"] + supplier_options, index=default_supplier_idx)
                                else:
                                    supplier = st.text_input("Supplier", value=asset.get('Supplier', ''))
                                
                                # Location dropdown
                                if not locations_df.empty:
                                    location_options = locations_df["Location Name"].tolist()
                                    current_location = asset.get('Location', '')
                                    if current_location in location_options:
                                        default_location_idx = location_options.index(current_location) + 1
                                    else:
                                        default_location_idx = 0
                                    location = st.selectbox("Location", ["None"] + location_options, index=default_location_idx)
                                else:
                                    location = st.text_input("Location", value=asset.get('Location', ''))
                                
                                assigned_to = st.text_input("Assigned To", value=asset.get('Assigned To', ''))
                                
                                # Condition dropdown
                                condition_options = ["Excellent", "Good", "Fair", "Poor", "Damaged"]
                                current_condition = asset.get('Condition', 'Good')
                                if current_condition in condition_options:
                                    default_condition_idx = condition_options.index(current_condition)
                                else:
                                    default_condition_idx = 1
                                condition = st.selectbox("Condition", condition_options, index=default_condition_idx)
                                
                                # Status dropdown
                                status_options = ["Active", "Inactive", "Maintenance", "Retired"]
                                current_status = asset.get('Status', 'Active')
                                if current_status in status_options:
                                    default_status_idx = status_options.index(current_status)
                                else:
                                    default_status_idx = 0
                                status = st.selectbox("Status", status_options, index=default_status_idx)
                                
                                remarks = st.text_area("Remarks", value=asset.get('Remarks', ''))
                                attachment = st.text_input("Attachment URL", value=asset.get('Attachment', ''))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Update Asset", use_container_width=True, type="primary"):
                                    if not asset_name:
                                        st.error("Asset Name is required")
                                    else:
                                        # Prepare data for update
                                        data = [
                                            edit_asset_id, asset_name, category if category != "Select category" else "",
                                            subcategory if subcategory != "None" else "", model_serial,
                                            purchase_date.strftime("%Y-%m-%d") if purchase_date else "",
                                            purchase_cost, supplier if supplier != "None" else "",
                                            location if location != "None" else "", assigned_to,
                                            condition, status, remarks, attachment
                                        ]
                                        
                                        # Get the original row index from the full assets_df
                                        original_row = assets_df[assets_df["Asset ID"] == edit_asset_id]
                                        if not original_row.empty:
                                            original_idx = int(original_row.index[0])
                                            
                                            with st.spinner("Updating asset..."):
                                                if update_data(SHEETS["assets"], original_idx, data):
                                                    st.success(f"✅ Asset '{asset_name}' (ID: {edit_asset_id}) updated successfully!")
                                                    # Clear edit state
                                                    if "edit_asset_id" in st.session_state:
                                                        del st.session_state["edit_asset_id"]
                                                    if "edit_asset_idx" in st.session_state:
                                                        del st.session_state["edit_asset_idx"]
                                                    # Clear search to refresh
                                                    if "search_term" in st.session_state:
                                                        del st.session_state["search_term"]
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to update asset")
                            with col2:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    if "edit_asset_id" in st.session_state:
                                        del st.session_state["edit_asset_id"]
                                    if "edit_asset_idx" in st.session_state:
                                        del st.session_state["edit_asset_idx"]
                                    st.rerun()
                    else:
                        st.warning("Selected asset not found in data.")
            else:
                st.info("No matching assets found")

def barcode_print_page():
    """Multiple barcode printing page"""
    st.header("🖨️ Print Multiple Barcodes")
    
    assets_df = read_data(SHEETS["assets"])
    
    if assets_df.empty:
        st.warning("No assets found. Please add assets first.")
        return
    
    st.subheader("Select Assets to Print Barcodes")
    
    # Multi-select assets
    asset_options = assets_df.apply(
        lambda x: f"{x['Asset ID']} - {x.get('Asset Name', 'N/A')}", axis=1
    ).tolist()
    
    selected_assets = st.multiselect(
        "Select Assets",
        asset_options,
        help="Select multiple assets to generate barcodes for printing"
    )
    
    if selected_assets:
        # Extract Asset IDs
        asset_ids = [asset.split(" - ")[0] for asset in selected_assets]
        
        col1, col2 = st.columns(2)
        with col1:
            barcode_format = st.selectbox("Barcode Format", ["Code128", "QR Code"])
        with col2:
            barcodes_per_row = st.number_input("Barcodes per Row", min_value=1, max_value=5, value=2)
        
        if st.button("Generate Barcodes for Printing", use_container_width=True):
            # Generate barcodes
            barcode_images = []
            for asset_id in asset_ids:
                img = generate_barcode_image(asset_id, "qr" if barcode_format == "QR Code" else "code128")
                if img:
                    barcode_images.append((asset_id, img))
            
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
                            asset_id, img = barcode_images[idx]
                            with cols[col_idx]:
                                st.image(img, caption=asset_id, use_container_width=True)
                
                # Download option
                st.subheader("Download Barcodes")
                st.info("Right-click on each barcode image and select 'Save image as...' to download, or use the print function in your browser.")
                
                # Create a combined image for printing
                if st.button("Create Print Layout", use_container_width=True):
                    # Create a combined image
                    img_width = 400
                    img_height = 200
                    combined_width = img_width * barcodes_per_row
                    combined_height = img_height * rows
                    
                    combined_img = Image.new('RGB', (combined_width, combined_height), 'white')
                    
                    for idx, (asset_id, img) in enumerate(barcode_images):
                        row = idx // barcodes_per_row
                        col = idx % barcodes_per_row
                        
                        # Resize image
                        img_resized = img.resize((img_width - 20, img_height - 40))
                        
                        # Paste image
                        x_offset = col * img_width + 10
                        y_offset = row * img_height + 20
                        combined_img.paste(img_resized, (x_offset, y_offset))
                    
                    # Convert to bytes for download
                    img_buffer = io.BytesIO()
                    combined_img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    st.download_button(
                        label="Download Combined Barcode Sheet",
                        data=img_buffer,
                        file_name="barcodes_print_sheet.png",
                        mime="image/png",
                        use_container_width=True
                    )
