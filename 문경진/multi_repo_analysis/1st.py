import json, requests
from dotenv import load_dotenv
import os, re

load_dotenv()

OWNER = 'HTTP501'

gms_api_key = os.getenv('GMS_API_KEY')
gms_base_url = os.getenv('GMS_BASE_URL')

def safe_json_load(text: str) -> dict:
    """
    LLM 출력에서
    - ```json ``` 코드블록 제거
    - 앞뒤 잡음 제거
    - JSON 파싱
    """
    if not text:
        raise ValueError("Empty response")

    # 1. 코드 블록 제거 (```json ... ```)
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())

    # 2. JSON 객체만 추출 (혹시 앞뒤 잡문이 있을 경우)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")

    text = text[start:end + 1]

    # 3. JSON 파싱
    return json.loads(text)

repo1_path = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\backend_single_analysis\HTTP501_idk_single_analysis.json"
with open(repo1_path, "r", encoding="utf-8") as f:
    repo1_analysis = json.load(f)

repo1_analysis_text = json.dumps(
    repo1_analysis,
    ensure_ascii=False,
    indent=2
)


portfolio_path = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\pdf_ocr\output\portfolio_structured_summary.json"
with open(portfolio_path, "r", encoding="utf-8") as f:
    structured_portfolio = json.load(f) 

portfolio_text = json.dumps(
    structured_portfolio,
    ensure_ascii=False,
    indent=2
) if structured_portfolio else "(제공되지 않음)"


repo2_analysis_text = None
repo3_analysis_text = None


prompt = f"""
너는 여러 프로젝트 분석 결과와 포트폴리오 정보를 종합하여,
지원자의 역량을 채용 시장 관점에서 표준화된 형태로 변환하는 AI다.

이 단계의 목적은
추천이나 평가가 아니라,
채용 공고와 비교 가능한 "역량 표현"을 생성하는 것이다.

---

## 중요 규칙 (반드시 준수)

- 제공된 입력 데이터 외의 정보는 절대 사용하지 마라.
- 개인적인 서사, 감정적 표현, 회사명, 프로젝트명 언급 금지.
- 출력은 반드시 JSON 형식만 허용한다.
- 설명 문장, 마크다운, 코드 블록을 절대 포함하지 마라.

---

## target_roles 규칙
- target_roles는 반드시 아래 값 중 하나다.
  - "Backend"
  - "Frontend"

---

## 출력 스키마

{{
  "target_roles": "",
  "core_skills": [string],
  "project_experience_summary": [string],
  "strength_keywords": [string]
}}

---

## 입력

[repo1 분석 결과]
{repo1_analysis_text}

[repo2 분석 결과]
{repo2_analysis_text}

[repo3 분석 결과]
{repo3_analysis_text}

[포트폴리오 구조화 요약]
{portfolio_text}
"""



def multi_repo_analysis(
    gms_api_key: str,
    gms_base_url: str,
    prompt
) -> str:

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gms_api_key,
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    response = requests.post(
        gms_base_url,
        headers=headers,
        json=payload,
        timeout=90
    )

    response.raise_for_status()
    data = response.json()

    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


raw_result = multi_repo_analysis(
    gms_api_key=gms_api_key,
    gms_base_url=gms_base_url,
    prompt=prompt
)

result = safe_json_load(raw_result)


output_dir = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\multi_repo_analysis"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, f"{OWNER}_multi_repo_analysis_result.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    
print(f"✅ 분석 결과 저장 완료: {output_path}")