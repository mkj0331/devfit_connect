import json
import os
from openai import OpenAI
from dotenv import load_dotenv


def safe_json_load(text: str) -> dict:
    """
    LLM 응답에서 ```json 코드블록을 제거하고 안전하게 JSON 파싱
    """
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    return json.loads(text)


def structure_portfolio_from_ocr(
    input_json_path: str,
    output_json_path: str,
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.1,
) -> dict:
    """
    OCR 결과(JSON)를 입력으로 받아
    LLM(gpt-4o-mini)을 사용해 포트폴리오를 구조화한 JSON을 생성한다.

    Args:
        input_json_path (str): OCR 결과 JSON 파일 경로
        output_json_path (str): 구조화 결과 JSON 저장 경로
        model_name (str): 사용할 LLM 모델명
        temperature (float): LLM temperature

    Returns:
        dict: 구조화된 포트폴리오 JSON
    """

    # ==============================
    # 1. 환경 설정
    # ==============================
    load_dotenv()

    client = OpenAI(
        api_key=os.getenv("GMS_API_KEY"),
        base_url=os.getenv("GMS_GPT_BASE_URL")  # 예: https://api.gmst.ai/v1
    )

    # ==============================
    # 2. OCR 결과 로드
    # ==============================
    with open(input_json_path, "r", encoding="utf-8") as f:
        ocr_data = json.load(f)

    ocr_blocks = []
    for page, tokens in ocr_data.items():
        joined = " ".join(tokens)
        ocr_blocks.append(f"[{page}]\n{joined}")

    ocr_text = "\n\n".join(ocr_blocks)

    # ==============================
    # 3. 프롬프트 구성
    # ==============================
    prompt = f"""
너는 **개발자 포트폴리오 구조화 AI**다.

아래 텍스트는 PDF 포트폴리오를 OCR로 추출한 결과이며,
단어 단위로 분절되어 있고 노이즈가 섞여 있다.

이 OCR 결과를 바탕으로,
포트폴리오를 **채용 관점에서 의미 있는 구조화된 JSON 데이터**로 재구성하라.

---

## 필수 규칙
- 반드시 JSON 형식으로만 출력
- OCR 노이즈(기호, 단독 숫자, 깨진 단어)는 제거
- 명확히 드러난 정보만 사용하고 추측하지 말 것
- 기술명은 원문 표기를 최대한 유지
- name이나 contact와 같은 개인정보는 제거
---

## OCR 원본 텍스트
{ocr_text}
"""

    # ==============================
    # 4. LLM 호출
    # ==============================
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You extract structured information accurately."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
    )

    result_text = response.choices[0].message.content.strip()

    # ==============================
    # 5. JSON 파싱
    # ==============================
    try:
        structured_result = safe_json_load(result_text)
    except json.JSONDecodeError:
        raise ValueError(
            "LLM 응답이 JSON 형식이 아닙니다.\n\n=== RAW RESPONSE ===\n"
            + result_text
        )

    # ==============================
    # 6. 결과 저장
    # ==============================
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(structured_result, f, ensure_ascii=False, indent=2)

