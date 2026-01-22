from backend_single_analysis_method import collect_spring_backend_files, filter_backend_files_by_keywords, summarize_file_with_llm, split_into_batches,summarize_batch_semantic, analyze_project_from_batches, analyze_commit_style, call_with_retry
import os
import json
from dotenv import load_dotenv
import time

load_dotenv()

gms_api_key=os.getenv("GMS_API_KEY")
gms_base_url=os.getenv("GMS_BASE_URL")


OWNER = 'HTTP501'
REPO = 'idk'

position = 'backend' # backend / frontend

if position == 'backend':
    backend_framework = 'spring' # spring / fastapi / django

    if backend_framework == "spring":
        language = "Java"    
        TARGET_DIRS = {"controller", "service", "repository"}
        SERVICE_KEYWORDS = ["@Transactional","if (", "for (", "while (","try {", "catch (","throw new","validate", "check","Event", "publish"]
        REPOSITORY_KEYWORDS = ["@Query","nativeQuery", "join","fetch","existsBy","findBy","countBy"]
    elif backend_framework == "fastapi":
        language = "Python"
        TARGET_DIRS = {"routers", "router", "api", "services", "service", "crud", "db", "models", "schemas"}
        SERVICE_KEYWORDS = ["Depends(", "def ", "async def", "if ", "for ", "while ", "try:", "except", "raise ", "validate", "process", "logic"]
        REPOSITORY_KEYWORDS = ["select(", "insert(", "update(", "delete(", "join(", "where(", "session.execute", "db.query", "await session", "commit()"]
    elif backend_framework == "django":
        language = "Python"
        TARGET_DIRS = {"views", "models", "serializers", "services", "repositories"}
        SERVICE_KEYWORDS = ["def ", "class ", "if ", "for ", "try:", "except", "raise ", "validate", "process"]
        REPOSITORY_KEYWORDS = [".objects.filter", ".objects.get", ".objects.create", ".objects.update", ".objects.exclude", ".objects.annotate", ".objects.aggregate", "select_related", "prefetch_related"]

user_input = "백엔드에서 돈포켓, 목표저축, 자동이체 기능을 구현했습니다"

repo_root = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl\idk"


#################################################
### 필요한 파일 선별
selected_files = collect_spring_backend_files(repo_root, TARGET_DIRS=TARGET_DIRS)
print("1차 선별:", len(selected_files)) # 핵심 디렉토리로 선별

filtered_files = filter_backend_files_by_keywords(selected_files, SERVICE_KEYWORDS=SERVICE_KEYWORDS, REPOSITORY_KEYWORDS=REPOSITORY_KEYWORDS)
print("2차 선별:", len(filtered_files)) # 코드 내 핵심 keyword로 선별


#####################################################
### 개별 파일 분석 및 요약
BASE_SLEEP = 1.5          # 기본 대기
LONG_SLEEP_EVERY = 15     # 15개마다
LONG_SLEEP_TIME = 180     # 3분

filtered_file_summaries = []

for i, file in enumerate(filtered_files):
    result = call_with_retry(
        lambda: summarize_file_with_llm(
            path=file["path"],
            content=file["content"],
            gms_api_key=gms_api_key,
            gms_base_url=gms_base_url,
            user_input = user_input
        )
    )

    filtered_file_summaries.append(result)

    INDIVIDUAL_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\backend_single_analysis\individual_summaries"
    os.makedirs(INDIVIDUAL_DIR, exist_ok=True)
    
    output_path = os.path.join(INDIVIDUAL_DIR, f"{REPO}_files_{i}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"선별된 파일 저장 완료: {output_path}")

    time.sleep(BASE_SLEEP)

    # 🛑 누적 쿼터 회피용 강제 휴식
    if (i + 1) % LONG_SLEEP_EVERY == 0:
        print(f"⏸️ {LONG_SLEEP_EVERY}개 처리 → {LONG_SLEEP_TIME//60}분 휴식")
        time.sleep(LONG_SLEEP_TIME)

        
###############################
### 배치로 나누기
batches = split_into_batches(
    items=filtered_file_summaries,
    batch_size=10
)
print("배치(10)으로 나누기 완료")


##########################################################

# 5. 배치 단위로 의미 요약(LLM 1회 x batch 수)
batch_semantic_summaries = []
BATCH_SUMMARY_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\backend_single_analysis\batch_summaries"
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
            gms_api_key=gms_api_key,
            gms_base_url=gms_base_url
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
    gms_api_key=gms_api_key,
    gms_base_url=gms_base_url, 
    repo_analysis_id=f"{OWNER}_{REPO}"
)

final_result['language'] = language # 언어 우선 Java 기반으로 분석



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
    gms_api_key=gms_api_key,
    gms_base_url=gms_base_url
)
final_result["collaboration_style"] = commit_style


# ==============================
# 9. 분석 리포트 저장
# ==============================
BASE_OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\backend_single_analysis"

final_output_path = os.path.join(
    BASE_OUTPUT_DIR, f"{OWNER}_{REPO}_single_analysis.json"
)

with open(final_output_path, "w", encoding="utf-8") as f:
    json.dump(final_result, f, ensure_ascii=False, indent=2)

print("프로젝트 최종 분석 완료")