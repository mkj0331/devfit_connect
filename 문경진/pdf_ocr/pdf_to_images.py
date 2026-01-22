from pdf2image import convert_from_path
import os

# ====== 설정 ======
PDF_PATH = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\문경진_Portfolio.pdf"   # <-- 네 PDF 파일명
OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\pages"         # 이미지 저장 폴더
DPI = 200

# Poppler 경로 (PATH 안 잡혀있으니 직접 지정)
POPPLER_PATH = r"C:\Users\SSAFY\Downloads\poppler-25.12.0\Library\bin"

# ==================

def split_pdf_to_images(PDF_PATH, OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    images = convert_from_path(
        PDF_PATH,
        dpi=DPI,
        poppler_path=POPPLER_PATH
    )

    image_paths = []

    for i, img in enumerate(images):
        path = os.path.join(OUTPUT_DIR, f"page_{i+1}.png")
        img.save(path, "PNG")
        image_paths.append(path)

    print(f"✅ 총 {len(image_paths)} 페이지 분해 완료")
    return image_paths


if __name__ == "__main__":
    split_pdf_to_images()
