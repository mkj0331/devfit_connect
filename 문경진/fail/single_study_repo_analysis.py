# study repo 분석 전용

import os
import json
import re
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ==============================
# 1. 설정
# ==============================
OWNER = "thstmddns"
REPO = "algorithm-study"   # 공부 레포

BASE_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl"
SUMMARY_DIR = os.path.join(BASE_DIR, "summary")
REPO_SUMMARY_DIR = os.path.join(SUMMARY_DIR, "repo_divided_summary")
COMMIT_SUMMARY_PATH = os.path.join(
    SUMMARY_DIR, "commit_summary", f"{OWNER}_{REPO}_commit_summary.json"
)

MODEL_NAME = "gpt-4o-mini"

client = OpenAI(
    api_key=os.getenv("GMS_API_KEY"),
    base_url=os.getenv("GMS_BASE_URL")
)

# ==============================
# 2. 요약 파일 로드
# ==============================
def load_repo_file_summaries(summary_dir: str) -> List[Dict]:
    summaries = []
    for filename in os.listdir(summary_dir):
        if filename.endswith(".json"):
            with open(os.path.join(summary_dir, filename), "r", encoding="utf-8") as f:
                summaries.append(json.load(f))
    return summaries


def load_commit_summary(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ==============================
# 3. Study Repo 출력 스키마
# ==============================
OUTPUT_SCHEMA = """
{
  "study_domain": "",
  "difficulty_level": "",

  "study_topics": [],

  "learning_style": {
    "type": "",
    "characteristics": []
  },

  "core_concepts": [
    {
      "concept_name": "",
      "description": "",
      "evidence_code_paths": []
    }
  ],

  "growth_signals": [],

  "study_persona": {
    "type": "",
    "strengths": []
  },

  "next_learning_recommendations": []
}
"""

# ==============================
# 4. LLM 프롬프트
# ==============================
def build_prompt(repo_summaries, commit_summary):
    return f"""
너는 **개발자 공부 레포지토리 분석 AI**다.

아래에 제공된:
- 파일 단위 코드 요약
- 커밋 메시지 요약

을 기반으로,
해당 레포지토리를 **학습 관점에서 분석**하라.

---

## 분석 시 반드시 포함할 관점

1. 이 레포의 **학습 주제와 범위**
2. 전반적인 **난이도 수준**
3. 개발자의 **학습 방식**
   - 문제 풀이 반복형 / 개념 정리형 / 실험형 등
4. 코드와 주석에서 드러나는 **핵심 학습 개념**
5. 커밋 및 코드 변화에서 보이는 **성장 흔적**
6. 이 레포가 보여주는 **학습자 성향(Persona)**
7. 다음 단계로 추천할 **추가 학습 방향**

---

### 출력 규칙 (매우 중요)
- JSON 형식으로만 출력
- 모든 판단은 제공된 코드/커밋 요약에 근거
- 기술명은 영어 유지
- 설명은 한국어

---

## 파일 단위 코드 요약
{json.dumps(repo_summaries, ensure_ascii=False)}

---

## 커밋 요약
{json.dumps(commit_summary, ensure_ascii=False)}

---

## 출력 예시(JSON)
{OUTPUT_SCHEMA}
"""

# ==============================
# 5. LLM 호출
# ==============================
def analyze_with_llm(prompt: str) -> str:
    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        temperature=0.2
    )
    return response.output_text

# ==============================
# 6. JSON 안전 파싱
# ==============================
def safe_json_loads(llm_output: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", llm_output).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON 파싱 실패")
    return json.loads(cleaned[start:end + 1])

# ==============================
# 7. 실행
# ==============================
if __name__ == "__main__":
    print("📂 코드 요약 로드 중...")
    repo_summaries = load_repo_file_summaries(REPO_SUMMARY_DIR)

    print("📂 커밋 요약 로드 중...")
    commit_summary = load_commit_summary(COMMIT_SUMMARY_PATH)

    print("🧠 프롬프트 구성...")
    prompt = build_prompt(repo_summaries, commit_summary)
    print(f"Prompt length: {len(prompt)}")

    print("🚀 Study Repo 분석 요청...")
    raw_result = analyze_with_llm(prompt)

    result = safe_json_loads(raw_result)

    # PK
    result["repo_analysis_id"] = f"{OWNER}/{REPO}"
    result["repo_type"] = "study"

    save_dir = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\single_repo_analysis"
    os.makedirs(save_dir, exist_ok=True)

    output_path = os.path.join(
        save_dir, f"{OWNER}_{REPO}_study_analysis.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ Study Repo 분석 완료!\n저장 위치:\n{output_path}")
