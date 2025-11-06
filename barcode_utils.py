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
from google_sheets import read_data
from config import SHEETS
import numpy as np

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
    """Barcode scanner and search page"""
    st.header("🔍 Barcode Scanner & Search")
    
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
                
                for idx, asset in matching_assets.iterrows():
                    with st.expander(f"Asset: {asset['Asset ID']} - {asset.get('Asset Name', 'N/A')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write("**Asset Details:**")
                            st.write(f"**Asset ID:** {asset['Asset ID']}")
                            st.write(f"**Asset Name:** {asset.get('Asset Name', 'N/A')}")
                            st.write(f"**Category:** {asset.get('Category', 'N/A')}")
                            st.write(f"**Sub Category:** {asset.get('Sub Category', 'N/A')}")
                            st.write(f"**Location:** {asset.get('Location', 'N/A')}")
                            st.write(f"**Status:** {asset.get('Status', 'N/A')}")
                            st.write(f"**Condition:** {asset.get('Condition', 'N/A')}")
                            st.write(f"**Assigned To:** {asset.get('Assigned To', 'N/A')}")
                        
                        with col2:
                            # Display barcode
                            barcode_img = generate_barcode_image(asset['Asset ID'])
                            if barcode_img:
                                st.image(barcode_img, caption=f"Barcode: {asset['Asset ID']}", use_container_width=True)
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
                st.dataframe(results, use_container_width=True)
                
                # Option to view barcode for each result
                selected_asset_id = st.selectbox(
                    "Select Asset to View Barcode",
                    ["Select an asset"] + results["Asset ID"].tolist()
                )
                
                if selected_asset_id != "Select an asset":
                    barcode_img = generate_barcode_image(selected_asset_id)
                    if barcode_img:
                        st.image(barcode_img, caption=f"Barcode: {selected_asset_id}", use_container_width=True)
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
