import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# =========================
# 설정
# =========================
BASE_DIR = "crawling\output"
DART_DIR = os.path.join(BASE_DIR, "dart")
NEWS_DIR = os.path.join(BASE_DIR, "news")

client = OpenAI(
    api_key=os.getenv("GMS_API_KEY"),
    base_url=os.getenv("GMS_GPT_BASE_URL")
)  # OPENAI_API_KEY 환경변수 사용

MODEL = "gpt-4.1-mini"


# =========================
# 데이터 로딩
# =========================
def load_dart_info(company: str) -> str:
    dart_path = os.path.join(DART_DIR, f"{company}.txt")
    if not os.path.exists(dart_path):
        return ""
    with open(dart_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_news_info(company: str) -> list:
    news_path = os.path.join(NEWS_DIR, f"{company}.json")
    if not os.path.exists(news_path):
        return ""
    with open(news_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# 프롬프트 생성
# =========================
def build_prompt(company: str, dart_info: str, news_info: list) -> str:
    news_text = "\n".join(
        f"- ({n.get('date', '')}) {n.get('title', '')}: {n.get('content', '')}"
        for n in news_info
    )

    return f"""
너는 기업 분석 AI다.
아래에 제공된 자료만을 근거로 분석하라.
추측이나 외부 지식은 절대 사용하지 마라.

[기업명]
{company}

[사업의 개요 (DART)]
{dart_info if dart_info else "(제공되지 않음)"}

[최근 뉴스]
{news_text if news_text else "(제공되지 않음)"}

--- 출력 규칙 ---
- JSON 형식으로만 출력
- company_summary, recent_trend는 각각 **최대 3문장만 허용**

--- 출력 형식 ---
{{
  "company_summary": "이 기업은 …",
  "recent_trend": "최근 동향은 …"
}}
"""


# =========================
# LLM 호출
# =========================
def analyze_company(company: str) -> dict:
    dart_info = load_dart_info(company)
    news_info = load_news_info(company)

    prompt = build_prompt(company, dart_info, news_info)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "너는 사실 기반 기업 분석 전문가다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)


# =========================
# 실행 예시
# =========================
if __name__ == "__main__":
    company = "비바리퍼블리카"  # 사용자 입력
    result = analyze_company(company)

    output_dir = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\company_analysis"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{company}_analysis.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 기업 분석 결과 저장 완료: {output_path}")
