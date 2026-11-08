import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.pdfgen import canvas

pdf_path = "/Users/nethan/.gemini/antigravity/scratch/reviewpulse/ReviewPulse_Presentation_Report.pdf"

class PresentationCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()
    def draw_decorations(self, page_count):
        self.saveState()
        self.setFillColor(colors.HexColor("#1E3A8A"))
        self.rect(0, 782, letter[0], 10, fill=1, stroke=0)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(40, 765, "REVIEWPULSE | ASPECT-BASED SENTIMENT ANALYSIS (ABSA)")
        self.drawRightString(letter[0] - 40, 765, "PROJECT & ARCHITECTURE PRESENTATION")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(40, 757, letter[0] - 40, 757)
        self.line(40, 42, letter[0] - 40, 42)
        self.setFont("Helvetica", 8)
        self.drawString(40, 30, "ReviewPulse - NLP & Streamlit Architecture Documentation")
        self.drawRightString(letter[0] - 40, 30, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()
doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=45, bottomMargin=50)
styles = getSampleStyleSheet()
c_navy = colors.HexColor("#1E3A8A")
c_teal = colors.HexColor("#0D9488")
c_slate = colors.HexColor("#0F172A")
c_border = colors.HexColor("#CBD5E1")
c_card_bg = colors.HexColor("#F8FAFC")

title_style = ParagraphStyle("SlideTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=c_navy, spaceAfter=3)
subtitle_style = ParagraphStyle("SlideSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=14, textColor=c_teal, spaceAfter=10)
section_h1 = ParagraphStyle("SectionH1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=c_navy, spaceBefore=8, spaceAfter=4, keepWithNext=True)
section_h2 = ParagraphStyle("SectionH2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=12.5, textColor=c_teal, spaceBefore=5, spaceAfter=2, keepWithNext=True)
body = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=c_slate, spaceAfter=4)
callout = ParagraphStyle("Callout", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=12.5, textColor=c_slate)
tbl_cell = ParagraphStyle("TCell", parent=styles["Normal"], fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=c_slate)
tbl_head = ParagraphStyle("THead", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10.5, textColor=colors.white)

elements = []
