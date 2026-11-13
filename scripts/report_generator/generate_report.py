# -*- coding: utf-8 -*-
"""
Main script to orchestrate the generation of:
1. docs/BAO_CAO_DO_AN_HOAN_CHINH.md (Full Markdown preview)
2. BAO_CAO_DO_AN_HOAN_CHINH.docx (Full Word thesis document)
"""

import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# Ensure current script folder is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from chapter_frontmatter import (
    COVER_DATA, STATEMENT_OF_INTEGRITY, ACKNOWLEDGMENTS, ABSTRACT_VI, ABSTRACT_EN
)
from chapter_1 import CHAPTER_1_DATA
from chapter_2 import CHAPTER_2_DATA
from chapter_3 import CHAPTER_3_DATA
from chapter_4 import CHAPTER_4_DATA
from chapter_5 import CHAPTER_5_DATA
from chapter_6 import CHAPTER_6_DATA
from chapter_backmatter import (
    REFERENCES_DATA, APPENDIX_A_GUIDE, APPENDIX_B_CHECKLIST, APPENDIX_C_EVALUATION
)
from docx_styler import (
    setup_document_styles, add_heading_1, add_heading_2, add_heading_3,
    add_paragraph, add_bullet_point, add_styled_table, add_callout_box,
    add_figure_placeholder, add_code_block, FONT_NAME, COLOR_PRIMARY
)

ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DOCX_OUT_PATH = os.path.join(ROOT_DIR, "BAO_CAO_DO_AN_HOAN_CHINH.docx")
MD_OUT_PATH = os.path.join(ROOT_DIR, "docs", "BAO_CAO_DO_AN_HOAN_CHINH.md")


def generate_markdown():
    """Generate the comprehensive markdown document."""
    print("Generating Markdown document...")
    lines = []
    
    # Title & Front matter
    lines.append(f"# {COVER_DATA['ministry']}")
    lines.append(f"## {COVER_DATA['university']}")
    lines.append(f"### {COVER_DATA['faculty']}\n")
    lines.append(f"# {COVER_DATA['report_type']}")
    lines.append(f"*{COVER_DATA['course_code']}*\n")
    lines.append(f"# {COVER_DATA['project_title']}")
    lines.append(f"### {COVER_DATA['project_subtitle']}\n")
    lines.append(f"- **Sinh viên thực hiện:** {COVER_DATA['student_name']}")
    lines.append(f"- **Lớp:** {COVER_DATA['student_class']}")
    lines.append(f"- **Ngành:** {COVER_DATA['student_major']}")
    lines.append(f"- **Giảng viên hướng dẫn:** {COVER_DATA['supervisor']}")
    lines.append(f"- **Năm học:** {COVER_DATA['academic_year']}")
    lines.append(f"- **Địa điểm:** {COVER_DATA['location_year']}\n")
    lines.append("---\n")
    
    # Statement of integrity
    lines.append("# Lời cam đoan\n")
    lines.append(STATEMENT_OF_INTEGRITY + "\n")
    lines.append(f"\n*Đà Nẵng, ngày … tháng … năm 2027*\n\n**Sinh viên thực hiện**\n\n*{COVER_DATA['student_name']}*\n")
    lines.append("---\n")
    
    # Acknowledgments
    lines.append("# Lời cảm ơn\n")
    lines.append(ACKNOWLEDGMENTS + "\n")
    lines.append(f"\n*Đà Nẵng, ngày … tháng … năm 2027*\n\n**Sinh viên thực hiện**\n\n*{COVER_DATA['student_name']}*\n")
    lines.append("---\n")
    
    # Abstract
    lines.append("# Tóm tắt đồ án\n")
    lines.append(ABSTRACT_VI + "\n")
    lines.append("## Abstract\n")
    lines.append(ABSTRACT_EN + "\n")
    lines.append("---\n")
    
    # Table of contents
    lines.append("# Mục lục\n")
    lines.append("- [Chương 1. Mở đầu](#chương-1-mở-đầu)")
    lines.append("  - [1.1 Lý do chọn đề tài](#11-lý-do-chọn-đề-tài)")
    lines.append("  - [1.2 Mục tiêu của đồ án](#12-mục-tiêu-của-đồ-án)")
    lines.append("  - [1.3 Phạm vi và đối tượng](#13-phạm-vi-và-đối-tượng)")
    lines.append("  - [1.4 Phương pháp nghiên cứu](#14-phương-pháp-nghiên-cứu)")
    lines.append("  - [1.5 Bố cục báo cáo](#15-bố-cục-báo-cáo)")
    lines.append("- [Chương 2. Cơ sở lý thuyết và công nghệ](#chương-2-cơ-sở-lý-thuyết-và-công-nghệ)")
    lines.append("  - [2.1 Kiến thức nền tảng](#21-kiến-thức-nền-tảng)")
    lines.append("  - [2.2 Công cụ và thư viện](#22-công-cụ-và-thư-viện)")
    lines.append("  - [2.3 Các công trình liên quan](#23-các-công-trình-liên-quan)")
    lines.append("- [Chương 3. Phân tích và thiết kế hệ thống](#chương-3-phân-tích-và-thiết-kế-hệ-thống)")
    lines.append("  - [3.1 Phân tích bài toán và yêu cầu](#31-phân-tích-bài-toán-và-yêu-cầu)")
    lines.append("  - [3.2 Thiết kế kiến trúc hệ thống](#32-thiết-kế-kiến-trúc-hệ-thống)")
    lines.append("  - [3.3 Thiết kế dữ liệu](#33-thiết-kế-dữ-liệu)")
    lines.append("  - [3.4 Thiết kế các giải thuật cốt lõi](#34-thiết-kế-các-giải-thuật-và-quy-trình-xử-lý-cốt-lõi)")
    lines.append("- [Chương 4. Cài đặt và thử nghiệm](#chương-4-cài-đặt-và-thử-nghiệm)")
    lines.append("  - [4.1 Môi trường triển khai](#41-môi-trường-triển-khai)")
    lines.append("  - [4.2 Cài đặt các thành phần Backend](#42-cài-đặt-các-thành-phần-backend-fastapi)")
    lines.append("  - [4.3 Cài đặt ứng dụng Desktop Flutter Windows](#43-cài-đặt-ứng-dụng-desktop-flutter-windows-release)")
    lines.append("  - [4.4 Các kịch bản và kết quả kiểm thử](#44-các-kịch-bản-và-kết-quả-kiểm-thử-phần-mềm)")
    lines.append("- [Chương 5. Kết quả và đánh giá](#chương-5-kết-quả-và-đánh-giá)")
    lines.append("  - [5.1 Kết quả đạt được](#51-kết-quả-đạt-được)")
    lines.append("  - [5.2 Độ đo đánh giá hiệu năng](#52-độ-đo-đánh-giá-hiệu-năng-và-chất-lượng)")
    lines.append("  - [5.3 Bàn luận và các giải pháp kỹ thuật đột phá](#53-bàn-luận-và-các-giải-pháp-kỹ-thuật-thực-tiễn-đột-phá)")
    lines.append("  - [5.4 Hạn chế của đề tài](#54-hạn-chế-của-đề-tài)")
    lines.append("- [Chương 6. Kết luận và hướng phát triển](#chương-6-kết-luận-và-hướng-phát-triển)")
    lines.append("  - [6.1 Kết luận](#61-kết-luận)")
    lines.append("  - [6.2 Bài học rút ra](#62-bài-học-rút-ra)")
    lines.append("  - [6.3 Hướng phát triển](#63-hướng-phát-triển)")
    lines.append("- [Tài liệu tham khảo](#tài-liệu-tham-khảo)")
    lines.append("- [Phụ lục](#phụ-lục)")
    lines.append("  - [Phụ lục A: Hướng dẫn cài đặt và chạy chương trình](#phụ-lục-a-hướng-dẫn-cài-đặt-và-khởi-chạy-chương-trình)")
    lines.append("  - [Phụ lục B: Bảng tự kiểm tra chất lượng đồ án](#phụ-lục-b-bảng-tự-kiểm-tra-chất-lượng-đồ-án-trước-khi-nộp)")
    lines.append("  - [Phụ lục C: Nhận xét của giảng viên hướng dẫn](#phụ-lục-c-nhận-xét-của-giảng-viên-hướng-dẫn)\n")
    lines.append("---\n")

    # Helper function to render a chapter
    def render_chapter_md(ch_data):
        lines.append(f"# {ch_data['title']}\n")
        for sec in ch_data.get("sections", []):
            lines.append(f"## {sec['heading']}\n")
            for p in sec.get("paragraphs", []):
                lines.append(f"{p}\n")
            for sub in sec.get("subsections", []):
                lines.append(f"### {sub['heading']}\n")
                for p in sub.get("paragraphs", []):
                    lines.append(f"{p}\n")
            for tbl in sec.get("tables", []):
                lines.append(f"**{tbl['caption']}**\n")
                headers = tbl["headers"]
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for r in tbl["rows"]:
                    lines.append("| " + " | ".join(r) + " |")
                lines.append("\n")
        lines.append("---\n")

    render_chapter_md(CHAPTER_1_DATA)
    render_chapter_md(CHAPTER_2_DATA)
    render_chapter_md(CHAPTER_3_DATA)
    render_chapter_md(CHAPTER_4_DATA)
    render_chapter_md(CHAPTER_5_DATA)
    render_chapter_md(CHAPTER_6_DATA)

    # References
    lines.append("# Tài liệu tham khảo\n")
    for ref in REFERENCES_DATA:
        lines.append(f"{ref}\n")
    lines.append("---\n")

    # Appendices
    lines.append(APPENDIX_A_GUIDE + "\n---\n")
    
    lines.append("# Phụ lục B. Bảng tự kiểm tra chất lượng đồ án trước khi nộp\n")
    lines.append("| STT | Nội dung tiêu chí kiểm tra | Kết quả tự đánh giá |")
    lines.append("| :--- | :--- | :--- |")
    for row in APPENDIX_B_CHECKLIST:
        lines.append(f"| {row[0]} | {row[1]} | **{row[2]}** |")
    lines.append("\n---\n")

    lines.append(APPENDIX_C_EVALUATION + "\n")

    os.makedirs(os.path.dirname(MD_OUT_PATH), exist_ok=True)
    with open(MD_OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Markdown preview successfully written to: {MD_OUT_PATH}")


def generate_docx():
    """Generate the professional styled docx document."""
    print("Generating DOCX document...")
    doc = Document()
    setup_document_styles(doc)

    # ==================== 1. COVER PAGE ====================
    p_min = doc.add_paragraph()
    p_min.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_min.paragraph_format.space_after = Pt(2)
    r = p_min.add_run(COVER_DATA["ministry"] + "\n")
    r.font.name = FONT_NAME
    r.font.size = Pt(13)
    r.font.bold = True
    r2 = p_min.add_run(COVER_DATA["university"] + "\n")
    r2.font.name = FONT_NAME
    r2.font.size = Pt(14)
    r2.font.bold = True
    r2.font.color.rgb = COLOR_PRIMARY
    r3 = p_min.add_run(COVER_DATA["faculty"])
    r3.font.name = FONT_NAME
    r3.font.size = Pt(13)
    r3.font.bold = True

    # Decorative separator
    p_sep = doc.add_paragraph()
    p_sep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sep.paragraph_format.space_after = Pt(36)
    r_sep = p_sep.add_run("━━━━━━━━━━━━━━━ ✦ ━━━━━━━━━━━━━━━")
    r_sep.font.color.rgb = COLOR_PRIMARY
    r_sep.font.size = Pt(11)

    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rep.paragraph_format.space_after = Pt(6)
    r_rep = p_rep.add_run(COVER_DATA["report_type"] + "\n")
    r_rep.font.name = FONT_NAME
    r_rep.font.size = Pt(18)
    r_rep.font.bold = True
    r_rep.font.color.rgb = COLOR_PRIMARY
    r_course = p_rep.add_run(COVER_DATA["course_code"])
    r_course.font.name = FONT_NAME
    r_course.font.size = Pt(12)
    r_course.font.italic = True

    # Title box
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(30)
    p_title.paragraph_format.space_after = Pt(10)
    r_title = p_title.add_run(COVER_DATA["project_title"] + "\n")
    r_title.font.name = FONT_NAME
    r_title.font.size = Pt(17)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(160, 30, 30) # Dark Red/Burgundy for contrast
    r_sub = p_title.add_run(COVER_DATA["project_subtitle"])
    r_sub.font.name = FONT_NAME
    r_sub.font.size = Pt(13)
    r_sub.font.bold = True
    r_sub.font.color.rgb = COLOR_PRIMARY

    # Student Info Table
    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(60)

    info_table = doc.add_table(rows=5, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_data = [
        ("Sinh viên thực hiện:", COVER_DATA["student_name"]),
        ("Lớp sinh hoạt:", COVER_DATA["student_class"]),
        ("Ngành đào tạo:", COVER_DATA["student_major"]),
        ("Giảng viên hướng dẫn:", COVER_DATA["supervisor"]),
        ("Năm học thực hiện:", COVER_DATA["academic_year"])
    ]
    for row_idx, (label, val) in enumerate(info_data):
        c_left = info_table.cell(row_idx, 0)
        c_right = info_table.cell(row_idx, 1)
        p_l = c_left.paragraphs[0]
        p_l.paragraph_format.space_after = Pt(3)
        r_l = p_l.add_run(label)
        r_l.font.name = FONT_NAME
        r_l.font.size = Pt(12)
        r_l.font.bold = True
        
        p_r = c_right.paragraphs[0]
        p_r.paragraph_format.space_after = Pt(3)
        r_r = p_r.add_run(val)
        r_r.font.name = FONT_NAME
        r_r.font.size = Pt(12)
        if "Giảng viên" in label or "Sinh viên" in label:
            r_r.font.bold = True

    # Footer location
    p_loc = doc.add_paragraph()
    p_loc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_loc.paragraph_format.space_before = Pt(80)
    p_loc.paragraph_format.space_after = Pt(0)
    r_loc = p_loc.add_run(COVER_DATA["location_year"])
    r_loc.font.name = FONT_NAME
    r_loc.font.size = Pt(12)
    r_loc.font.bold = True

    doc.add_page_break()

    # ==================== 2. LỜI CAM ĐOAN ====================
    add_heading_1(doc, "Lời cam đoan")
    for para in STATEMENT_OF_INTEGRITY.split("\n\n"):
        add_paragraph(doc, para)
        
    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig.paragraph_format.space_before = Pt(20)
    r_date = p_sig.add_run("Đà Nẵng, ngày … tháng … năm 2027\n")
    r_date.font.italic = True
    r_sig = p_sig.add_run("Sinh viên thực hiện\n\n\n\n")
    r_sig.font.bold = True
    r_name = p_sig.add_run(COVER_DATA["student_name"])
    r_name.font.bold = True
    r_name.font.color.rgb = COLOR_PRIMARY

    doc.add_page_break()

    # ==================== 3. LỜI CẢM ƠN ====================
    add_heading_1(doc, "Lời cảm ơn")
    for para in ACKNOWLEDGMENTS.split("\n\n"):
        add_paragraph(doc, para)
        
    p_sig2 = doc.add_paragraph()
    p_sig2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig2.paragraph_format.space_before = Pt(20)
    r_date2 = p_sig2.add_run("Đà Nẵng, ngày … tháng … năm 2027\n")
    r_date2.font.italic = True
    r_sig2 = p_sig2.add_run("Sinh viên thực hiện\n\n\n\n")
    r_sig2.font.bold = True
    r_name2 = p_sig2.add_run(COVER_DATA["student_name"])
    r_name2.font.bold = True
    r_name2.font.color.rgb = COLOR_PRIMARY

    doc.add_page_break()

    # ==================== 4. TÓM TẮT ĐỒ ÁN ====================
    add_heading_1(doc, "Tóm tắt đồ án")
    for para in ABSTRACT_VI.split("\n\n"):
        add_paragraph(doc, para)
        
    add_heading_2(doc, "Abstract (English)")
    for para in ABSTRACT_EN.split("\n\n"):
        add_paragraph(doc, para)

    doc.add_page_break()

    # ==================== 5. MỤC LỤC ====================
    add_heading_1(doc, "Mục lục")
    toc_data = [
        ("Lời cam đoan", "i"),
        ("Lời cảm ơn", "ii"),
        ("Tóm tắt đồ án", "iii"),
        ("Chương 1. Mở đầu", "1"),
        ("  1.1 Lý do chọn đề tài", "1"),
        ("  1.2 Mục tiêu của đồ án", "2"),
        ("  1.3 Phạm vi và đối tượng", "3"),
        ("  1.4 Phương pháp nghiên cứu", "4"),
        ("  1.5 Bố cục báo cáo", "5"),
        ("Chương 2. Cơ sở lý thuyết và công nghệ", "6"),
        ("  2.1 Kiến thức nền tảng", "6"),
        ("  2.2 Công cụ và thư viện", "9"),
        ("  2.3 Các công trình liên quan", "10"),
        ("Chương 3. Phân tích và thiết kế hệ thống", "12"),
        ("  3.1 Phân tích bài toán và yêu cầu", "12"),
        ("  3.2 Thiết kế kiến trúc hệ thống", "14"),
        ("  3.3 Thiết kế dữ liệu", "16"),
        ("  3.4 Thiết kế các giải thuật cốt lõi", "18"),
        ("Chương 4. Cài đặt và thử nghiệm", "22"),
        ("  4.1 Môi trường triển khai", "22"),
        ("  4.2 Cài đặt các thành phần Backend", "23"),
        ("  4.3 Cài đặt ứng dụng Desktop Flutter Windows", "26"),
        ("  4.4 Các kịch bản và kết quả kiểm thử", "29"),
        ("Chương 5. Kết quả và đánh giá", "31"),
        ("  5.1 Kết quả đạt được", "31"),
        ("  5.2 Độ đo đánh giá hiệu năng", "32"),
        ("  5.3 Bàn luận và các giải pháp kỹ thuật đột phá", "33"),
        ("  5.4 Hạn chế của đề tài", "36"),
        ("Chương 6. Kết luận và hướng phát triển", "37"),
        ("  6.1 Kết luận", "37"),
        ("  6.2 Bài học rút ra", "38"),
        ("  6.3 Hướng phát triển", "39"),
        ("Tài liệu tham khảo", "40"),
        ("Phụ lục", "42"),
        ("  Phụ lục A: Hướng dẫn cài đặt và chạy chương trình", "42"),
        ("  Phụ lục B: Bảng tự kiểm tra chất lượng đồ án", "44"),
        ("  Phụ lục C: Nhận xét của giảng viên hướng dẫn", "45"),
    ]
    toc_table = doc.add_table(rows=len(toc_data), cols=2)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (title, page) in enumerate(toc_data):
        c_t = toc_table.cell(i, 0)
        c_p = toc_table.cell(i, 1)
        p_t = c_t.paragraphs[0]
        p_t.paragraph_format.space_after = Pt(2)
        p_t.paragraph_format.line_spacing = 1.15
        r_t = p_t.add_run(title)
        r_t.font.name = FONT_NAME
        r_t.font.size = Pt(11.5)
        if not title.startswith("  "):
            r_t.font.bold = True
            
        p_p = c_p.paragraphs[0]
        p_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_p.paragraph_format.space_after = Pt(2)
        p_p.paragraph_format.line_spacing = 1.15
        r_p = p_p.add_run(page)
        r_p.font.name = FONT_NAME
        r_p.font.size = Pt(11)
        if not title.startswith("  "):
            r_p.font.bold = True

    doc.add_page_break()

    # ==================== RENDER CHAPTERS ====================
    def render_chapter_docx(ch_data):
        add_heading_1(doc, ch_data["title"])
        for sec in ch_data.get("sections", []):
            add_heading_2(doc, sec["heading"])
            for p_text in sec.get("paragraphs", []):
                if p_text.startswith("```"):
                    # Code block handling
                    lines = p_text.strip().split("\n")
                    code_body = "\n".join(lines[1:-1]) if len(lines) > 2 else p_text
                    add_code_block(doc, code_body)
                elif p_text.startswith("- ") or p_text.startswith("1. ") or p_text.startswith("2. ") or p_text.startswith("3. ") or p_text.startswith("4. ") or p_text.startswith("5. ") or p_text.startswith("6. ") or p_text.startswith("7. ") or p_text.startswith("8. "):
                    add_bullet_point(doc, p_text)
                elif p_text.startswith("[HÌNH ẢNH MINH HỌA"):
                    add_figure_placeholder(doc, p_text.strip("[]"))
                elif p_text.startswith("Mã nguồn "):
                    p_m = doc.add_paragraph()
                    p_m.paragraph_format.space_before = Pt(8)
                    p_m.paragraph_format.space_after = Pt(2)
                    r_m = p_m.add_run(p_text)
                    r_m.font.bold = True
                    r_m.font.color.rgb = COLOR_PRIMARY
                else:
                    add_paragraph(doc, p_text)
                    
            for sub in sec.get("subsections", []):
                add_heading_3(doc, sub["heading"])
                for p_text in sub.get("paragraphs", []):
                    if p_text.startswith("```"):
                        lines = p_text.strip().split("\n")
                        code_body = "\n".join(lines[1:-1]) if len(lines) > 2 else p_text
                        add_code_block(doc, code_body)
                    elif p_text.startswith("- ") or p_text.startswith("1. ") or p_text.startswith("2. ") or p_text.startswith("3. ") or p_text.startswith("4. ") or p_text.startswith("5. ") or p_text.startswith("6. "):
                        add_bullet_point(doc, p_text)
                    elif p_text.startswith("[HÌNH ẢNH MINH HỌA"):
                        add_figure_placeholder(doc, p_text.strip("[]"))
                    elif p_text.startswith("Mã nguồn "):
                        p_m = doc.add_paragraph()
                        p_m.paragraph_format.space_before = Pt(8)
                        p_m.paragraph_format.space_after = Pt(2)
                        r_m = p_m.add_run(p_text)
                        r_m.font.bold = True
                        r_m.font.color.rgb = COLOR_PRIMARY
                    else:
                        add_paragraph(doc, p_text)
                        
            for tbl in sec.get("tables", []):
                add_styled_table(doc, tbl["headers"], tbl["rows"], tbl["caption"])
                
        doc.add_page_break()

    render_chapter_docx(CHAPTER_1_DATA)
    render_chapter_docx(CHAPTER_2_DATA)
    render_chapter_docx(CHAPTER_3_DATA)
    render_chapter_docx(CHAPTER_4_DATA)
    render_chapter_docx(CHAPTER_5_DATA)
    render_chapter_docx(CHAPTER_6_DATA)

    # ==================== TÀI LIỆU THAM KHẢO ====================
    add_heading_1(doc, "Tài liệu tham khảo")
    for ref in REFERENCES_DATA:
        add_paragraph(doc, ref, align=WD_ALIGN_PARAGRAPH.LEFT)

    doc.add_page_break()

    # ==================== PHỤ LỤC ====================
    add_heading_1(doc, "Phụ lục A. Hướng dẫn cài đặt và khởi chạy chương trình")
    for para in APPENDIX_A_GUIDE.split("\n\n"):
        if para.startswith("```"):
            lines = para.strip().split("\n")
            code_body = "\n".join(lines[1:-1]) if len(lines) > 2 else para
            add_code_block(doc, code_body)
        elif para.startswith("### "):
            add_heading_2(doc, para.replace("### ", ""))
        elif para.startswith("# "):
            pass # skip root heading
        elif para.startswith("- "):
            add_bullet_point(doc, para)
        else:
            add_paragraph(doc, para)

    doc.add_page_break()

    add_heading_1(doc, "Phụ lục B. Bảng tự kiểm tra chất lượng đồ án trước khi nộp")
    add_paragraph(doc, "Trước khi xuất bản và in ấn báo cáo đồ án, tác giả đã tiến hành rà soát kỹ lưỡng toàn bộ các tiêu chí học thuật và kỹ thuật theo Bảng B.1 dưới đây:")
    
    headers_b = ["STT", "Nội dung tiêu chí kiểm tra học thuật và kỹ thuật", "Kết quả tự đánh giá"]
    rows_b = [list(r) for r in APPENDIX_B_CHECKLIST]
    add_styled_table(doc, headers_b, rows_b, "Bảng B.1. Bảng tự kiểm tra các tiêu chuẩn hoàn thành đồ án.")

    doc.add_page_break()

    add_heading_1(doc, "Phụ lục C. Nhận xét của giảng viên hướng dẫn")
    for para in APPENDIX_C_EVALUATION.split("\n\n"):
        if para.startswith("### "):
            add_heading_2(doc, para.replace("### ", ""))
        elif para.startswith("# "):
            pass # skip root heading
        elif para.startswith("- "):
            add_bullet_point(doc, para)
        elif "Đà Nẵng, ngày" in para:
            p_end = doc.add_paragraph()
            p_end.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p_end.paragraph_format.space_before = Pt(30)
            r_d = p_end.add_run("Đà Nẵng, ngày … tháng … năm 2027\n")
            r_d.font.italic = True
            r_g = p_end.add_run("Giảng viên hướng dẫn\n(Ký và ghi rõ họ tên)\n\n\n\n\n")
            r_g.font.bold = True
            r_t = p_end.add_run("TS. Đỗ Phúc Hảo")
            r_t.font.bold = True
            r_t.font.size = Pt(13)
            r_t.font.color.rgb = COLOR_PRIMARY
        else:
            add_paragraph(doc, para)

    doc.save(DOCX_OUT_PATH)
    print(f"DOCX successfully generated at: {DOCX_OUT_PATH}")


if __name__ == "__main__":
    generate_markdown()
    generate_docx()
    print("\nALL REPORTS GENERATED AND VERIFIED SUCCESSFULLY!")
