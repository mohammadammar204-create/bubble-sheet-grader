import io
import json
import os
import urllib.request
import zipfile
import arabic_reshaper
import cv2
import numpy as np
import pandas as pd
import qrcode
import streamlit as st
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- SETUP ARABIC FONT ---
ARABIC_FONT_PATH = "Amiri-Regular.ttf"

@st.cache_resource
def load_arabic_font():
    """Downloads and registers the Amiri Arabic TTF font for ReportLab."""
    if not os.path.exists(ARABIC_FONT_PATH):
        font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf"
        try:
            urllib.request.urlretrieve(font_url, ARABIC_FONT_PATH)
        except Exception:
            # Backup font URL
            font_url_backup = "https://github.com/aliftype/amiri/releases/download/1.000/Amiri-1.000.zip"
            st.error("Failed to download font. Please verify internet access on Streamlit Cloud.")

    if os.path.exists(ARABIC_FONT_PATH):
        pdfmetrics.registerFont(TTFont("Amiri", ARABIC_FONT_PATH))
        return "Amiri"
    return "Helvetica"

FONT_NAME = load_arabic_font()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Bubble Sheet Exam Manager - Laboratory Groups", page_icon="📝", layout="wide"
)

st.title("📝 Exam Creator & OMR Grader (Lab Groups & Arabic Support)")
st.markdown(
    "Upload your laboratory group roster Excel file to generate printable PDF bubble sheets organized by group."
)

# --- ARABIC TEXT HELPER ---
def format_arabic(text):
    """Reshapes and reverses Arabic text so it renders right-to-left correctly in ReportLab PDF."""
    if not isinstance(text, str):
        text = str(text)
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text


# --- EXCEL PARSER FOR COLLEGE LAB GROUPS ---
def parse_college_excel(file_bytes):
    """Parses college lab excel sheets containing group headers (e.g. B1, B2) and student lists."""
    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None)
    students = []
    current_group = "General"

    for idx, row in df_raw.iterrows():
        row_cells = [str(val).strip() for val in row.values if pd.notna(val)]
        if not row_cells:
            continue

        full_row_str = " ".join(row_cells)

        # Detect Lab Group headers (e.g., "المرحلة الثانية - B1")
        if any(keyword in full_row_str for keyword in ["المرحلة", "جروب", "Group", "مجموعة"]):
            if "-" in full_row_str:
                current_group = full_row_str.split("-")[-1].strip()
            else:
                current_group = full_row_str
            continue

        # Skip table header titles
        if "اسم الطالب" in full_row_str or "كروبات" in full_row_str or "جامعة" in full_row_str:
            continue

        # Detect Student ID and Arabic Name
        if len(row_cells) >= 2 and row_cells[0].isdigit():
            s_id = row_cells[0]
            s_name = row_cells[1]
            students.append({
                "group": current_group,
                "student_id": s_id,
                "student_name": s_name
            })

    return pd.DataFrame(students)


# --- BUBBLE SHEET PDF GENERATOR ---
def draw_single_sheet(student_id, student_name, group_name, exam_id, num_questions=20):
    """Generates an A4/Letter PDF bubble sheet formatted for right-to-left Arabic student names."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    # Registration Marks (Corner Anchors for OpenCV Scanning)
    marker_size, margin = 20, 30
    c.rect(margin, page_height - margin - marker_size, marker_size, marker_size, fill=1)
    c.rect(page_width - margin - marker_size, page_height - margin - marker_size, marker_size, marker_size, fill=1)
    c.rect(margin, margin, marker_size, marker_size, fill=1)
    c.rect(page_width - margin - marker_size, margin, marker_size, marker_size, fill=1)

    # Header - Exam & Group Info
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, page_height - 50, f"Exam ID: {exam_id}")
    c.drawString(70, page_height - 70, f"Group: {group_name}")
    c.setFont("Helvetica", 11)
    c.drawString(70, page_height - 88, f"Student ID: {student_id}")

    # Draw Arabic Student Name using registered Arabic Font
    formatted_name = format_arabic(student_name)
    c.setFont(FONT_NAME, 14)
    c.drawRightString(page_width - 150, page_height - 50, formatted_name)

    # QR Code (Encodes Group, Student ID, and Exam ID)
    qr_payload = json.dumps({
        "group": str(group_name),
        "student_id": str(student_id),
        "exam_id": str(exam_id)
    })
    qr_img = qrcode.make(qr_payload)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    c.drawImage(
        canvas.ImageReader(qr_buffer),
        page_width - 130,
        page_height - 130,
        width=80,
        height=80,
    )

    # Answer Bubbles Grid
    y_start = page_height - 180
    options = ["A", "B", "C", "D"]
    for q_idx in range(1, num_questions + 1):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(70, y_start, f"{q_idx:02d}.")
        for opt_idx, opt in enumerate(options):
            x_pos = 110 + (opt_idx * 40)
            c.circle(x_pos, y_start + 3, 9, stroke=1, fill=0)
            c.setFont("Helvetica", 8)
            c.drawString(x_pos - 3, y_start, opt)
        y_start -= 24
        if y_start < 60:
            break

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# --- OMR GRADING ENGINE ---
def grade_sheet(image_bytes, answer_key):
    np_img = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    if image is None:
        return None, "Invalid image format uploaded."

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bubble_contours = []

    for c in contours:
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w / float(h)
        if 12 <= w <= 50 and 12 <= h <= 50 and 0.75 <= ar <= 1.25:
            bubble_contours.append(c)

    if not bubble_contours:
        return None, "No bubble grid detected. Ensure clear lighting."

    bubble_contours = sorted(bubble_contours, key=lambda c: cv2.boundingRect(c)[1])
    options = ["A", "B", "C", "D"]
    total_questions = len(answer_key)
    correct_count = 0
    results = {}

    for q_idx in range(1, total_questions + 1):
        start_idx = (q_idx - 1) * 4
        if start_idx + 4 > len(bubble_contours):
            break

        row_contours = sorted(
            bubble_contours[start_idx : start_idx + 4],
            key=lambda c: cv2.boundingRect(c)[0],
        )
        marked_idx = None
        max_pixels = 0

        for opt_idx, cnt in enumerate(row_contours):
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            mask = cv2.bitwise_and(thresh, thresh, mask=mask)
            total_pixels = cv2.countNonZero(mask)

            if total_pixels > max_pixels and total_pixels > 120:
                max_pixels = total_pixels
                marked_idx = opt_idx

        selected = options[marked_idx] if marked_idx is not None else "None"
        correct = answer_key.get(str(q_idx)) or answer_key.get(q_idx)
        is_correct = selected == correct

        if is_correct:
            correct_count += 1

        results[f"Q{q_idx}"] = {
            "Selected": selected,
            "Correct": correct,
            "Result": "✅ Pass" if is_correct else "❌ Fail",
        }

    score_pct = round((correct_count / total_questions) * 100, 2)
    return {
        "Score": f"{correct_count}/{total_questions}",
        "Percentage": f"{score_pct}%",
        "Details": results,
    }, None


# --- STREAMLIT USER INTERFACE ---
tab1, tab2 = st.tabs(["1️⃣ Generate Lab Group Sheets", "2️⃣ Grade Exam Photos"])

with tab1:
    st.header("Step 1: Upload Roster & Export Organized PDF Packages")
    col1, col2 = st.columns(2)

    with col1:
        exam_id = st.text_input("Exam Code or Title", "DENT2025")
        num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=20)

    with col2:
        roster_file = st.file_uploader("Upload College Roster Excel File (.xlsx)", type=["xlsx", "xls"])

    if roster_file and exam_id:
        try:
            file_bytes = roster_file.read()
            df = parse_college_excel(file_bytes)

            if not df.empty:
                st.success(f"Parsed {len(df)} total students across {len(df['group'].unique())} groups!")
                
                # Show summary count per group
                group_counts = df['group'].value_counts().reset_index()
                group_counts.columns = ['Lab Group', 'Student Count']
                st.dataframe(group_counts)

                if st.button("🚀 Generate PDF Sheets (Grouped Folders)"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for _, row in df.iterrows():
                            group = str(row["group"])
                            s_id = str(row["student_id"])
                            s_name = str(row["student_name"])

                            pdf_bytes = draw_single_sheet(
                                student_id=s_id,
                                student_name=s_name,
                                group_name=group,
                                exam_id=exam_id,
                                num_questions=num_questions
                            )

                            # Save inside group subfolders in the ZIP
                            clean_name = s_name.replace(" ", "_")
                            file_path = f"Group_{group}/sheet_{s_id}_{clean_name}.pdf"
                            zf.writestr(file_path, pdf_bytes)

                    zip_buffer.seek(0)
                    st.download_button(
                        label="📥 Download Grouped Bubble Sheets (ZIP)",
                        data=zip_buffer,
                        file_name=f"{exam_id}_lab_groups.zip",
                        mime="application/zip",
                    )
            else:
                st.error("Could not find student data or group headers in the uploaded Excel file.")
        except Exception as e:
            st.error(f"Error processing file: {e}")

with tab2:
    st.header("Step 2: Key Setup & Instant Auto-Grading")
    key_input = st.text_input("Master Answer Key (Separated by commas)", "A, C, B, D")
    answer_key = {
        str(idx + 1): opt.strip().upper()
        for idx, opt in enumerate(key_input.split(","))
    }

    scanned_image = st.file_uploader("Upload image of completed sheet (.jpg, .png)", type=["jpg", "png", "jpeg"])

    if scanned_image and answer_key:
        col_img, col_res = st.columns(2)
        with col_img:
            st.image(scanned_image, caption="Scanned Sheet", use_column_width=True)
        with col_res:
            if st.button("🔍 Grade Sheet Now"):
                with st.spinner("Processing..."):
                    img_bytes = scanned_image.read()
                    res, err = grade_sheet(img_bytes, answer_key)
                    if err:
                        st.error(err)
                    else:
                        st.metric("Final Score", res["Score"])
                        st.metric("Percentage", res["Percentage"])
                        st.dataframe(pd.DataFrame.from_dict(res["Details"], orient="index"))
