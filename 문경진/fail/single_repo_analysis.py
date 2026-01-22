import os
import json
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ==============================
# 1. 설정
# ==============================
OWNER = "thstmddns"
REPO = "NaturalProject"

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
        if not filename.endswith(".json"):
            continue

        path = os.path.join(summary_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            summaries.append(data)

    return summaries


def load_commit_style_summary(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ==============================
# 3. 사용자 참고 텍스트
# ==============================
user_text_for_analysis = "나는 이 프로젝트에서 AI 역할 전반을 맡았어."

# ==============================
# 4. LLM 입력 프롬프트 구성
# ==============================

def build_prompt(repo_summaries, commit_summary):
    return f"""
너는 **개발자 레포지토리 종합 분석 AI**다.

아래에 제공된:
- **파일 단위 코드 요약 정보**
- **커밋 메시지 기반 개발 스타일 요약**
- **사용자가 제공한 분석 참고 텍스트**

를 종합하여,
사용자에게 아래 5가지를 **명확하고 구조적으로 분석**해서 제공하라.

### 반드시 지켜야 할 출력 규칙
- JSON 형식으로만 출력
- 각 항목은 반드시 제공된 요약 정보에 근거할 것
- 프레임워크, 라이브러리, 기술명은 영어 원문 유지
- 서술형 설명은 한국어로 작성

---

## 분석 항목

1. **사용 기술 / 라이브러리**
    - 라이브러리는 핵심인 상위 5개만 선정
2. **협업 및 개발 스타일 분석**
3. **프로젝트 주제**
4. **핵심 기능 및 어필 포인트**
   - 관련 파일 경로 포함
5. **개선 방향 제안**
   - 사용자 역할 고려

---

## 사용자 제공 분석 참고 텍스트
{user_text_for_analysis}

---

## 파일 단위 코드 요약
{json.dumps(repo_summaries, ensure_ascii=False)}

---

## 커밋 기반 개발 스타일 요약
{json.dumps(commit_summary, ensure_ascii=False)}

---

## 출력 예시(JSON)
{{
  "tech_stack": {{
    "frameworks": [],
    "libraries": []
  }},
  "collaboration_analysis": {{
    "collaboration": "",
    "development_style": "",
    "developer_traits": ""
  }},
  "project_domain": "",
  "key_features": [
    {{
      "feature": "",
      "description": "",
      "related_code": []
    }}
  ],
  "improvement_suggestions": [
    {{
      "area": "",
      "suggestion": "",
      "reason": ""
    }}
  ]
}}
"""

# ==============================
# 5. LLM 호출
# ==============================

def analyze_with_llm(prompt: str):
    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        temperature=0.2
    )
    return response.output_text


# ==============================
# 6. Github api로 해당 레포에서 language 사용 이력 가져오기
# ==============================
PROGRAMMING_LANGUAGES = {
    "Python", "Java", "JavaScript", "TypeScript",
    "C", "C++", "C#", "Go", "Rust",
    "Kotlin", "Swift",
    "PHP", "Ruby",
    "R",
    "Scala",
    "MATLAB",
    "Dart"
}


def extract_main_languages(languages_raw, whitelist):
    filtered = {
        lang: bytes_
        for lang, bytes_ in languages_raw.items()
        if lang in whitelist
    }

    sorted_langs = sorted(
        filtered.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [lang for lang, _ in sorted_langs]

import requests
import os

def fetch_repo_languages(owner: str, repo: str, github_token: str | None = None) -> dict:
    """
    GitHub REST API를 사용해 레포의 언어별 사용량(bytes)을 가져온다.
    반환값 예:
    {
        "Python": 27171,
        "C": 1005230,
        ...
    }
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    return response.json()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

languages_raw = fetch_repo_languages(
    owner=OWNER,
    repo=REPO,
    github_token=GITHUB_TOKEN
)


languages = extract_main_languages(
    languages_raw,
    PROGRAMMING_LANGUAGES
)

import re

def safe_json_loads(llm_output: str) -> dict:
    """
    LLM 출력에서 JSON 객체만 추출하여 dict로 변환
    """
    if not llm_output or not llm_output.strip():
        raise ValueError("LLM 응답이 비어 있습니다.")

    # 코드블록 제거
    cleaned = re.sub(r"```(?:json)?", "", llm_output).strip()

    # JSON 시작/끝 위치 찾기
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("LLM 응답에서 JSON 객체를 찾을 수 없습니다.")

    json_str = cleaned[start:end + 1]

    return json.loads(json_str)



# ==============================
# 7. 실행
# ==============================

if __name__ == "__main__":
    print("📂 파일 요약 로드 중...")
    repo_summaries = load_repo_file_summaries(REPO_SUMMARY_DIR)

    print("📂 커밋 요약 로드 중...")
    commit_summary = load_commit_style_summary(COMMIT_SUMMARY_PATH)

    print("🧠 LLM 프롬프트 구성...")
    prompt = build_prompt(repo_summaries, commit_summary)
    print(f"Prompt length: {len(prompt)}")

    print("🚀 AI 종합 분석 요청 중...")
    raw_result = analyze_with_llm(prompt)

    result = safe_json_loads(raw_result)

    result["tech_stack"]["languages"] = languages # api로 가져온 언어 사용량 정렬한거

    # PK 설정
    repo_analysis_id = f"{OWNER}/{REPO}"    
    result["repo_analysis_id"] = repo_analysis_id 

    save_path = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\single_repo_analysis"
    output_path = os.path.join(save_path, f"{OWNER}_{REPO}_single_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 최종 분석 완료!\n결과 저장 위치:\n{output_path}")
