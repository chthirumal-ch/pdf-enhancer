import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
import io
import os

# App Layout Configuration (Using wide mode for side-by-side previewing)
st.set_page_config(page_title="Document Pack Enhancer", page_icon="📄", layout="wide")

st.title("📄 UNIVERSAL DOCUMENT & PDF ENHANCER")
st.write("Upload single/multiple images or PDF packets. Adjust settings in the sidebar to see changes in real-time.")

# Sidebar Settings panel
st.sidebar.header("🎛️ Fine-Tune Enhancements")
dpi_setting = st.sidebar.slider("Resolution (DPI)", min_value=200, max_value=400, value=300, step=30)

# Settings matching your core text enhancement adjustments
sharpness_val = st.sidebar.slider("Sharpness", min_value=1.0, max_value=3.0, value=1.80, step=0.1)
brightness_val = st.sidebar.slider("Brightness", min_value=1.0, max_value=3.0, value=1.60, step=0.1)
contrast_val = st.sidebar.slider("Contrast", min_value=1.0, max_value=3.0, value=1.40, step=0.1)

# Helper function to process images uniformly 
def apply_enhancements(img, sharp, bright, cont):
    img = img.convert("L")  # Convert to Grayscale
    img = ImageEnhance.Sharpness(img).enhance(sharp)   # Crisp text lines
    img = ImageEnhance.Brightness(img).enhance(bright) # Bleach gray background
    img = ImageEnhance.Contrast(img).enhance(cont)     # Make ink darker
    return img

# Main Document Upload Widget - Now supports images (PNG, JPG, JPEG) and PDFs simultaneously!
uploaded_files = st.file_uploader(
    "Drop your PDF or Image files here (Hold Ctrl to select multiple images)", 
    type=["pdf", "png", "jpg", "jpeg","jfif"], 
    accept_multiple_files=True
)

if uploaded_files:
    # Temporary array structures to store unenhanced preview versions
    raw_preview_images = []
    
    # Process uploaded files and parse pages quietly into cache arrays
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        
        # Scenario A: Handle Incoming PDF Documents
        if file_ext == ".pdf":
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page_index in range(len(doc)):
                # DPI is necessary here to maintain text scale and quality loops
                pix = doc[page_index].get_pixmap(dpi=150) # lower DPI for faster screen preview rendering
                page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                raw_preview_images.append(page_img)
            doc.close()
            
        # Scenario B: Handle Incoming Images (JPG/PNG)
        else:
            img_data = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            raw_preview_images.append(img_data)
            
    total_pages = len(raw_preview_images)
    st.info(f"Loaded successfully! Total Pages generated in file package: {total_pages}")
    
    # Allow choosing which page to preview
    preview_page_num = st.number_input("Select page to preview:", min_value=1, max_value=total_pages, value=1)
    
    # --- LIVE PREVIEW WINDOW ---
    st.subheader(f"🔍 Live Preview (Page {preview_page_num})")
    orig_preview_img = raw_preview_images[preview_page_num - 1]
    
    # Run filters instantly in memory
    enhanced_preview_img = apply_enhancements(orig_preview_img, sharpness_val, brightness_val, contrast_val)
    
    # Side-by-side split screen view layouts
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Original Page {preview_page_num}")
        st.image(orig_preview_img, use_container_width=True)
    with col2:
        st.caption(f"Enhanced Page {preview_page_num} (Live Preview)")
        st.image(enhanced_preview_img, use_container_width=True)
    
    st.markdown("---")
    
    # --- FULL PRODUCTION BUNDLE AND CONVERT PACK RUN ---
    st.subheader("🚀 Ready?")
    if st.button("Enhance & Save All Pages as One PDF", type="primary", use_container_width=True):
        with st.spinner(f"Compiling and enhancing all {total_pages} pages into a single print-ready PDF... please wait."):
            try:
                new_doc = fitz.open()

                # Process every single file node sequentially
                for idx, uploaded_file in enumerate(uploaded_files):
                    file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
                    file_ext = os.path.splitext(uploaded_file.name)[1].lower()

                    if file_ext == ".pdf":
                        doc = fitz.open(stream=file_bytes, filetype="pdf")
                        for page_index in range(len(doc)):
                            pix = doc[page_index].get_pixmap(dpi=dpi_setting) # High definition print scaling applied
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            img = apply_enhancements(img, sharpness_val, brightness_val, contrast_val)
                            
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format="JPEG", quality=95)
                            img_bytes.seek(0)
                            
                            img_doc = fitz.open("pdf", fitz.open(stream=img_bytes.getvalue(), filetype="jpeg").convert_to_pdf())
                            new_doc.insert_pdf(img_doc)
                        doc.close()
                    else:
                        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                        # Emulate high-definition DPI limits on plain images via scaling transformations
                        w, h = img.size
                        scale_factor = dpi_setting / 72.0  # standard conversion layout factor
                        if scale_factor > 1.0:
                            img = img.resize((int(w * scale_factor), int(h * scale_factor)), Image.Resampling.LANCZOS)
                            
                        img = apply_enhancements(img, sharpness_val, brightness_val, contrast_val)
                        
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="JPEG", quality=95)
                        img_bytes.seek(0)
                        
                        img_doc = fitz.open("pdf", fitz.open(stream=img_bytes.getvalue(), filetype="jpeg").convert_to_pdf())
                        new_doc.insert_pdf(img_doc)

                # Save the final consolidated multi-page bundle
                output_stream = io.BytesIO()
                new_doc.save(output_stream)
                new_doc.close()
                
                output_bytes = output_stream.getvalue()

                st.balloons()
                st.success("✨ Document package compilation and text optimization complete!")
                
                st.download_button(
                    label="💾 DOWNLOAD SINGLE CONSOLIDATED PDF PACKET",
                    data=output_bytes,
                    file_name="enhanced_compiled_output.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"An unexpected tracking error occurred during conversion: {e}")
