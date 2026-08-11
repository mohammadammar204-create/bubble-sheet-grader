import io
import json
import zipfile
import cv2
import numpy as np
import pandas as pd
import qrcode
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Bubble Sheet Exam Manager", page_icon="📝", layout="wide"
)

st.title("📝 Automated Exam Creator & OMR Grader")
st.markdown(
    "Upload your student roster Excel file, generate printable PDF bubble sheets, and grade exam photos automatically."
)


# --- HELPER FUNCTIONS ---
def draw_single_sheet(student_id, student_name, exam_id, num_questions=20):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    # Registration Marks (Corner Markers for OpenCV Alignment)
    marker_size, margin = 20, 30
    c.rect(margin, page_height - margin - marker_size, marker_size, marker_size, fill=1)
    c.rect(page_width - margin - marker_size, page_height - margin - marker_size, marker_size, marker_size, fill=1)
    c.rect(margin, margin, marker_size, marker_size, fill=1)
    c.rect(page_width - margin - marker_size, margin, marker_size, marker_size, fill=1)

    # Header Text
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, page_height - 50, f"Exam ID: {exam_id}")
    c.drawString(70, page_height - 70, f"Student: {student_name}")
    c.setFont("Helvetica", 11)
    c.drawString(70, page_height - 88, f"Student ID: {student_id}")

    # QR Metadata Encoding
    qr_payload = json.dumps(
        {"student_id": str(student_id), "exam_id": str(exam_id)}
    )
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

    # Drawing Bubbles
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


def grade_sheet(image_bytes, answer_key):
    np_img = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    if image is None:
        return None, "Invalid image format uploaded."

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    contours, _ = cv2.findContours(
        thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    bubble_contours = []

    for c in contours:
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w / float(h)
        if 12 <= w <= 50 and 12 <= h <= 50 and 0.75 <= ar <= 1.25:
            bubble_contours.append(c)

    if not bubble_contours:
        return None, "No bubble grid detected. Ensure good lighting and a clear picture."

    bubble_contours = sorted(
        bubble_contours, key=lambda c: cv2.boundingRect(c)[1]
    )
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
            "Result": "✅ Correct" if is_correct else "❌ Incorrect",
        }

    score_pct = round((correct_count / total_questions) * 100, 2)
    return {
        "Score": f"{correct_count}/{total_questions}",
        "Percentage": f"{score_pct}%",
        "Details": results,
    }, None


# --- WEBSITE INTERFACE TABS ---
tab1, tab2 = st.tabs(
    ["1️⃣ Generate Bubble Sheets", "2️⃣ Grade Exam Photos"]
)

# TAB 1: GENERATE SHEETS
with tab1:
    st.header("Step 1: Import Roster & Download PDFs")
    col1, col2 = st.columns(2)

    with col1:
        exam_id = st.text_input("Exam Code or Title", "EXAM101")
        num_questions = st.number_input(
            "Number of Questions", min_value=1, max_value=50, value=20
        )

    with col2:
        roster_file = st.file_uploader(
            "Upload Excel Student List (.xlsx)", type=["xlsx", "xls"]
        )

    if roster_file and exam_id:
        try:
            df = pd.read_excel(roster_file)
            df.columns = [
                str(c).strip().lower().replace(" ", "_") for c in df.columns
            ]

            if "student_id" in df.columns and "student_name" in df.columns:
                st.success(
                    f"Roster loaded! Found {len(df)} students."
                )
                st.dataframe(df[["student_id", "student_name"]].head())

                if st.button("🚀 Generate PDF Bubble Sheet Package"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(
                        zip_buffer, "w", zipfile.ZIP_DEFLATED
                    ) as zf:
                        for _, row in df.iterrows():
                            s_id = str(row["student_id"])
                            s_name = str(row["student_name"])
                            pdf_data = draw_single_sheet(
                                s_id, s_name, exam_id, num_questions
                            )
                            zf.writestr(
                                f"sheet_{s_id}_{s_name}.pdf", pdf_data
                            )

                    zip_buffer.seek(0)
                    st.download_button(
                        label="📥 Download All Sheets (ZIP)",
                        data=zip_buffer,
                        file_name=f"{exam_id}_bubble_sheets.zip",
                        mime="application/zip",
                    )
            else:
                st.error(
                    "Excel must contain two columns titled: 'student_id' and 'student_name'."
                )
        except Exception as e:
            st.error(f"Error reading file: {e}")

# TAB 2: GRADE SHEETS
with tab2:
    st.header("Step 2: Key Setup & Instant Auto-Grading")

    key_input = st.text_input(
        "Master Answer Key (Separated by commas)", "A, C, B, D"
    )
    answer_key = {
        str(idx + 1): opt.strip().upper()
        for idx, opt in enumerate(key_input.split(","))
    }

    st.subheader("Upload Student Paper Photo")
    scanned_image = st.file_uploader(
        "Upload image of completed sheet (.jpg, .png)", type=["jpg", "png", "jpeg"]
    )

    if scanned_image and answer_key:
        col_img, col_res = st.columns(2)

        with col_img:
            st.image(
                scanned_image, caption="Uploaded Sheet", use_column_width=True
            )

        with col_res:
            if st.button("🔍 Grade Sheet Now"):
                with st.spinner("Grading..."):
                    img_bytes = scanned_image.read()
                    res, err = grade_sheet(img_bytes, answer_key)

                    if err:
                        st.error(err)
                    else:
                        st.metric("Final Score", res["Score"])
                        st.metric("Percentage", res["Percentage"])

                        itemized_df = pd.DataFrame.from_dict(
                            res["Details"], orient="index"
                        )
                        st.dataframe(itemized_df)
