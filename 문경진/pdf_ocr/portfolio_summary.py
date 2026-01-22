from pdf_to_images import split_pdf_to_images
from paddleOCR import portfolio_paddleocr
from structure_portfolio import structure_portfolio_from_ocr
import os

# ====== 설정 ======
PDF_PATH = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\문경진_Portfolio.pdf"   # <-- 네 PDF 파일명
PAGE_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\pages"         # 이미지 저장 폴더
OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\output"

# 이미지로 스플릿
split_pdf_to_images(PDF_PATH=PDF_PATH, OUTPUT_DIR=PAGE_DIR)

portfolio_paddleocr(PAGE_DIR=PAGE_DIR, OUTPUT_DIR=OUTPUT_DIR)

INPUT_JSON = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\output\portfolio_ocr_result.json"
OUTPUT_JSON = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\output\portfolio_structured_summary.json"

structure_portfolio_from_ocr(input_json_path=INPUT_JSON, output_json_path=OUTPUT_JSON)
