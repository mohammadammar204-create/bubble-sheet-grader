import difflib
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Safe import for pypdf
try:
    import pypdf

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

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
st.set_page_config(page_title="Grading & Attendance System", page_icon="⚡", layout="wide")

bg_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop"

# --- AESTHETIC STYLING ---
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        color: #F5F5F7 !important;
    }}

    .stApp {{
        background: 
            linear-gradient(rgba(12, 14, 22, 0.70), rgba(12, 14, 22, 0.70)),
            url("{bg_url}") no-repeat center center fixed !important;
        background-size: cover !important;
    }}

    .header-card {{
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
    }}

    .title-text {{
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        background: linear-gradient(135deg, #00D2FF 0%, #3A7BD5 50%, #FF7E5F 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.1;
    }}

    .glass-card {{
        background: rgba(22, 24, 30, 0.55);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 40px;
        border-radius: 10px;
        font-weight: 500;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.65) !important;
        border: 1px solid transparent !important;
        padding: 0 18px;
        background-color: transparent !important;
        transition: all 0.25s ease;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: rgba(255, 255, 255, 0.95) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: rgba(255, 255, 255, 0.18) !important;
        color: #FFFFFF !important;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        backdrop-filter: blur(10px);
    }}

    .stTabs [data-baseweb="tab-highlight-title"] {{
        display: none !important;
    }}

    div[data-baseweb="input"] input {{
        background-color: rgba(28, 28, 30, 0.8) !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }}

    div.stButton > button {{
        background: linear-gradient(180deg, #0A84FF 0%, #0071E3 100%) !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 22px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        box-shadow: 0 4px 16px rgba(10, 132, 255, 0.3) !important;
        transition: all 0.25s ease !important;
    }}

    div.stButton > button:hover {{
        transform: translateY(-1px) scale(1.01) !important;
        box-shadow: 0 6px 22px rgba(10, 132, 255, 0.45) !important;
    }}

    div.stDownloadButton > button {{
        background: linear-gradient(180deg, #30D158 0%, #28CD41 100%) !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 22px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        box-shadow: 0 4px 16px rgba(48, 209, 88, 0.3) !important;
        transition: all 0.25s ease !important;
    }}

    div.stDownloadButton > button:hover {{
        transform: translateY(-1px) scale(1.01) !important;
        box-shadow: 0 6px 22px rgba(48, 209, 88, 0.45) !important;
    }}

    section[data-testid="stFileUploader"] {{
        border: 1.5px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 14px !important;
        background: rgba(255, 255, 255, 0.02) !important;
        padding: 12px !important;
    }}

    h1, h2, h3, h4, label {{
        color: #F5F5F7 !important;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>

    <div class="header-card">
        <h1 class="title-text">Grading & Attendance System</h1>
    </div>
""",
    unsafe_allow_html=True,
)


def format_arabic(text):
    if not isinstance(text, str):
        text = str(text)
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)


def parse_college_excel(file_bytes):
    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None)
    students = []
    current_group = "General"

    for idx, row in df_raw.iterrows():
        row_cells = [str(val).strip() for val in row.values if pd.notna(val)]
        if not row_cells:
            continue

        full_row_str = " ".join(row_cells)

        if any(
            keyword in full_row_str
            for keyword in ["المرحلة", "جروب", "Group", "مجموعة"]
        ):
            if "-" in full_row_str:
                current_group = full_row_str.split("-")[-1].strip()
            else:
                current_group = full_row_str
            continue

        if (
            "اسم الطالب" in full_row_str
            or "كروبات" in full_row_str
            or "جامعة" in full_row_str
        ):
            continue

        if len(row_cells) >= 2 and row_cells[0].isdigit():
            students.append(
                {
                    "group": current_group,
                    "student_id": str(row_cells[0]),
                    "student_name": str(row_cells[1]),
                }
            )

    return pd.DataFrame(students)


def generate_attendance_pdf(group_name, students_list, exam_id):
    """Generates printable attendance sheet for a group."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, page_height - 50, f"Attendance Sheet - {exam_id}")
    c.setFont("Helvetica", 12)
    c.drawString(50, page_height - 70, f"Group: {group_name}")

    y = page_height - 110
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "No.")
    c.drawString(80, y, "ID")
    c.drawString(160, y, "Student Name")
    c.drawString(450, y, "Signature / Status")
    c.line(50, y - 5, page_width - 50, y - 5)

    y -= 25
    c.setFont(FONT_NAME, 11)

    for idx, student in enumerate(students_list, 1):
        if y < 50:
            c.showPage()
            y = page_height - 50

        c.setFont("Helvetica", 10)
        c.drawString(50, y, str(idx))
        c.drawString(80, y, str(student["student_id"]))

        formatted_name = format_arabic(student["student_name"])
        c.setFont(FONT_NAME, 11)
        c.drawString(160, y, formatted_name)

        c.setFont("Helvetica", 10)
        c.rect(450, y - 2, 100, 15)
        y -= 22

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def draw_single_sheet(
    student_id,
    student_name,
    group_name,
    exam_id,
    form_type="A",
    num_questions=10,
    is_reference=False,
):
    """Generates PDF bubble sheet with QR code for student or reference answer key."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    # Registration Corner Marks
    marker_size, margin = 20, 30
    c.rect(
        margin, page_height - margin - marker_size, marker_size, marker_size, fill=1
    )
    c.rect(
        page_width - margin - marker_size,
        page_height - margin - marker_size,
        marker_size,
        marker_size,
        fill=1,
    )
    c.rect(margin, margin, marker_size, marker_size, fill=1)
    c.rect(
        page_width - margin - marker_size,
        margin,
        marker_size,
        marker_size,
        fill=1,
    )

    # Header Details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, page_height - 45, f"Exam Code: {exam_id}")
    c.drawString(70, page_height - 65, f"Group: {group_name}")

    if is_reference:
        c.setFillColorRGB(0.8, 0.1, 0.1)
        c.drawString(
            70,
            page_height - 85,
            f"OFFICIAL ANSWER KEY - FORM {form_type}",
        )
        c.setFillColorRGB(0, 0, 0)
    else:
        c.drawString(
            70,
            page_height - 85,
            f"Form: {form_type} (10 Questions / Max Grade: 10)",
        )

    c.setFont("Helvetica", 11)
    c.drawString(70, page_height - 105, f"ID / Code: {student_id}")

    # Right-aligned Arabic Name
    formatted_name = format_arabic(student_name)
    c.setFont(FONT_NAME, 14)
    c.drawRightString(page_width - 160, page_height - 45, formatted_name)

    # QR Code payload
    qr_payload = json.dumps(
        {
            "is_reference": is_reference,
            "group": str(group_name),
            "student_id": str(student_id),
            "student_name": str(student_name),
            "exam_id": str(exam_id),
            "form": str(form_type),
        }
    )
    qr_img = qrcode.make(qr_payload)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    c.drawImage(
        canvas.ImageReader(qr_buffer),
        page_width - 130,
        page_height - 135,
        width=85,
        height=85,
    )

    # 10 Bubbles Grid
    y_start = page_height - 180
    options = ["A", "B", "C", "D"]
    for q_idx in range(1, num_questions + 1):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y_start, f"{q_idx:02d}.")
        for opt_idx, opt in enumerate(options):
            x_pos = 120 + (opt_idx * 45)
            c.circle(x_pos, y_start + 4, 10, stroke=1, fill=0)
            c.setFont("Helvetica", 9)
            c.drawString(x_pos - 3, y_start + 1, opt)
        y_start -= 32

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def decode_sheet_qr(image_np):
    qr_detector = cv2.QRCodeDetector()
    data, _, _ = qr_detector.detectAndDecode(image_np)
    if data:
        try:
            return json.loads(data)
        except Exception:
            pass
    return None


def scan_bubbles_from_image(image_bytes, num_questions=10):
    np_img = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    if image is None:
        return None, None, "Invalid image format uploaded."

    qr_meta = decode_sheet_qr(image)

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
        if 12 <= w <= 60 and 12 <= h <= 60 and 0.75 <= ar <= 1.25:
            bubble_contours.append(c)

    if not bubble_contours:
        return None, qr_meta, "No bubbles detected."

    bubble_contours = sorted(
        bubble_contours, key=lambda c: cv2.boundingRect(c)[1]
    )

    rows = []
    current_row = []
    prev_y = None
    y_threshold = 15

    for cnt in bubble_contours:
        _, y, _, _ = cv2.boundingRect(cnt)
        if prev_y is None or abs(y - prev_y) <= y_threshold:
            current_row.append(cnt)
        else:
            rows.append(current_row)
            current_row = [cnt]
        prev_y = y

    if current_row:
        rows.append(current_row)

    options = ["A", "B", "C", "D"]
    answers = {}

    for q_idx in range(1, num_questions + 1):
        if q_idx - 1 >= len(rows):
            break

        row_contours = sorted(rows[q_idx - 1], key=lambda c: cv2.boundingRect(c)[0])
        marked_idx = None
        max_pixels = 0

        for opt_idx, cnt in enumerate(row_contours[:4]):
            mask = np.zeros(thresh.shape, dtype="uint8")
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            mask = cv2.bitwise_and(thresh, thresh, mask=mask)
            total_pixels = cv2.countNonZero(mask)

            if total_pixels > max_pixels and total_pixels > 120:
                max_pixels = total_pixels
                marked_idx = opt_idx

        answers[str(q_idx)] = (
            options[marked_idx] if (marked_idx is not None and marked_idx < 4) else "None"
        )

    return answers, qr_meta, None


def find_best_name_match(query_name, candidate_names, cutoff=0.55):
    if not query_name or pd.isna(query_name):
        return None
    matches = difflib.get_close_matches(
        str(query_name), [str(c) for c in candidate_names], n=1, cutoff=cutoff
    )
    return matches[0] if matches else None


# --- STREAMLIT UI TABS ---
tab1, tab2, tab3 = st.tabs(
    [
        "Sheet & Attendance Generator",
        "Auto Grader & Attendance",
        "Master Consolidator",
    ]
)

with tab1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("1. Download Blank Reference Answer Keys (Form A & B)")
    col_ref_a, col_ref_b = st.columns(2)

    with col_ref_a:
        pdf_ref_a = draw_single_sheet(
            student_id="REF_KEY_FORM_A",
            student_name="مفتاح الإجابة النموذجية",
            group_name="ANSWER KEY",
            exam_id="DENT2025",
            form_type="A",
            num_questions=10,
            is_reference=True,
        )
        st.download_button(
            label="📄 Download Blank Reference Sheet (Form A)",
            data=pdf_ref_a,
            file_name="Reference_Key_Form_A.pdf",
            mime="application/pdf",
        )

    with col_ref_b:
        pdf_ref_b = draw_single_sheet(
            student_id="REF_KEY_FORM_B",
            student_name="مفتاح الإجابة النموذجية",
            group_name="ANSWER KEY",
            exam_id="DENT2025",
            form_type="B",
            num_questions=10,
            is_reference=True,
        )
        st.download_button(
            label="📄 Download Blank Reference Sheet (Form B)",
            data=pdf_ref_b,
            file_name="Reference_Key_Form_B.pdf",
            mime="application/pdf",
        )

    st.markdown("---")
    st.subheader("2. Generate Student Sheets & Printable Attendance Lists")
    col1, col2 = st.columns(2)

    with col1:
        exam_id = st.text_input("Exam Code or Title", "DENT2025")
        form_mode = st.radio(
            "Form Distribution Strategy",
            [
                "Alternate Form A and Form B per student",
                "All Form A",
                "All Form B",
            ],
        )

    with col2:
        roster_file = st.file_uploader(
            "Upload Roster Excel File (.xlsx)",
            type=["xlsx", "xls"],
            key="roster_gen",
        )

    if roster_file and exam_id:
        try:
            file_bytes = roster_file.read()
            df = parse_college_excel(file_bytes)

            if not df.empty:
                st.success(
                    f"Parsed {len(df)} total students across {len(df['group'].unique())} groups!"
                )

                if st.button("🚀 Generate Student Sheets & Attendance PDFs"):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(
                        zip_buffer, "w", zipfile.ZIP_DEFLATED
                    ) as zf:
                        # 1. Generate Student Bubble Sheets
                        for idx, row in df.iterrows():
                            group = str(row["group"])
                            s_id = str(row["student_id"])
                            s_name = str(row["student_name"])

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
                                num_questions=10,
                                is_reference=False,
                            )

                            clean_name = s_name.replace(" ", "_")
                            file_path = f"Group_{group}/Form_{current_form}_sheet_{s_id}_{clean_name}.pdf"
                            zf.writestr(file_path, pdf_bytes)

                        # 2. Generate Group Attendance PDFs
                        for group_name, group_df in df.groupby("group"):
                            students_list = group_df.to_dict("records")
                            att_pdf = generate_attendance_pdf(
                                group_name, students_list, exam_id
                            )
                            zf.writestr(
                                f"Group_{group_name}/Attendance_Sheet_Group_{group_name}.pdf",
                                att_pdf,
                            )

                    zip_buffer.seek(0)
                    st.download_button(
                        label="📥 Download Student Sheets & Attendance Sheets (ZIP)",
                        data=zip_buffer,
                        file_name=f"{exam_id}_Sheets_And_Attendance.zip",
                        mime="application/zip",
                    )
        except Exception as e:
            st.error(f"Error processing file: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("Upload Reference Answer Keys & Batch Grade Papers")

    col_a, col_b = st.columns(2)
    with col_a:
        key_img_a = st.file_uploader(
            "Upload Filled Reference Photo for Form A",
            type=["jpg", "png", "jpeg"],
            key="key_a",
        )
    with col_b:
        key_img_b = st.file_uploader(
            "Upload Filled Reference Photo for Form B",
            type=["jpg", "png", "jpeg"],
            key="key_b",
        )

    answer_key_a = None
    answer_key_b = None

    if key_img_a:
        key_a_bytes = key_img_a.read()
        answer_key_a, qr_meta_a, err_a = scan_bubbles_from_image(key_a_bytes, num_questions=10)
        if err_a:
            st.error(f"Form A Reference Key Error: {err_a}")
        else:
            st.success("Form A Reference Key loaded successfully!")

    if key_img_b:
        key_b_bytes = key_img_b.read()
        answer_key_b, qr_meta_b, err_b = scan_bubbles_from_image(key_b_bytes, num_questions=10)
        if err_b:
            st.error(f"Form B Reference Key Error: {err_b}")
        else:
            st.success("Form B Reference Key loaded successfully!")

    st.markdown("---")
    st.subheader("📁 Batch Upload Student Exam Photos (Auto-Tracks Attendance)")

    roster_file_grade = st.file_uploader(
        "Upload Roster Excel File to sync results into",
        type=["xlsx", "xls"],
        key="roster_grade",
    )
    mixed_student_imgs = st.file_uploader(
        "Upload Mixed Student Exam Photos",
        type=["jpg", "png", "jpeg"],
        accept_multiple_files=True,
    )

    if st.button("⚡ Process All Papers & Grade Out of 10"):
        if not roster_file_grade:
            st.error("Please upload the Roster Excel file.")
        elif not answer_key_a and not answer_key_b:
            st.error("Please upload at least one Reference Key Photo (Form A or Form B).")
        elif not mixed_student_imgs:
            st.error("Please upload student photos.")
        else:
            roster_bytes = roster_file_grade.read()
            df_students = parse_college_excel(roster_bytes)

            df_students["Form"] = "N/A"
            df_students["Attendance"] = "Absent"
            df_students["Grade (/10)"] = "N/A"

            graded_count = 0
            progress_bar = st.progress(0)

            for idx, student_file in enumerate(mixed_student_imgs):
                s_bytes = student_file.read()
                s_answers, qr_meta, err = scan_bubbles_from_image(s_bytes, num_questions=10)

                if err or not s_answers:
                    st.warning(f"Could not read bubbles for {student_file.name}: {err}")
                    continue

                student_id = qr_meta.get("student_id") if qr_meta else None
                form_detected = qr_meta.get("form", "A") if qr_meta else "A"

                target_key = answer_key_a if form_detected == "A" else answer_key_b
                if not target_key:
                    st.warning(f"Skipped {student_file.name}: No reference key loaded for Form {form_detected}.")
                    continue

                correct_count = 0
                for q_idx in range(1, 11):
                    q_str = str(q_idx)
                    if s_answers.get(q_str) == target_key.get(q_str) and s_answers.get(q_str) != "None":
                        correct_count += 1

                score_out_of_10 = float(correct_count)

                if student_id and student_id in df_students["student_id"].values:
                    df_students.loc[df_students["student_id"] == student_id, "Form"] = form_detected
                    df_students.loc[df_students["student_id"] == student_id, "Attendance"] = "Present"
                    df_students.loc[df_students["student_id"] == student_id, "Grade (/10)"] = score_out_of_10
                    graded_count += 1

                progress_bar.progress((idx + 1) / len(mixed_student_imgs))

            st.success(f"Grading Complete! Graded {graded_count} student papers and recorded attendance.")
            st.dataframe(df_students)

            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                df_students.to_excel(writer, index=False, sheet_name="Exam Results Out of 10")
            output_excel.seek(0)

            st.download_button(
                label="📊 Download Graded & Attendance Excel File",
                data=output_excel,
                file_name="Exam_Grades_And_Attendance.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("AI Master Excel Consolidator")

    master_excel_file = st.file_uploader(
        "Upload Master Reference Excel Sheet",
        type=["xlsx", "xls"],
        key="master_ref",
    )
    group_excel_files = st.file_uploader(
        "Upload Graded Group Excel Files",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="group_excels",
    )

    if st.button("🤖 Auto-Consolidate & Align Grades with AI Match"):
        if not master_excel_file:
            st.error("Please upload the Master Reference Excel file.")
        elif not group_excel_files:
            st.error("Please upload at least one group Excel file.")
        else:
            try:
                master_df = pd.read_excel(master_excel_file)
                name_col_master = None
                for col in master_df.columns:
                    if "اسم" in str(col) or "Name" in str(col).capitalize():
                        name_col_master = col
                        break

                if not name_col_master:
                    name_col_master = (
                        master_df.columns[1]
                        if len(master_df.columns) > 1
                        else master_df.columns[0]
                    )

                master_df["Exam_Grade_Out_Of_10"] = "N/A"
                master_df["Attendance_Status"] = "Absent"
                master_df["Matched_Form"] = "N/A"

                total_matched = 0

                for g_file in group_excel_files:
                    g_df = pd.read_excel(g_file)

                    for _, g_row in g_df.iterrows():
                        g_name = g_row.get("student_name") or g_row.get("Name")
                        g_grade = g_row.get("Grade (/10)", "N/A")
                        g_att = g_row.get("Attendance", "Absent")
                        g_form = g_row.get("Form", "N/A")

                        if pd.notna(g_name) and g_grade != "N/A":
                            matched_name = find_best_name_match(
                                g_name,
                                master_df[name_col_master].values,
                                cutoff=0.55,
                            )

                            if matched_name:
                                master_df.loc[
                                    master_df[name_col_master] == matched_name,
                                    "Exam_Grade_Out_Of_10",
                                ] = g_grade
                                master_df.loc[
                                    master_df[name_col_master] == matched_name,
                                    "Attendance_Status",
                                ] = g_att
                                master_df.loc[
                                    master_df[name_col_master] == matched_name,
                                    "Matched_Form",
                                ] = g_form
                                total_matched += 1

                st.success(
                    f"AI Alignment Complete! Successfully matched {total_matched} students with grades and attendance."
                )
                st.dataframe(master_df)

                master_output = io.BytesIO()
                with pd.ExcelWriter(master_output, engine="openpyxl") as writer:
                    master_df.to_excel(
                        writer, index=False, sheet_name="Master Final Grades"
                    )
                master_output.seek(0)

                st.download_button(
                    label="📥 Download Consolidated Master Excel File",
                    data=master_output,
                    file_name="Master_Final_Consolidated_Grades.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                st.error(f"Error consolidating files: {e}")
    st.markdown("</div>", unsafe_allow_html=True)
