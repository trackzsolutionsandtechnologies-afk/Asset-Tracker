"""
Barcode utilities for scanning and printing
"""
import base64
import streamlit as st
import streamlit.components.v1 as components
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import io
import pandas as pd
import barcode
from barcode.writer import ImageWriter
import uuid
from google_sheets import read_data, update_data
from config import SHEETS
import numpy as np
from datetime import datetime
import subprocess
import sys

# Try to import barcode scanning libraries
PYZBAR_AVAILABLE = False
PYZBAR_IMPORT_ERROR = None
CV2_AVAILABLE = False

def _attempt_pyzbar_import():
    global PYZBAR_AVAILABLE, PYZBAR_IMPORT_ERROR, pyzbar_decode
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode  # type: ignore
        PYZBAR_AVAILABLE = True
        PYZBAR_IMPORT_ERROR = None
    except (ImportError, OSError) as err:
        PYZBAR_AVAILABLE = False
        PYZBAR_IMPORT_ERROR = str(err)

_attempt_pyzbar_import()

if not PYZBAR_AVAILABLE:
    # Try to install pyzbar dynamically (best effort)
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyzbar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _attempt_pyzbar_import()
    except Exception:
        pass

try:
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    import av
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
class BarcodeStreamProcessor:
    def __init__(self) -> None:
        self.latest_result: str | None = None
        self._last_announced: str | None = None

    def recv(self, frame: "av.VideoFrame") -> "av.VideoFrame":  # type: ignore[name-defined]
        img = frame.to_ndarray(format="bgr24")
        display_img = img.copy()

        result = decode_barcode_from_array(img)

        if PYZBAR_AVAILABLE:
            try:
                decoded_objects = pyzbar_decode(img)
                if decoded_objects and CV2_AVAILABLE:
                    import cv2  # type: ignore

                    for obj in decoded_objects:
                        x, y, w, h = obj.rect
                        cv2.rectangle(display_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(
                            display_img,
                            obj.data.decode("utf-8"),
                            (x, max(y - 10, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 0),
                            2,
                        )
            except Exception:
                pass

        if result and result != self._last_announced:
            self.latest_result = result
            self._last_announced = result

        return av.VideoFrame.from_ndarray(display_img, format="bgr24")

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

def _generate_image_variants(image: Image.Image) -> list[np.ndarray]:
    """Create multiple pre-processed variants of the image to improve decoding success."""
    variants: list[np.ndarray] = []
    base = image.convert("RGB")
    variants.append(np.array(base))

    try:
        contrast_img = ImageEnhance.Contrast(base).enhance(2.0)
        variants.append(np.array(contrast_img))
    except Exception:
        pass

    try:
        sharpen_img = ImageEnhance.Sharpness(base).enhance(2.0)
        variants.append(np.array(sharpen_img))
    except Exception:
        pass

    try:
        grayscale = ImageOps.grayscale(base)
        variants.append(np.array(grayscale))
        inverted = ImageOps.invert(grayscale)
        variants.append(np.array(inverted))
    except Exception:
        pass

    try:
        resized = base.resize((int(base.width * 1.5), int(base.height * 1.5)))
        variants.append(np.array(resized))
    except Exception:
        pass

    for angle in (90, -90, 180):
        try:
            rotated = base.rotate(angle, expand=True)
            variants.append(np.array(rotated))
        except Exception:
            pass

    # Ensure we at least have the original image
    if not variants:
        variants.append(np.array(base))

    return variants


def decode_barcode_from_image(image):
    """Decode barcode from image using pyzbar or OpenCV with multiple preprocessing variants."""
    try:
        variants = _generate_image_variants(image)

        if PYZBAR_AVAILABLE:
            for variant in variants:
                try:
                    decoded_objects = pyzbar_decode(variant)
                    if decoded_objects:
                        return decoded_objects[0].data.decode("utf-8")
                except Exception:
                    continue

        if CV2_AVAILABLE:
            import cv2  # type: ignore
            detector = getattr(cv2, "barcode_BarcodeDetector", None)
            qr_detector = cv2.QRCodeDetector()

            for variant in variants:
                try:
                    img_array = variant
                    if detector is not None:
                        barcode_detector = detector()
                        retval, decoded_info, _ = barcode_detector.detectAndDecode(img_array)
                        if retval:
                            if isinstance(decoded_info, (list, tuple)):
                                for info in decoded_info:
                                    if info:
                                        return info
                            elif decoded_info:
                                return decoded_info
                except Exception:
                    pass

                try:
                    data, points, _ = qr_detector.detectAndDecode(img_array)
                    if data:
                        return data
                except Exception:
                    continue
    except Exception as e:
        st.error(f"Error decoding barcode: {str(e)}")
    return None


def decode_barcode_from_array(array: np.ndarray):
    try:
        if array.ndim == 3:
            pil_image = Image.fromarray(array[:, :, ::-1])  # BGR -> RGB
        else:
            pil_image = Image.fromarray(array)
        return decode_barcode_from_image(pil_image)
    except Exception as e:
        st.error(f"Error decoding barcode frame: {str(e)}")
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
            ["📱 Live Mobile Scanner", "📷 Camera Scan", "🖼️ Upload Barcode Image", "⌨️ Manual Entry"],
            horizontal=True,
            key="barcode_input_method"
        )
        
        scanned_barcode = None
        
        if input_method == "📱 Live Mobile Scanner":
            if not WEBRTC_AVAILABLE:
                st.warning("⚠️ Live camera scanning requires `streamlit-webrtc`. Please install dependencies: `pip install streamlit-webrtc av`.")
            elif not PYZBAR_AVAILABLE and not CV2_AVAILABLE:
                st.warning("⚠️ Barcode decoding libraries are not available. Please install `pyzbar` or `opencv-contrib-python-headless` on the server.")
                if PYZBAR_IMPORT_ERROR:
                    st.caption(f"pyzbar import error: {PYZBAR_IMPORT_ERROR}")
            else:
                st.info("Allow camera access. Position the barcode within the frame; scanning is continuous and the first successful decode will auto-fill the result.")
                ctx = webrtc_streamer(
                    key="barcode-live-scanner",
                    mode=WebRtcMode.SENDRECV,
                    media_stream_constraints={"video": True, "audio": False},
                    video_processor_factory=BarcodeStreamProcessor,
                    async_processing=False,
                )

                if ctx and ctx.video_processor:
                    latest = ctx.video_processor.latest_result
                    if latest:
                        scanned_barcode = latest
                        st.success(f"✅ Barcode scanned: {latest}")
                        st.session_state["scanned_barcode"] = latest
        elif input_method == "📷 Camera Scan":
            st.info("📷 Use your device camera to capture the barcode. Make sure to grant camera permissions when prompted.")
            
            if not PYZBAR_AVAILABLE and not CV2_AVAILABLE:
                st.warning("⚠️ Barcode decoding libraries are not available. Please install `pyzbar` or `opencv-contrib-python-headless` on the server.")
                if PYZBAR_IMPORT_ERROR:
                    st.caption(f"pyzbar import error: {PYZBAR_IMPORT_ERROR}")
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
        elif input_method == "🖼️ Upload Barcode Image":
            st.info("🖼️ Upload an image file containing the barcode to decode it.")

            if not PYZBAR_AVAILABLE and not CV2_AVAILABLE:
                st.warning("⚠️ Barcode decoding libraries are not available. Please install `pyzbar` or `opencv-contrib-python-headless` on the server.")
                if PYZBAR_IMPORT_ERROR:
                    st.caption(f"pyzbar import error: {PYZBAR_IMPORT_ERROR}")
                st.info("You can still use manual entry below.")
            else:
                uploaded_image = st.file_uploader(
                    "Upload Barcode Image",
                    type=["png", "jpg", "jpeg", "webp"],
                    key="barcode_image_uploader",
                    help="Provide a clear image of the barcode or QR code."
                )
                if uploaded_image is not None:
                    try:
                        img = Image.open(uploaded_image)
                        if img.mode not in ("RGB", "RGBA"):
                            img = img.convert("RGB")
                        with st.spinner("Decoding barcode..."):
                            decoded_barcode = decode_barcode_from_image(img)

                        if decoded_barcode:
                            scanned_barcode = decoded_barcode
                            st.success(f"✅ Barcode decoded: {decoded_barcode}")
                            st.session_state["scanned_barcode"] = decoded_barcode
                        else:
                            st.warning("⚠️ Could not decode the uploaded barcode image. Please try a clearer image or use manual entry.")
                            st.image(img, caption="Uploaded Image", use_container_width=True)
                    except Exception as err:
                        st.error(f"Error processing image: {err}")

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
