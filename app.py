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
            pass

    if os.path.exists(ARABIC_FONT_PATH):
        pdfmetrics.registerFont(TTFont("Amiri", ARABIC_FONT_PATH))
        return "Amiri"
    return "Helvetica"

FONT_NAME = load_arabic_font()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Bubble Sheet Exam Manager - Form A/B & Reference Grading", page_icon="📝", layout="wide"
)

st.title("📝 Exam Creator & OMR Grader (Form A/B & Reference Photo Key)")

# --- ARABIC TEXT HELPER ---
def format_arabic(text):
    if not isinstance(text, str):
        text = str(text)
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)


# --- EXCEL PARSER FOR COLLEGE LAB GROUPS ---
def parse_college_excel(file_bytes):
    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None)
    students = []
    current_group = "General"

    for idx, row in df_raw.iterrows():
        row_cells = [str(val).strip() for val in row.values if pd.notna(val)]
        if not row_cells:
            continue

        full_row_str = " ".join(row_cells)

        if any(keyword in full_row_str for keyword in ["المرحلة", "جروب", "Group", "مجموعة"]):
            if "-" in full_row_str:
                current_group = full_row_str.split("-")[-1].strip()
            else:
                current_group = full_row_str
            continue

        if "اسم الطالب" in full_row_str or "كروبات" in full_row_str or "جامعة" in full_row_str:
            continue

        if len(row_cells) >= 2 and row_cells[0].isdigit():
            students.append({
                "group": current_group,
                "student_id": row_cells[0],
                "student_name": row_cells[1]
            })

    return pd.DataFrame(students)


# --- BUBBLE SHEET PDF GENERATOR (WITH FORM A / B) ---
def draw_single_sheet(student_id, student_name, group_name, exam_id, form_type="A", num_questions=20):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    # Registration Corner Marks
    marker_size, margin = 20, 30
    c.rect(margin, page_height - margin - marker_size, marker_size, marker_size, fill=1)
    c.rect(page_width - margin - marker_size, page_height - margin - marker_size, marker_size, marker_size, fill=1)
    c.rect(margin, margin, marker_size, marker_size, fill=1)
    c.rect(page_width - margin - marker_size, margin, marker_size, marker_size, fill=1)

    # Header Details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, page_height - 45, f"Exam ID: {exam_id}")
    c.drawString(70, page_height - 65, f"Group: {group_name}")
    c.drawString(70, page_height - 85, f"Form: {form_type}")
    c.setFont("Helvetica", 11)
    c.drawString(70, page_height - 102, f"Student ID: {student_id}")

    # Right-aligned Arabic Name
    formatted_name = format_arabic(student_name)
    c.setFont(FONT_NAME, 14)
    c.drawRightString(page_width - 150, page_height - 45, formatted_name)

    # QR Code (Encodes Student ID, Group, Exam, and Form)
    qr_payload = json.dumps({
        "group": str(group_name),
        "student_id": str(student_id),
        "exam_id": str(exam_id),
        "form": str(form_type)
    })
    qr_img = qrcode.make(qr_payload)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    c.drawImage(
        canvas.ImageReader(qr_buffer),
        page_width - 130,
        page_height - 135,
        width=80,
        height=80,
    )

    # Bubbles Grid
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


# --- OMR SCANNER HELPER (READS BUBBLES FROM IMAGE) ---
def scan_bubbles_from_image(image_bytes, num_questions=20):
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
        return None, "No bubbles detected. Please ensure clear lighting and straight photo."

    bubble_contours = sorted(bubble_contours, key=lambda c: cv2.boundingRect(c)[1])
    options = ["A", "B", "C", "D"]
    answers = {}

    for q_idx in range(1, num_questions + 1):
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

        answers[str(q_idx)] = options[marked_idx] if marked_idx is not None else "None"

    return answers, None


# --- STREAMLIT UI ---
tab1, tab2 = st.tabs(["1️⃣ Generate Form A & B Sheets", "2️⃣ Reference Photo Key & Grading"])

with tab1:
    st.header("Step 1: Generate Form A & Form B Sheets for Lab Groups")
    col1, col2 = st.columns(2)

    with col1:
        exam_id = st.text_input("Exam Code or Title", "DENT2025")
        num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=20)
        form_mode = st.radio("Form Distribution Strategy", ["Alternate Form A and Form B per student", "All Form A", "All Form B"])

    with col2:
        roster_file = st.file_uploader("Upload College Roster Excel File (.xlsx)", type=["xlsx", "xls"])

    if roster_file and exam_id:
        try:
            file_bytes = roster_file.read()
            df = parse_college_excel(file_bytes)

            if not df.empty:
                st.success(f"Parsed {len(df)} total students across {len(df['group'].unique())} groups!")

                if st.button("🚀 Generate Form A/B Sheets (Group Folders)"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        for idx, row in df.iterrows():
                            group = str(row["group"])
                            s_id = str(row["student_id"])
                            s_name = str(row["student_name"])

                            # Assign Form A or B
                            if form_mode == "Alternate Form A and Form B per student":
                                current_form = "A" if idx % 2 == 0 else "B"
                            elif form_mode == "All Form A":
                                current_form = "A"
                            else:
                                current_form = "B"

                            pdf_bytes = draw_single_sheet(
                                student_id=s_id,
                                student_name=s_name,
                                group_name=group,
                                exam_id=exam_id,
                                form_type=current_form,
                                num_questions=num_questions
                            )

                            clean_name = s_name.replace(" ", "_")
                            file_path = f"Group_{group}/Form_{current_form}_sheet_{s_id}_{clean_name}.pdf"
                            zf.writestr(file_path, pdf_bytes)

                    zip_buffer.seek(0)
                    st.download_button(
                        label="📥 Download Grouped Form A/B Sheets (ZIP)",
                        data=zip_buffer,
                        file_name=f"{exam_id}_FormA_FormB_sheets.zip",
                        mime="application/zip",
                    )
        except Exception as e:
            st.error(f"Error processing file: {e}")

with tab2:
    st.header("Step 2: Upload Reference Photo Keys & Grade Student Papers")

    st.subheader("📷 1. Upload Reference Key Photos (Correct Answers)")
    col_a, col_b = st.columns(2)

    with col_a:
        key_img_a = st.file_uploader("Upload Reference Answer Sheet Photo for Form A", type=["jpg", "png", "jpeg"])
    with col_b:
        key_img_b = st.file_uploader("Upload Reference Answer Sheet Photo for Form B (Optional)", type=["jpg", "png", "jpeg"])

    answer_key_a = None
    answer_key_b = None

    if key_img_a:
        key_a_bytes = key_img_a.read()
        answer_key_a, err_a = scan_bubbles_from_image(key_a_bytes, num_questions=num_questions)
        if err_a:
            st.error(f"Form A Reference Key Error: {err_a}")
        else:
            st.success("Form A Reference Answer Key loaded successfully!")
            st.json(answer_key_a)

    if key_img_b:
        key_b_bytes = key_img_b.read()
        answer_key_b, err_b = scan_bubbles_from_image(key_b_bytes, num_questions=num_questions)
        if err_b:
            st.error(f"Form B Reference Key Error: {err_b}")
        else:
            st.success("Form B Reference Answer Key loaded successfully!")
            st.json(answer_key_b)

    st.markdown("---")
    st.subheader("📝 2. Upload & Grade Student Exam Photos")

    student_img = st.file_uploader("Upload Student Exam Photo", type=["jpg", "png", "jpeg"])
    selected_form = st.radio("Which Form is this student paper?", ["Form A", "Form B"])

    if student_img:
        target_key = answer_key_a if selected_form == "Form A" else answer_key_b

        if not target_key:
            st.warning(f"Please upload the reference key photo for {selected_form} above first!")
        else:
            col_preview, col_result = st.columns(2)
            with col_preview:
                st.image(student_img, caption="Student Paper", use_column_width=True)

            with col_result:
                if st.button("🔍 Grade Student Paper"):
                    student_bytes = student_img.read()
                    student_answers, err = scan_bubbles_from_image(student_bytes, num_questions=num_questions)

                    if err:
                        st.error(err)
                    else:
                        correct_count = 0
                        total_q = len(target_key)
                        grading_details = {}

                        for q_idx in range(1, total_q + 1):
                            q_str = str(q_idx)
                            s_ans = student_answers.get(q_str, "None")
                            k_ans = target_key.get(q_str, "None")
                            is_correct = (s_ans == k_ans) and (s_ans != "None")
                            if is_correct:
                                correct_count += 1

                            grading_details[f"Q{q_idx}"] = {
                                "Student Answer": s_ans,
                                "Correct Key": k_ans,
                                "Result": "✅ Pass" if is_correct else "❌ Fail"
                            }

                        score_pct = round((correct_count / total_q) * 100, 2)
                        st.metric("Final Score", f"{correct_count}/{total_q}")
                        st.metric("Percentage", f"{score_pct}%")
                        st.dataframe(pd.DataFrame.from_dict(grading_details, orient="index"))
