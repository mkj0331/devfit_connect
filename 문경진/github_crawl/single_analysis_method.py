import os
import json
import re
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GMS_API_KEY"),
    base_url=os.getenv("GMS_BASE_URL")
)


### 개별 파일 내 코드가 너무 길 때, 처음 1500자와 끝 1500자만 input으로 넣어서 분석 및 요약
def make_snippet_for_llm(text: str, head_len=1500, tail_len=1500) -> str:
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


### 레포 파일 중에 확장자 기준으로 필요한 파일만 로드해서 repo_files에 추가
ALLOWED_EXTENSIONS = (
    ".py", ".js", ".ts", ".sql",
    ".yml", ".yaml", ".md", ".java"
) # 프론트 파일 추가

EXCLUDE_DIRS = {
    ".git", ".svn", ".hg",
    ".idea", ".vscode", ".metadata", ".settings",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".venv", "venv",
    "node_modules", ".next", ".nuxt", ".svelte-kit",
    "dist", "build", "out", "target",
    "logs", "tmp", "temp",
    ".DS_Store", "Thumbs.db", ".jpg", ".png"
}

def load_repo_as_analysis_input(repo_root: str, ALLOWED_EXTENSIONS=ALLOWED_EXTENSIONS, EXCLUDE_DIRS=EXCLUDE_DIRS) -> List[Dict]:
    repo_files = []

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if not file.endswith(ALLOWED_EXTENSIONS):
                continue
            if file.startswith("."):
                continue

            path = os.path.join(root, file)
            try:
                content = Path(path).read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            except Exception:
                continue

            repo_files.append({
                "path": os.path.relpath(path, repo_root),
                "content": content
            })

    return repo_files
########################################################################################


### 개별 파일 단위 요약 및 분석
MODEL_NAME = 'gpt-4o-mini'
def summarize_file_with_llm(path: str, content: str, client, MODEL_NAME=MODEL_NAME) -> dict:
    snippet = make_snippet_for_llm(content)

    prompt = f"""
당신은 여러 프로젝트를 자동 분석하기 위해,
파일 단위에서 **나중에 합성 가능한 증거(evidence)**를 추출하는 분석기입니다.

---

## 원칙

- 프로젝트 전체 기능을 단정하지 마세요.
- 파일 하나에서 확인되는 **사실(근거)**과 **추정(가능성)**을 명확히 분리하세요.
- 아래 스키마에 맞게 **합성 재료**를 최대한 구조적으로 추출하세요.

---

## 입력

[파일 경로]
{path}

[코드 일부]
{snippet}

---

## 해야 할 일

### 1) 파일 레이어 / 책임 추정
- 이 파일의 레이어와 책임을 추정하고 confidence를 부여하세요.

### 2) 도메인 신호 추출
- 도메인 키워드 / 엔티티 / 모듈 신호를 **이름 기반**으로 추출하세요.

### 3) 기능 후보(feature_candidates) 추출
- 기능 후보를 1~5개 추출하세요.
- 각 기능은 **verb-object** 형태로 표현하세요.  
  (예: "알림 조회", "토큰 검증")
- 가능한 경우 inputs / outputs / side_effects를 추출하세요.

### 4) 구현 방식 / 기술 신호
- 데이터 접근 방식: JPA / SQL / Redis 등
- 패턴 / 관례: DTO, Repository, Validation 등
- 횡단 관심사: 보안, 트랜잭션, 동시성, 캐시, 예외 처리 등

### 5) 품질 신호
- strengths (어필 포인트 후보) 1~5개
- risks (잠재 리스크) 1~5개
- missing_standard_checks  
  - 현업 기준에서 흔히 추가되는 요소 1~5개

### 6) evidence
- 위 판단의 근거가 되는 요소를 3~7개 발췌하세요.
- import / annotation / call / query / endpoint / config 중 하나의 type을 사용하세요.
- text는 짧고 구체적으로 작성하세요.

### 7) handoff_tags
- 이 파일을 10개 묶음 또는 전체 분석에서 군집화하기 위한
  cluster_keys를 3~10개 생성하세요.  
  (예: "auth+jwt", "payment+webhook", "alarm+sse", "db+jpa", "api+controller")
- 관련 파일 후보를 **경로/이름 기반으로 추정**하세요.
- 추정 불가 시 빈 배열을 사용하세요.

---

## 출력 규칙 (중요)

- 반드시 **JSON만 출력**
- 설명 문장, 마크다운, 코드 블록 절대 금지
- 아래 스키마를 **정확히** 따르세요.
- 값이 없으면 빈 문자열("") 또는 빈 배열([])을 사용하세요.

---

## 출력 JSON 스키마

{{
  "file": {{
    "path": "",
    "language": "",
    "frameworks": [],
    "libraries": [],
    "layer_guess": "",
    "confidence": 0.0
  }},
  "domain_signals": {{
    "keywords": [],
    "entities": [],
    "modules": []
  }},
  "feature_candidates": [
    {{
      "name": "",
      "verb_object": "",
      "inputs": [],
      "outputs": [],
      "side_effects": [],
      "confidence": 0.0
    }}
  ],
  "technique_signals": {{
    "data_access": [],
    "patterns": [],
    "cross_cutting": []
  }},
  "quality_signals": {{
    "strengths": [],
    "risks": [],
    "missing_standard_checks": []
  }},
  "evidence": [
    {{ "type": "import|annotation|call|query|endpoint|config", "text": "" }}
  ],
  "handoff_tags": {{
    "cluster_keys": [],
    "related_files_guess": []
  }}
}}
"""

    response = client.responses.create(
        model=MODEL_NAME,
        input=prompt,
        temperature=0.2
    )

    result = safe_json_loads(response.output_text)
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
def summarize_batch_semantic(batch_data: dict, client: OpenAI, model: str) -> dict:
    compact = [
        {
            "path": i["file"]["path"],   
            "analysis": i                
        }
        for i in batch_data["summaries"]
    ]
    prompt = f"""
너는 개발자 프로젝트 레포지토리의 **배치 단위 증거 추출 / 군집화 AI**다.

이 배치는 순차로 묶였으며, 서로 다른 기능 또는 모듈이 섞여 있을 수 있다.
따라서 너의 목표는 **하나의 역할로 요약하는 것이 아니라**,
서로 다른 기능 후보를 분해하고, 각 후보에 태그와 근거를 붙여
다음 단계(전체 레포 분석)에서 재조립 가능하게 만드는 것이다.

입력은 "파일 요약(JSON)" 리스트이며,
각 아이템은 파일 경로, 기술, 역할, 기능 힌트를 포함한다.

출력은 반드시 **JSON만** 사용한다.

---

## 해야 할 일

### 1) 기능 후보 군집화
- 이 배치 안에서 서로 관련 있는 파일들을
  **기능 후보 단위(feature_clusters)**로 군집화하라.
- 군집 수는 **1~5개까지 가능**
- 서로 다른 기능이 섞여 있다면 반드시 군집을 분리하라  
  (예: 알림, 인증, 공통 DTO 등)

### 2) 각 군집마다 아래 정보를 추출하라

- cluster_name  
  - 명사 + 동사 형태 권장  
  - 예: "알림 조회/읽음 처리", "JWT 인증", "SSE 실시간 알림 스트리밍"

- domain_tags  
  - 군집을 대표하는 태그 3~10개  
  - 예: alarm, notification, sse, auth, jwt, login, validation

- responsibilities  
  - 이 군집이 담당하는 책임(행동 단위) 3~8개

- implementation_signals  
  - 기술 또는 설계 패턴 신호  
  - 예: JPA repository, DTO, SSE emitter, Spring Security filter 등

- evidence  
  - 이 군집 판단의 근거가 되는
    **file paths 또는 key strings** 3~10개  
  - 짧고 구체적으로 작성

- confidence  
  - 0 ~ 1 사이의 실수

- risks_or_unknowns  
  - 맥락 부족으로 인해 확신하지 못하는 점 1~5개

### 3) 배치 레벨에서 반드시 정리할 것

- languages / technologies  
  - 배치 내 파일들에서 사용된 언어/기술의 유니크 집합

- batch_mixture_flag  
  - 서로 다른 기능이 섞여 있다고 판단되면 true, 아니면 false

- suggested_cluster_keys  
  - 전체 레포 분석 단계에서 군집화 기준으로 사용할 키워드 5~20개

---

## 출력 스키마 (JSON only)

{{
  "batch_id": {batch_data["batch_id"]},
  "batch_mixture_flag": false,
  "languages": [],
  "technologies": [],
  "feature_clusters": [
    {{
      "cluster_name": "",
      "domain_tags": [],
      "responsibilities": [],
      "implementation_signals": [],
      "related_files": [],
      "evidence": [],
      "confidence": 0.0,
      "risks_or_unknowns": []
    }}
  ],
  "suggested_cluster_keys": []
}}

---

[입력]
{json.dumps(compact, ensure_ascii=False)}

---

⚠️ 주의사항

- "batch_role" 과 같은 **단일 요약 문장**을 만들지 마라.
- 하나의 파일이 여러 기능에 걸칠 수 있다면  
  related_files에 **중복 포함해도 된다**.
- 절대 프로젝트 전체를 단정하지 말고,  
  **이 배치에 포함된 근거 내에서만** 판단하라.
- 반드시 **JSON만 출력**하고,
  설명 문장이나 코드 블록은 절대 포함하지 마라.
"""


    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2
    )

    result = safe_json_loads(response.output_text)
    result["batch_id"] = batch_data["batch_id"]
    return result
#######################################################################################



### 배치 단위로 요약된 내용들을 바탕으로 최종 레포 분석에 사용할 프롬프트 구성
def build_final_project_prompt(
    batch_semantic_summaries: list,
    repo_analysis_id: str
) -> str:

    return f"""
너는 개발자 프로젝트 레포지토리 **종합 분석 AI**다.

아래에 제공된 정보는
하나의 프로젝트를 구성하는 **기능 단위 배치 요약들**이다.

⚠️ 각 배치는 순차적으로 묶였으며,
서로 다른 기능이 섞여 있을 수 있다.

---

## 너의 역할

- 배치 요약을 그대로 재서술하지 마라.
- 배치 내부의 기능 / 도메인 힌트를 **재조합**하여
  프로젝트의 핵심 기능을 **의미 단위로 재구성**하라.

---

## 분석 목표 (중요)

- 이 프로젝트가 어떤 **서비스 / 도메인**의 프로젝트인지 설명할 것
- 기능 단위로 프로젝트를 재구성할 것
- 각 기능에 대해 아래 질문에 모두 답할 것:

  - 이 기능은 무엇을 하는가?
  - 어떤 기술 스택과 구현 방식으로 만들어졌는가?
  - 현업에서 일반적으로 사용하는 구현 방식과 비교하면 어떤 수준인가?
  - 이 구현에서 특히 잘된 점은 무엇인가? (취업 어필 포인트)
  - 이 기능을 앞으로 어떻게 발전시킬 수 있는가?

---

## 기능 재구성 규칙 (매우 중요)

- 배치 단위가 아닌 **기능 단위**로 `core_features`를 재정의하라.
- 서로 다른 배치에 등장하더라도,
  - 동일한 도메인
  - 유사한 책임
  - 같은 기술 패턴
  을 가진 항목은 **하나의 기능으로 병합**하라.
- `core_features`는 **2~5개로 제한**하라.

### 기능 중요도 판단 신호
- 여러 배치에 반복 등장하는지
- 관련 코드 경로 수
- 프로젝트 도메인에서의 핵심성

---

## 현업 스탠다드 비교 가이드

`industry_standard_comparison`에서는 반드시
아래 관점 중 **해당 기능과 직접적으로 관련된 것만** 선택하여 비교하라.

- 레이어 분리 (Controller / Service / Repository)
- 데이터 접근 방식 (JPA, Query 방식, 트랜잭션 경계)
- 인증 / 인가 처리 방식
- 실시간 처리 방식 (SSE, Polling 등)
- 입력 검증 및 예외 처리
- 확장성 / 유지보수 관점의 구조

⚠️ 배치 요약에 **근거 없는 기술은 절대 언급하지 말 것**.

---

## 강점 및 개선점 생성 규칙

### strengths
- "좋다", "잘했다" 같은 추상 표현 금지
- 반드시  
  **구현 선택 → 그로 인한 효과**  
  형태로 작성할 것  
  (예: 구조 분리 → 변경 영향 최소화)

### future_development_suggestions
- 아키텍처 전체 교체 ❌
- 현재 구현을 기반으로 한 **현실적인 확장 / 보완만 제안**
- 제안에는 반드시 **기대 효과**를 함께 설명할 것

---

## 협업 스타일 분석

`collaboration_style`에는 아래를 근거로
이 프로젝트에서 드러나는 **협업 방식**을 서술하라.

- 코드 구조
- 역할 분리
- 구현 일관성

⚠️ 개인의 성향 추측 금지

---

## 출력 규칙 (절대 준수)

- 반드시 **JSON 형식으로만 출력**
- 아래 JSON 스키마를 **그대로 유지**
- 기술명은 영어, 설명은 한국어
- `related_code_paths`는 **배치 요약에 실제 등장한 경로만 사용**
- 근거 없는 추측 금지

---

## 입력: 배치 단위 의미 요약
{json.dumps(batch_semantic_summaries, ensure_ascii=False)}

---

## 출력 JSON 형식 (반드시 그대로 사용)

{{
  "repo_analysis_id": "{repo_analysis_id}",
  "project_domain": "",
  "tech_stack": {{
    "frameworks": [],
    "libraries": []
  }},
  "core_features": [
    {{
      "feature_name": "",
      "feature_description": "",
      "implementation": {{
        "implementation_method": "",
        "related_code_paths": []
      }},
      "industry_standard_comparison": {{
        "standard_approach": "",
        "comparison_result": ""
      }},
      "strengths": [],
      "future_development_suggestions": [
        {{
          "suggestion": "",
          "expected_effect": ""
        }}
      ]
    }}
  ],
  "collaboration_style": ""
}}
"""

###########################################################################


### 배치 의미 요약들을 바탕으로 프로젝트 최종 분석 수행
def analyze_project_from_batches(
    batch_semantic_summaries: list,
    client,
    model: str,
    repo_analysis_id: str
) -> dict:
    """
    
    """
    prompt = build_final_project_prompt(
        batch_semantic_summaries=batch_semantic_summaries,
        repo_analysis_id=repo_analysis_id
    )

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2
    )

    return safe_json_loads(response.output_text)
#################################################################


### GitHub API로 언어 사용량 가져오기
import requests

def fetch_repo_languages(
    owner: str,
    repo: str,
    github_token: str | None = None
) -> dict:
    """
    GitHub REST API를 사용해 레포의 언어별 사용량(bytes)을 가져온다.
    반환 예:
    {
        "Python": 27171,
        "Java": 502130,
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
###################################################################


### 주요 언어만 추출해서 사용량별로 정렬
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

def extract_main_languages(
    languages_raw: dict,
    whitelist: set
) -> list[str]:
    """
    GitHub API 결과에서
    whitelist에 포함된 언어만 추출 후
    사용량(bytes) 기준 내림차순 정렬
    """
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

#####################################################


### github 레포의 주요 사용 언어 리스트 반환
def get_repo_main_languages(
    owner: str,
    repo: str,
    github_token: str | None = None,
    whitelist: set = PROGRAMMING_LANGUAGES
) -> list[str]:
    """
    GitHub 레포의 주요 사용 언어 리스트 반환
    """
    raw = fetch_repo_languages(
        owner=owner,
        repo=repo,
        github_token=github_token
    )

    return extract_main_languages(
        languages_raw=raw,
        whitelist=whitelist
    )
###############################################################


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


### commit 스타일 분석 및 요약 by LLM
def summarize_commit_style_with_llm(
    commit_summary: dict,
    client,
    model: str
) -> str:
    prompt = f"""
너는 GitHub 프로젝트의 **커밋 메시지를 근거로
프로젝트의 협업 형태와 운영 흔적을 분석하는 AI**다.

아래 정보는 하나의 프로젝트에서 수집된 **커밋 메시지 요약**이다.

[입력]
{commit_summary}

---

## 분석 목적

이 분석은 **개발자를 평가하기 위함이 아니라**,
이 프로젝트가 **협업을 전제로 운영되었는지**, 그리고
**어떤 방식의 협업 흔적이 있는지**를 근거 기반으로 설명하기 위함이다.

---

## 분석 항목

1) **협업 여부**
- 커밋 작성자 수
- 서로 다른 작성자의 커밋이 교차하는지

2) **협업 규칙 흔적**
- 커밋 메시지 포맷의 일관성
- prefix(feat/fix 등) 또는 이슈 식별자 사용 여부

3) **역할 분리의 간접 신호 (가능한 경우만)**
- 작성자별로 반복되는 작업 영역 또는 키워드

4) **조율/혼선 신호**
- 동일 기능에 대한 반복 수정
- fix/hotfix/revert 등 안정화 흐름

---

## 출력 규칙

- 반드시 **JSON만 출력**
- 설명 문장, 마크다운, 코드 블록 금지
- 설명은 반드시 한국어로 출력
---

## 출력 JSON 스키마

{{
  "collaboration_type": "",
  "collaboration_signals": {{
    "rules_presence": "",
    "rules_evidence": [],
    "coordination_signals": []
  }}
}}
"""


    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2
    )

    return response.output_text.strip()
########################################################


### 커밋 요약 전체 함수
def analyze_commit_style(
    commit_metadata: dict,
    client,
    model: str,
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
        client=client,
        model=model
    )

    return safe_json_loads(raw)
