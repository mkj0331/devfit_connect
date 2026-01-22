import os, json
from paddleocr import PaddleOCR

PAGE_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\pages"
OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\output"
OUTPUT_FILE = "portfolio_ocr_result.json"

ocr = PaddleOCR(
    lang="korean",
    use_gpu=False,
    det=True,
    rec=True,
    cls=False,          # 각도 분류 완전 OFF
    enable_mkldnn=False,
    cpu_threads=1,
    show_log=False
)

def portfolio_paddleocr(PAGE_DIR, OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    res = {}

    files = sorted(
        [f for f in os.listdir(PAGE_DIR) if f.endswith(".png")],
        key=lambda x: int("".join(filter(str.isdigit, x)) or 0)
    )

    for f in files:
        print("OCR:", f)
        out = ocr.ocr(os.path.join(PAGE_DIR, f), cls=False)
        texts = [t for _, (t, s) in out[0]] if out else []
        res[f] = texts

    with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), "w", encoding="utf-8") as fp:
        json.dump(res, fp, ensure_ascii=False, indent=2)

    print("✅ DONE")

if __name__ == "__main__":
    portfolio_paddleocr()
