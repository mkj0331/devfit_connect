import os
import json
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
from single_analysis_method import load_repo_as_analysis_input, summarize_file_with_llm, split_into_batches, summarize_batch_semantic, get_repo_main_languages, analyze_commit_style, analyze_project_from_batches

# ==============================
# 0. 기본 설정
# ==============================

OWNER = 'team-algogo'
REPO = 'algogo_server'

REPO_PATH = rf"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl\{REPO}"

BASE_OUTPUT_DIR = rf"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl\{OWNER}_{REPO}_summary"
DIVIDED_SUMMARY_DIR = os.path.join(BASE_OUTPUT_DIR, "repo_divided_summary")
BATCH_SUMMARY_DIR = os.path.join(BASE_OUTPUT_DIR, "repo_batch_summary")

os.makedirs(DIVIDED_SUMMARY_DIR, exist_ok=True)
os.makedirs(BATCH_SUMMARY_DIR, exist_ok=True)

BATCH_SIZE = 10
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.2

# ==============================
# 1. OpenAI Client
# ==============================

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GMS_API_KEY"),
    base_url=os.getenv("GMS_BASE_URL")
)

# ==============================
# 2. 레포 파일 로더
# ==============================
repo_files = load_repo_as_analysis_input(repo_root=REPO_PATH)
print(f"레포 파일 로드 완료 (파일 갯수 : {len(repo_files)}")

# ==============================
# 3. 파일 단위 요약(개별 파일 - LLM 여러 번) + 저장
# ==============================

file_summaries = []
total = len(repo_files)

os.makedirs(DIVIDED_SUMMARY_DIR, exist_ok=True)

for idx, f in enumerate(repo_files, start=1):
    print(f"[{idx}/{total}] START  {f['path']}")

    try:
        summary = summarize_file_with_llm(
            path=f['path'],
            content=f["content"],
            client=client
        )

        # 메모리에도 저장
        file_summaries.append(summary)

        # 즉시 파일로 저장 (checkpoint)
        filename = (f["path"].replace("\\", "_").replace("/", "_") + ".json")
        output_path = os.path.join(DIVIDED_SUMMARY_DIR, filename)

        with open(output_path, "w", encoding="utf-8") as out:
            json.dump(summary, out, ensure_ascii=False, indent=2)

        print(f"[{idx}/{total}] DONE   {f['path']}")

    except Exception as e:
        print(f"[{idx}/{total}] ERROR  {f['path']} :: {e}")


# ==============================
# 4. 파일 단위 요약 결과를 배치(10)으로 나누기
# ==============================
batches = split_into_batches(
    items=file_summaries,
    batch_size=10
)
print("배치(10)으로 나누기 완료")

# ==============================


# 5. 배치 단위로 의미 요약(LLM 1회 x batch 수) + 저장
# ==============================
batch_semantic_summaries = []

os.makedirs(BATCH_SUMMARY_DIR, exist_ok=True)

total = len(batches)

for idx, batch in enumerate(batches, 1):
    print(f"[BATCH {idx}/{total}] START")

    batch_json = {
        "batch_id": idx,
        "files_count": len(batch),
        "summaries": batch
    }

    try:
        semantic = summarize_batch_semantic(
            batch_data=batch_json,
            client=client,
            model=MODEL_NAME
        )

        batch_semantic_summaries.append(semantic)

        output_path = os.path.join(
            BATCH_SUMMARY_DIR,
            f"batch_{idx}_semantic.json"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(semantic, f, ensure_ascii=False, indent=2)

        print(f"[BATCH {idx}/{total}] DONE")

    except Exception as e:
        print(f"[BATCH {idx}/{total}] ERROR :: {e}")

print("배치 별 요약 완료")


# ==============================
# 6. 요약된 파일들 바탕으로 최종 리포트 생성
# ==============================
final_result = analyze_project_from_batches(
    batch_semantic_summaries=batch_semantic_summaries,
    client=client,
    model=MODEL_NAME,
    repo_analysis_id=f"{OWNER}_{REPO}"
)


# ==============================
# 7. 커밋 스타일 분석해서 협업 지표 리포트에 추가
# =============================

with open(
    rf"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl\{REPO}\{OWNER}_{REPO}_commit_metadata.json",
    encoding="utf-8"
) as f:
    commit_metadata = json.load(f)

commit_style = analyze_commit_style(
    commit_metadata=commit_metadata,
    client=client,
    model=MODEL_NAME
)
final_result["collaboration_style"] = commit_style


# ==============================
# 8. github api로 해당 레포에서 사용 언어 리스트 가져와서 리포트에 추가
# ==============================
languages = get_repo_main_languages(owner=OWNER, repo=REPO)
final_result["tech_stack"]["languages"] = languages

    
# ==============================
# 9. 분석 리포트 저장
# ==============================
final_output_path = os.path.join(
    BASE_OUTPUT_DIR, f"{OWNER}_{REPO}_single_analysis.json"
)

with open(final_output_path, "w", encoding="utf-8") as f:
    json.dump(final_result, f, ensure_ascii=False, indent=2)

print("프로젝트 최종 분석 완료")