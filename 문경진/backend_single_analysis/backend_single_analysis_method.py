import os
import json
import re
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
import time

# load_dotenv()

# client = OpenAI(
#     api_key=os.getenv("GMS_API_KEY"),
#     base_url=os.getenv("GMS_BASE_URL")
# )

## 막혔을 때 retry
def call_with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                wait = min(10, 2 ** attempt)  # 2, 4, 8, 10...
                print(f"⚠️ 429 발생 → {wait}s 대기 후 재시도 ({attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("429 재시도 한도 초과")


### 개별 파일 내 코드가 너무 길 때, 처음 800자와 끝 800자만 input으로 넣어서 분석 및 요약
def make_snippet_for_llm(text: str, head_len=800, tail_len=800) -> str:
    if len(text) <= head_len + tail_len:
        return text
    return (
        text[:head_len]
        + "\n\n# --- truncated ---\n\n"
        + text[-tail_len:]
    )
########################################################################################


### json 로드 시 불필요한 노이즈 제거
def safe_json_loads(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON 파싱 실패")
    return json.loads(cleaned[start:end+1])
########################################################################################



### java 핵심 디렉토리 + application.yml 선별 코드
from pathlib import Path
from typing import List, Dict

def collect_spring_backend_files(repo_root: str, TARGET_DIRS) -> List[Dict[str, str]]:
    """
    Spring / Spring Boot 백엔드 레포에서
    - controller / service / repository 하위의 .java 파일
    - application.yml
    - README.md
    을 선별하여
    [{'path': 상대경로, 'content': 파일내용}, ...] 형태로 반환
    """

    repo_root = Path(repo_root)

    selected_files: List[Dict[str, str]] = []
    application_yml_added = False
    readme_added = False

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        
        filename_lower = path.name.lower()
        
        # README.md (1개만, 위치 무관)
        if filename_lower == "readme.md" and not readme_added:
            selected_files.append({
                "path": str(path.relative_to(repo_root)),
                "content": path.read_text(encoding="utf-8", errors="ignore")
            })
            readme_added = True
            continue
        
        # application.yml
        if path.name == "application.yml" and not application_yml_added:
            selected_files.append({
                "path": str(path.relative_to(repo_root)),
                "content": path.read_text(encoding="utf-8", errors="ignore")
            })
            application_yml_added = True
            continue

        # .java 파일만 대상
        if path.suffix != ".java":
            continue

        # 핵심 디렉토리 하위인지 확인
        if any(part in TARGET_DIRS for part in path.parts):
            selected_files.append({
                "path": str(path.relative_to(repo_root)),
                "content": path.read_text(encoding="utf-8", errors="ignore")
            })

    return selected_files
##################################################################################


### 각 디렉토리 별 핵심 파일을 코드 내 키워드를 기준으로 선별

# 코드가 너무 짧은 의미 없는 파일 제거
def has_minimum_volume(content: str, min_lines: int = 40) -> bool:
    return content.count("\n") >= min_lines

def is_meaningful_service(content: str, SERVICE_KEYWORDS) -> bool:
    return any(keyword in content for keyword in SERVICE_KEYWORDS)

def is_meaningful_repository(content: str, REPOSITORY_KEYWORDS) -> bool:
    return any(keyword in content for keyword in REPOSITORY_KEYWORDS)


def filter_backend_files_by_keywords(
    selected_files: list,
     SERVICE_KEYWORDS, REPOSITORY_KEYWORDS, min_service_lines: int = 40
) -> list:
    """
    Controller: 전부 유지
    Service: 키워드 + 라인 수 기준 필터
    Repository: 커스텀 쿼리 있는 것만 유지
    """

    filtered_files = []

    for file in selected_files:
        path = file["path"].replace("\\", "/")
        content = file["content"]

        # 0️⃣ README / yml 파일은 무조건 유지
        if path.endswith(".md") or path.endswith(".yml") or path.endswith(".yaml"):
            filtered_files.append(file)
            continue
        
        # 1️⃣ Controller는 무조건 유지
        if "/controller/" in path:
            filtered_files.append(file)
            continue

        # 2️⃣ Service 필터
        if "/service/" in path:
            if (
                is_meaningful_service(content, SERVICE_KEYWORDS=SERVICE_KEYWORDS)
                and has_minimum_volume(content, min_service_lines)
            ):
                filtered_files.append(file)
            continue

        # 3️⃣ Repository 필터
        if "/repository/" in path:
            if is_meaningful_repository(content, REPOSITORY_KEYWORDS=REPOSITORY_KEYWORDS):
                filtered_files.append(file)
            continue


    return filtered_files
#################################################################


### 개별 파일 단위 요약 및 분석
import requests
import os


def summarize_file_with_llm(
    path: str,
    content: str,
    *,
    gms_api_key: str,
    gms_base_url: str,
    user_input
) -> dict:
    snippet = make_snippet_for_llm(content)

    prompt = f"""
너는 여러 소스 파일을 분석하여
나중에 하나의 프로젝트 분석 리포트로 합성하기 위한
"부분 분석 결과"를 생성하는 AI다.

중요:
- 이 단계에서는 프로젝트 전체를 단정하거나 요약하지 마라.
- 오직 "이 파일 하나"에서 확인 가능한 정보만 추출하라.
- 사용자가 입력한 텍스트를 바탕으로 분석을 수행하라.

---

## 입력

[파일 경로]
{path}

[파일 내용 일부]
{snippet}

[사용자가 입력한 텍스트]
{user_input}

(주의: 파일 내용은 길이 제한으로 인해 일부만 제공되었을 수 있다)

---

## 분석 목표

이 파일을 분석하여,
최종 프로젝트 분석 리포트에서 아래 항목들을 구성하는 데
사용될 수 있는 "부분 정보"를 JSON 형태로 추출하라.

---

## 추출해야 할 정보 (파일 단위 관점)

### 1. 프로젝트 주제 관련 신호
- 이 파일이 속한 프로젝트의 주제를 직접 단정하지 마라.
- 대신, 프로젝트 주제 추정에 도움이 될 수 있는
  도메인 키워드나 역할 설명을 간접적으로 기록하라.

### 2. 프레임워크 / 라이브러리 신호
- 이 파일에서 확인 가능한 프레임워크를 나열하라.
- 이 파일에서 직접 사용되거나 import된 라이브러리만 기록하라.

### 3. 핵심 기능 후보 (이 파일 기준)
- 이 파일이 수행하는 기능을 1~3개 수준으로 추출하라.
- 각 기능은 "무엇을 하는지"와 "어떻게 구현되었는지"를 분리하여 기록하라.
- 이 파일 하나만으로 판단 가능한 범위까지만 작성하라.
- 각 기능이 실무 또는 채용 관점에서 어떤 개발 역량을 보여주는지 한 문장으로 명확히 서술하라.

### 4. 개선 가능성 신호
- 이 파일 수준에서 관찰 가능한 개선 여지를 기록하라.
- 반드시 일반적인 개발 관점에서의 제안만 포함하라.

---

## 출력 규칙 (매우 중요)

- 반드시 JSON 형식으로만 출력하라.
- 설명 문장, 마크다운, 코드 블록을 절대 포함하지 마라.
- 기술명은 영어로, 설명은 한국어로 작성하라.
- 아래 출력 스키마를 정확히 따르라.

---

## 출력 JSON 스키마 (파일 단위 결과)

{{
  "path": "",
  "project_subject_signals": [],
  "frameworks": [],
  "libraries": [],
  "core_features": [
    {{
      "feature_name": "",
      "feature_description": "",
      "implementation_method": "",
      "job_value": ""
    }}
  ],
  "improvement_suggestions": []
}}
    """

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
        timeout=60
    )

    response.raise_for_status()
    data = response.json()

    # Gemini 응답에서 텍스트 추출
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    # JSON 안전 파싱
    result = safe_json_loads(raw_text)
    result["path"] = path
    return result

########################################################################################


### 배치 처리
def split_into_batches(items: list, batch_size: int):
    return [
        items[i:i + batch_size]
        for i in range(0, len(items), batch_size)
    ]
########################################################################################


### 배치 단위 의미 요약
def summarize_batch_semantic(batch_data: dict, *, gms_api_key: str, gms_base_url: str, user_input) -> dict:
    summaries = batch_data.get("summaries", [])

    compact = [
        {
            "path": i.get("path", ""),
            "analysis": i
        }
        for i in summaries
    ]
    
    prompt = f"""
너는 여러 개의 "개별 파일 분석 결과(JSON)"를 입력으로 받아,
나중에 하나의 최종 프로젝트 분석 리포트로 합성하기 위한
"배치 단위 중간 요약"을 생성하는 AI다.

---

## 배치 단위에서 해야 할 일

### 1. 프로젝트 주제 후보 정리
- 개별 파일에서 수집된 project_subject_signals를 종합하라.
- 배치 기준으로 프로젝트 주제 후보를 1~3개 수준으로 정리하라.
- 하나의 문장으로 단정하지 말고, 후보 형태로 기록하라.

### 2. 기술 스택 집계
- 배치 내 파일들에서 사용된
  - frameworks
  - libraries
  를 각각 유니크하게 집계하라.

### 3. 핵심 기능 후보 묶기
- 개별 파일의 core_features를 분석하여,
  서로 연관된 기능들을 묶어 배치 단위 핵심 기능 후보로 정리하라.
- 기능 수는 2~5개 이내로 제한하라.
- 각 기능에 대해 다음을 포함하라:
  - feature_name
  - feature_description
  - implementation_method
  - job_value
- 기능 설명은 배치 기준으로 일반화하되, 과도한 추상화는 피하라.

### 4. 개선 방향 신호 통합
- 개별 파일의 improvement_suggestions를 종합하라.
- 중복되는 제안은 하나로 합치고,
  배치 기준에서 의미 있는 개선 방향만 1~3개로 정리하라.

---

## 출력 규칙 (중요)

- 반드시 JSON 형식으로만 출력하라.
- 설명 문장, 마크다운, 코드 블록을 절대 포함하지 마라.
- 아래 출력 스키마를 정확히 따르라.
- 기술명은 영어로, 설명은 한국어로 작성하라.

---

## 출력 JSON 스키마 (배치 단위 결과)

{{
  "batch_id": ""
  "project_subject_candidates": [],
  "frameworks": [],
  "libraries": [],
  "core_features": [
    {{
      "feature_name": "",
      "feature_description": "",
      "implementation_method": "",
      "job_value": ""
    }}
  ],
  "improvement_suggestions": []
}}

---

[입력]
{json.dumps(compact, ensure_ascii=False)}
"""

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

    # Gemini 응답 텍스트 추출
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    # JSON 안전 파싱
    result = safe_json_loads(raw_text)

    # batch_id는 LLM 판단 대상이 아니므로 코드에서 주입
    result["batch_id"] = batch_data.get("batch_id")

    return result
#######################################################################################



### 배치 단위로 요약된 내용들을 바탕으로 최종 레포 분석에 사용할 프롬프트 구성
def build_final_project_prompt(
    batch_semantic_summaries: list,
    repo_analysis_id: str
) -> str:
    """
    배치 단위 의미 요약들을 입력으로 받아
    최종 프로젝트 분석을 수행하기 위한 프롬프트 생성
    """

    prompt = f"""
너는 개발자 프로젝트 레포지토리를 채용 관점에서 종합 분석하는 AI다.

아래에 제공되는 정보는
하나의 프로젝트를 구성하는 **배치 단위 의미 요약 결과들(JSON)**이다.

각 배치는 개별 파일 분석 결과를 바탕으로 생성되었으며,
서로 다른 기능 또는 도메인이 섞여 있을 수 있다.

---

## 너의 역할

- 배치 요약을 그대로 나열하거나 재서술하지 마라.
- 배치들에 흩어져 있는 단서를 **재조합**하여
  프로젝트 전체를 대표하는 분석 결과를 도출하라.
- 추측이 필요한 경우 과장하지 말고,
  제공된 정보로 합리적으로 판단 가능한 범위까지만 서술하라.

---

## 분석 목표 (반드시 충족)

아래 항목을 모두 포함하는 **최종 프로젝트 분석 결과**를 생성하라.

### 1. 프로젝트 주제
- 이 프로젝트가 어떤 문제를 해결하는 서비스인지
- 어떤 도메인에 속하는 프로젝트인지
- 한 문장으로 명확하게 요약하라.

### 2. 기술 스택
- 배치 요약들에서 확인된 정보를 기반으로
  frameworks와 libraries를 각각 정리하라.
- 실제로 사용 근거가 있는 기술만 포함하라.

### 3. 핵심 기능 정리
- 배치 단위가 아닌 **기능 단위**로 핵심 기능을 재구성하라.
- 유사하거나 중복되는 기능은 하나로 병합하라.
- 핵심 기능은 5개 이상을 반환하라.
- 각 기능에 대해 다음을 반드시 포함하라:
  - feature_name
  - feature_description
  - implementation_method
  - job_value(이 기능 구현을 통해 드러나는 실무/채용 관점의 개발 역량)

### 4. 프로젝트 개선 방향
- 배치 요약에서 언급된 개선 신호를 종합하여
  프로젝트 차원에서 의미 있는 개선 방향만 정리하라.
- 현재 구현을 완전히 부정하지 말고,
  현실적으로 확장·보완 가능한 제안 위주로 작성하라.

---

## 출력 규칙 (절대 준수)

- 반드시 JSON 형식으로만 출력하라.
- 설명 문장, 마크다운, 코드 블록은 절대 포함하지 마라.
- 아래 출력 JSON 스키마를 **그대로** 사용하라.
- 기술명은 영어로, 설명은 한국어로 작성하라.

---

## 출력 JSON 형식

{{
  "project_subject": "",
  "frameworks": [],
  "libraries": [],
  "core_features": [
    {{
      "feature_name": "",
      "feature_description": "",
      "implementation_method": "",
      "job_value": ""
    }}
  ],
  "improvement_suggestions": [],
  "collaboration_style": ""
}}

---

[입력: 배치 단위 의미 요약]
{json.dumps(batch_semantic_summaries, ensure_ascii=False)}

"""
    return prompt
###########################################################################

import requests

### 배치 의미 요약들을 바탕으로 프로젝트 최종 분석 수행 (Gemini)
def analyze_project_from_batches(
    batch_semantic_summaries: list,
    *,
    gms_api_key: str,
    gms_base_url: str,
    repo_analysis_id: str
) -> dict:
    """
    배치 단위 의미 요약들을 입력으로 받아
    Gemini(GMS)를 통해 프로젝트 최종 분석 수행
    """

    # 1️⃣ 프롬프트 구성
    prompt = build_final_project_prompt(
        batch_semantic_summaries=batch_semantic_summaries,
        repo_analysis_id=repo_analysis_id
    )

    # 2️⃣ Gemini GMS 헤더
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": gms_api_key,
    }

    # 3️⃣ Gemini GMS payload
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

    # 4️⃣ Gemini GMS 호출
    response = requests.post(
        gms_base_url,
        headers=headers,
        json=payload,
        timeout=180
    )

    response.raise_for_status()
    data = response.json()

    # 5️⃣ 응답 텍스트 추출
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    # 6️⃣ JSON 안전 파싱
    return safe_json_loads(raw_text)

#################################################################




# ### GitHub API로 언어 사용량 가져오기
# import requests

# def fetch_repo_languages(
#     owner: str,
#     repo: str,
#     github_token: str | None = None
# ) -> dict:
#     """
#     GitHub REST API를 사용해 레포의 언어별 사용량(bytes)을 가져온다.
#     반환 예:
#     {
#         "Python": 27171,
#         "Java": 502130,
#         ...
#     }
#     """
#     url = f"https://api.github.com/repos/{owner}/{repo}/languages"

#     headers = {
#         "Accept": "application/vnd.github+json"
#     }

#     if github_token:
#         headers["Authorization"] = f"Bearer {github_token}"

#     response = requests.get(url, headers=headers, timeout=10)
#     response.raise_for_status()

#     return response.json()
# ###################################################################


# ### 주요 언어만 추출해서 사용량별로 정렬
# PROGRAMMING_LANGUAGES = {
#     "Python", "Java", "JavaScript", "TypeScript",
#     "C", "C++", "C#", "Go", "Rust",
#     "Kotlin", "Swift",
#     "PHP", "Ruby",
#     "R",
#     "Scala",
#     "MATLAB",
#     "Dart"
# }

# def extract_main_languages(
#     languages_raw: dict,
#     whitelist: set
# ) -> list[str]:
#     """
#     GitHub API 결과에서
#     whitelist에 포함된 언어만 추출 후
#     사용량(bytes) 기준 내림차순 정렬
#     """
#     filtered = {
#         lang: bytes_
#         for lang, bytes_ in languages_raw.items()
#         if lang in whitelist
#     }

#     sorted_langs = sorted(
#         filtered.items(),
#         key=lambda x: x[1],
#         reverse=True
#     )

#     return [lang for lang, _ in sorted_langs]

# #####################################################


# ### github 레포의 주요 사용 언어 리스트 반환
# def get_repo_main_languages(
#     owner: str,
#     repo: str,
#     github_token: str | None = None,
#     whitelist: set = PROGRAMMING_LANGUAGES
# ) -> list[str]:
#     """
#     GitHub 레포의 주요 사용 언어 리스트 반환
#     """
#     raw = fetch_repo_languages(
#         owner=owner,
#         repo=repo,
#         github_token=github_token
#     )

#     return extract_main_languages(
#         languages_raw=raw,
#         whitelist=whitelist
#     )
# ###############################################################


### commit snippet 생성
def build_commit_snippet(commit_data: dict, max_messages: int = 15) -> dict:
    commits = commit_data.get("commits", [])

    authors = sorted({c["author_name"] for c in commits})

    messages = [c["message"] for c in commits]
    sample_messages = (
        messages[: max_messages // 2]
        + messages[-max_messages // 2 :]
    )

    return {
        "total_commits": commit_data.get("total_commits"),
        "authors": authors,
        "sample_messages": sample_messages
    }
##################################################################



### commit 스타일 분석 및 요약 by LLM (Gemini)
def summarize_commit_style_with_llm(
    commit_summary: dict,
    *,
    gms_api_key: str,
    gms_base_url: str
) -> str:
    prompt = f"""
너는 GitHub 프로젝트의 커밋 메시지를 근거로
프로젝트의 협업 형태와 운영 흔적을 분석하는 AI다.

아래 정보는 하나의 프로젝트에서 수집된 커밋 메시지 요약이다.

[입력]
{commit_summary}

---

## 분석 목적

이 분석은 개발자를 평가하기 위함이 아니라,
이 프로젝트가 협업을 전제로 운영되었는지, 그리고
어떤 방식의 협업 흔적이 있는지를 근거 기반으로 설명하기 위함이다.

---

## 분석 항목

1) 협업 여부
- 서로 다른 작성자의 커밋이 교차하는지

2) 협업 규칙 흔적
- 커밋 메시지의 가독성
- commit convention 준수 여부

---

## 출력 규칙

- 반드시 JSON만 출력
- 설명 문장, 마크다운, 코드 블록 금지
- 설명은 반드시 한국어로 출력

---

## 출력 JSON 스키마

{{
  "collaboration_type": "단독 개발 | 다인 협업",
  "commit_message_quality": {{
    "readability": "낮음 | 보통 | 높음",
    "convention_usage": "없음 | 일부 사용 | 일관되게 사용"
  }}
}}
"""

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
########################################################

def analyze_commit_style(
    commit_metadata: dict,
    *,
    gms_api_key: str,
    gms_base_url: str,
    max_messages: int = 15
) -> dict:
    """
    커밋 메타데이터 → 커밋 스타일 분석(JSON)
    """

    snippet = build_commit_snippet(
        commit_data=commit_metadata,
        max_messages=max_messages
    )

    raw = summarize_commit_style_with_llm(
        commit_summary=snippet,
        gms_api_key=gms_api_key,
        gms_base_url=gms_base_url
    )

    return safe_json_loads(raw)

