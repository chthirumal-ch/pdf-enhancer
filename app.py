print("⏳ Step 2/3: Generating the Streamlit UI script...")
with open("app.py", "w") as f:
    f.write('''import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
import io

# App Layout Configuration (Using wide mode for side-by-side previewing)
st.set_page_config(page_title="PDF Enhancer", page_icon="📄", layout="wide")

st.title("📄 OUR PDF ENHANCER")
st.write("Adjust settings in the sidebar to see changes in real-time on the preview window.")

# Sidebar Settings panel
st.sidebar.header("🎛️ Fine-Tune Enhancements")
dpi_setting = st.sidebar.slider("Resolution (DPI)", min_value=100, max_value=300, value=200, step=50)

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

# Main Document Upload Widget
uploaded_file = st.file_uploader("Drop your PDF here or click to browse", type=["pdf"])

if uploaded_file is not None:
    # Read file stream safely into memory
    file_bytes = uploaded_file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    
    st.info(f"Loaded document successfully! Total Pages: {total_pages}")
    
    # Allow choosing which page to preview
    preview_page_num = st.number_input("Select page to preview:", min_value=1, max_value=total_pages, value=1)
    
    # --- LIVE PREVIEW WINDOW ---
    st.subheader(f"🔍 Live Preview (Page {preview_page_num})")
    
    # Process chosen preview page (0-indexed in PyMuPDF)
    preview_page = doc[preview_page_num - 1]
    preview_pix = preview_page.get_pixmap(dpi=150)  # slightly lower DPI for rapid rendering
    orig_preview_img = Image.frombytes("RGB", [preview_pix.width, preview_pix.height], preview_pix.samples)
    
    # Run the filters over the raw preview image
    enhanced_preview_img = apply_enhancements(orig_preview_img, sharpness_val, brightness_val, contrast_val)
    
    # Render layout side-by-side using Streamlit horizontal layouts
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"Original Page {preview_page_num}")
        st.image(orig_preview_img, use_container_width=True)
    with col2:
        st.caption(f"Enhanced Page {preview_page_num} (Live Preview)")
        st.image(enhanced_preview_img, use_container_width=True)
    
    st.markdown("---")
    
    # --- FULL PRODUCTION RUN ---
    st.subheader("🚀 Ready?")
    if st.button("Process & Download Full PDF", type="primary", use_container_width=True):
        with st.spinner(f"Processing all {total_pages} pages... please stand by."):
            try:
                new_doc = fitz.open()

                # Loop through and filter every page sequentially
                for page_index in range(total_pages):
                    page = doc[page_index]

                    # Extract page image based on sidebar chosen DPI setting
                    pix = page.get_pixmap(dpi=dpi_setting)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Fire enhancement transformations
                    img = apply_enhancements(img, sharpness_val, brightness_val, contrast_val)

                    # Pack filtered images back cleanly into a PDF structure
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="JPEG", quality=95)
                    img_bytes.seek(0)

                    img_doc = fitz.open("pdf", fitz.open(stream=img_bytes.getvalue(), filetype="jpeg").convert_to_pdf())
                    new_doc.insert_pdf(img_doc)

                # Export document elements out onto byte memory array
                output_stream = io.BytesIO()
                new_doc.save(output_stream)
                new_doc.close()
                
                output_bytes = output_stream.getvalue()

                st.balloons()  # Fun success animation overlay
                st.success("✨ Whole document processing complete!")
                
                # Expose direct browser downloader stream button
                st.download_button(
                    label="💾 Click here to download Enhanced PDF",
                    data=output_bytes,
                    file_name="enhanced_output.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"An unexpected error occurred while processing: {e}")
                
    doc.close()
''')

