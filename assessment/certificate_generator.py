"""
PDF Certificate generator for top-performing students.
Uses fpdf2 to generate professional, styled certificates of achievement.
"""

import io
from fpdf import FPDF
from datetime import datetime

class CertificatePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, "Online Coding Assessment Platform | Verified Digital Credential", 0, 0, "C")


def generate_certificate_pdf(attempt) -> bytes:
    """
    Generates a landscape certificate of achievement PDF for a completed test attempt.
    """
    # Landscape orientation: 297mm width, 210mm height
    pdf = CertificatePDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Outer decorative border
    pdf.set_line_width(1.5)
    pdf.set_draw_color(30, 64, 175)  # Navy blue
    pdf.rect(10, 10, 277, 190)

    # Inner decorative border
    pdf.set_line_width(0.5)
    pdf.set_draw_color(234, 179, 8)  # Gold accent
    pdf.rect(14, 14, 269, 182)

    # Header / Org
    pdf.set_xy(20, 24)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(257, 8, "10000 CODERS ASSESSMENT PORTAL", 0, 1, "C")

    # Certificate Title
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(257, 14, "CERTIFICATE OF EXCELLENCE", 0, 1, "C")

    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(257, 10, "This is proudly presented to", 0, 1, "C")

    # Student Name
    student_name = attempt.student.user.get_full_name() or attempt.student.user.username
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(257, 14, student_name.upper(), 0, 1, "C")

    # Underline
    pdf.set_draw_color(234, 179, 8)
    pdf.set_line_width(1.0)
    pdf.line(70, pdf.get_y(), 227, pdf.get_y())
    pdf.ln(6)

    # Description
    roll_info = f"Roll Number: {attempt.student.roll_number}"
    if attempt.student.college:
        roll_info += f" | {attempt.student.college}"
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(257, 7, roll_info, 0, 1, "C")

    pdf.ln(2)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(51, 65, 85)
    body_text = (
        f"for outstanding performance in the '{attempt.test.title}' online examination, "
        f"scoring {attempt.score:.1f}/{attempt.total_marks:.1f} marks ({attempt.percentage:.1f}%) "
        f"with a completion time of {attempt.formatted_time_taken}."
    )
    pdf.multi_cell(257, 7, body_text, 0, "C")

    # Badges / Bottom Details
    completed_date = attempt.completed_at.strftime("%B %d, %Y") if attempt.completed_at else datetime.now().strftime("%B %d, %Y")
    cert_id = str(attempt.certificate.certificate_id)[:18] if hasattr(attempt, 'certificate') else "VERIFIED"

    pdf.set_xy(30, 148)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(80, 6, "DATE OF COMPLETION", 0, 1, "C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.set_x(30)
    pdf.cell(80, 6, completed_date, 0, 0, "C")

    pdf.set_xy(187, 148)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(80, 6, "CREDENTIAL ID", 0, 1, "C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.set_x(187)
    pdf.cell(80, 6, cert_id, 0, 0, "C")

    # Center Badge
    pdf.set_xy(110, 144)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(234, 179, 8)
    pdf.cell(77, 8, "[ TOP PERFORMER ]", 0, 1, "C")
    pdf.set_x(110)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(77, 6, "Authorized Examiner", 0, 0, "C")

    return bytes(pdf.output())
