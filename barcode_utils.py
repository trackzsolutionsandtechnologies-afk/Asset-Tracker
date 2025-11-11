"""Barcode utilities for scanning and printing."""

import base64
import io
import subprocess
import sys
import uuid
from datetime import datetime

import barcode
import numpy as np
import pandas as pd
import qrcode
import streamlit as st
import streamlit.components.v1 as components
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from components.quagga_scanner import quagga_scanner
from config import SHEETS
from google_sheets import read_data, update_data

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
    """Display the embedded QuaggaJS barcode scanner component."""
    st.header("📸 Live Barcode Scanner")

    result = quagga_scanner(key="live_barcode_scanner")

    if result:
        if "error" in result:
            st.error(f"Scanner error: {result['error']}")
        elif code := result.get("code"):
            st.success(f"Detected barcode: {code}")

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
