import streamlit as st
import cv2
import numpy as np
import fitz  # PyMuPDF
import io
import os
from PIL import Image

# ⚙️ Web Workspace Layout Initializer Configuration
st.set_page_config(page_title="AI Document Enhancer Pro", page_icon="📄", layout="centered")

st.title("📄 COMMERCIAL-GRADE AUTOMATED DOCUMENT ENHANCER")
st.write("Upload raw smartphone images or PDF packets. The app will automatically optimize text clarity and wipe background stains.")

# ==============================================================================
# PRO-CLASS PERFORMANCE CONSTANTS
# ==============================================================================
TARGET_LONG_SIDE = 2400     # Target resolution for crisp print formatting
MAX_UPSCALE_FACTOR = 2.0    # Soft interpolation limit to prevent blow-up blur
PDF_ZOOM_FACTOR = 2.5       # Resolution scale for PDF extraction loops
OUTPUT_MODE = "grayscale"   # "grayscale" or "binary"

DENOISE_STRENGTH = 15       # Less smoothing of photos / thin strokes
LIGHT_MAP_SIZE = 110        # Larger = keeps more photo tone (shadows still removed)
SHARPEN_AMOUNT = 2.0        # High sharpness multiplier
SHARPEN_SIGMA = 0.8         # Tighter radius = crisper edges, fewer halos
CONTRAST_BOOST = 1.0        # Smoothstep S-curve contrast boost

def _odd(n):
    """Ensures a kernel/block size is a valid odd integer >= 3."""
    n = int(n)
    if n < 3:
        n = 3
    return n if n % 2 == 1 else n + 1

def apply_commercial_grade_enhancements(pil_img, mode=OUTPUT_MODE):
    """
    Advanced Restoration Pipeline: Corrects smartphone shadows, normalizes contrast,
    protects handwritten strokes, and sharpens text lines cleanly.
    """
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    base_dim = min(h, w)
    scale_ref = base_dim / 1200.0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Light noise removal (reduced so photos / strokes are not smoothed)
    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=DENOISE_STRENGTH, sigmaSpace=DENOISE_STRENGTH)

    # Shadow / uneven-light removal
    light_map_k = _odd(LIGHT_MAP_SIZE * scale_ref)
    bg_light_map = cv2.GaussianBlur(denoised, (light_map_k, light_map_k), 0)
    bg_light_map[bg_light_map == 0] = 1
    norm_gray = cv2.divide(denoised, bg_light_map, scale=255)

    # Balanced contrast equalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(16, 16))
    contrasted = clahe.apply(norm_gray)

    # Unsharp mask sharpening
    blur_for_sharpen = cv2.GaussianBlur(contrasted, (0, 0), sigmaX=SHARPEN_SIGMA * max(scale_ref, 1.0))
    crisp = cv2.addWeighted(contrasted, 1 + SHARPEN_AMOUNT, blur_for_sharpen, -SHARPEN_AMOUNT, 0)

    # Small contrast boost: gentle S-curve (darker darks, cleaner whites)
    if CONTRAST_BOOST > 0:
        x = np.arange(256, dtype=np.float32) / 255.0
        s_curve = x * x * (3.0 - 2.0 * x)                       # smoothstep S-curve
        lut = ((1.0 - CONTRAST_BOOST) * x + CONTRAST_BOOST * s_curve) * 255.0
        crisp = cv2.LUT(crisp, np.clip(lut, 0, 255).astype(np.uint8))

    if mode == "binary":
        block = _odd(35 * scale_ref)
        binary = cv2.adaptiveThreshold(
            crisp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresh_type=cv2.THRESH_BINARY, blockSize=block, C=12
        )
        final_gray = cv2.medianBlur(binary, 3)
    else:
        final_gray = crisp

    # Convert back to standard 3-channel matrix format layout
    final_output = cv2.cvtColor(final_gray, cv2.COLOR_GRAY2BGR)
    return Image.fromarray(cv2.cvtColor(final_output, cv2.COLOR_BGR2RGB))

def smart_upscale(img):
    """Upscales low-res documents cleanly to the target resolution threshold."""
    w, h = img.size
    long_side = max(w, h)
    if long_side >= TARGET_LONG_SIDE:
        return img

    needed_factor = TARGET_LONG_SIDE / long_side
    scale_factor = min(needed_factor, MAX_UPSCALE_FACTOR)
    if scale_factor <= 1.0:
        return img

    return img.resize((int(w * scale_factor), int(h * scale_factor)), Image.Resampling.LANCZOS)


# ==============================================================================
# STREAMLIT INTERFACE MANAGER
# ==============================================================================
uploaded_files = st.file_uploader(
    "Upload single/multiple image files or PDF documents here:", 
    type=["png", "jpg", "jpeg", "jfif", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    # Use Streamlit session state to cache data securely between button clicks
    if 'processed_pdf_bytes' not in st.session_state:
        st.session_state.processed_pdf_bytes = None
        st.session_state.final_filename = ""

    # STATE 1: If data hasn't been enhanced yet, show the main Action button
    if st.session_state.processed_pdf_bytes is None:
        if st.button("🚀 Run Enhancement", type="primary", use_container_width=True):
            with st.spinner("Processing files... Please wait..."):
                new_doc = fitz.open()
                total_pages_processed = 0
                base_output_name = "enhanced_document"

                for idx, file in enumerate(uploaded_files):
                    file_bytes = file.read()
                    file_ext = os.path.splitext(file.name)[1].lower()
                    
                    if idx == 0:
                        base_output_name = os.path.splitext(file.name)[0]

                    # Scenario A: Process PDF pages
                    if file_ext == ".pdf":
                        doc = fitz.open(stream=file_bytes, filetype="pdf")
                        for page_index in range(len(doc)):
                            page = doc[page_index]
                            zoom_matrix = fitz.Matrix(PDF_ZOOM_FACTOR, PDF_ZOOM_FACTOR)
                            pix = page.get_pixmap(matrix=zoom_matrix, colorspace=fitz.csRGB, alpha=False)

                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            img = apply_commercial_grade_enhancements(img)

                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format="PNG")
                            img_bytes.seek(0)

                            img_doc = fitz.open("pdf", fitz.open(stream=img_bytes.getvalue(), filetype="png").convert_to_pdf())
                            new_doc.insert_pdf(img_doc)
                            total_pages_processed += 1
                        doc.close()

                    # Scenario B: Process images (PNG, JPG, JPEG, JFIF)
                    elif file_ext in [".png", ".jpg", ".jpeg", ".jfif"]:
                        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")

                        img = smart_upscale(img)
                        img = apply_commercial_grade_enhancements(img)

                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="PNG")
                        img_bytes.seek(0)

                        img_doc = fitz.open("pdf", fitz.open(stream=img_bytes.getvalue(), filetype="png").convert_to_pdf())
                        new_doc.insert_pdf(img_doc)
                        total_pages_processed += 1

                if total_pages_processed > 0:
                    output_stream = io.BytesIO()
                    new_doc.save(output_stream)
                    new_doc.close()
                    
                    # Store final output variables inside session memory
                    st.session_state.processed_pdf_bytes = output_stream.getvalue()
                    st.session_state.final_filename = f"enhanced_{base_output_name}.pdf"
                    st.rerun()
                else:
                    st.error("❌ Error: No valid images or PDF pages could be processed.")

    # STATE 2: Processing complete! Instantly show the native secure download layout
    else:
        st.balloons()
        st.success("🎉 Enhancement processing complete!")
        
        # This official native button instantly pops open the browser file save path window 
        st.download_button(
            label=f"📥 DOWNLOAD YOUR ENHANCED PDF ({st.session_state.final_filename})",
            data=st.session_state.processed_pdf_bytes,
            file_name=st.session_state.final_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        # Clean session reset layout button to process a fresh batch of documents
        if st.button("🔄 Enhance Another Document Pack", use_container_width=True):
            st.session_state.processed_pdf_bytes = None
            st.session_state.final_filename = ""
            st.rerun()
