from typing import Dict, List
import json

def build_job_profile_text(job: Dict) -> str:
    """
    채용공고 JSON 하나를 받아
    임베딩용 job_profile_text를 생성한다.
    """

    def join_lines(lines: List[str]) -> str:
        return "\n".join(f"- {line.strip()}" for line in lines if line.strip())

    sections = []

    # 회사 / 직무
    sections.append(f"[회사명] {job.get('회사명', '').strip()}")
    sections.append(f"[직무] {job.get('직무', '').strip()}")

    # 회사/포지션 소개
    position_detail = job.get("포지션 상세", [])
    if position_detail:
        sections.append("\n[회사 및 포지션 소개]")
        sections.append(join_lines(position_detail))

    # 주요 업무
    main_tasks = job.get("주요업무", [])
    if main_tasks:
        sections.append("\n[주요업무]")
        sections.append(join_lines(main_tasks))

    # 자격 요건
    requirements = job.get("자격요건", [])
    if requirements:
        sections.append("\n[자격요건]")
        sections.append(join_lines(requirements))

    # 우대 사항
    preferred = job.get("우대사항", [])
    if preferred:
        sections.append("\n[우대사항]")
        sections.append(join_lines(preferred))

    # 하나의 텍스트로 결합
    job_profile_text = "\n".join(sections).strip()

    return job_profile_text


## 임베딩 벡터 생성(복지, 전형, 마감일 제거된 상태에서)

# api 설정
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # .env에서 GMS_KEY 로드

client = OpenAI(
    api_key=os.getenv("GMS_API_KEY"),
    base_url=os.getenv("GMS_BASE_URL")
)

# 단일 공고 기준! 임베딩 생성 함수 -> 근데 공고 추천할 때 분석 내용 임베딩벡터는 모든 레포 분석한거 통합한걸 기준으로 임베딩벡터 만들어야 하는거 아닌가?
def embed_single_job(job_profile_text: str) -> List[float]:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=job_profile_text
    )
    return response.data[0].embedding


# 공고들 순회하면서 임베딩 생성하기 위해 경로 가져오기 
EMPLOY_NOTICE_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\output\employ_notice"
EMBEDDING_OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\output\embedding"

os.makedirs(EMBEDDING_OUTPUT_DIR, exist_ok=True)


json_files = [
    f for f in os.listdir(EMPLOY_NOTICE_DIR)
    if f.endswith(".json")
]
print(f"총 공고 파일 수: {len(json_files)}")

for idx, filename in enumerate(json_files, start=1):
    json_path = os.path.join(EMPLOY_NOTICE_DIR, filename)

    with open(json_path, "r", encoding="utf-8") as f:
        job = json.load(f)

    job_profile_id = job.get("job_profile_id")
    if not job_profile_id:
        print(f"job_profile_id 없음 → 스킵: {filename}")
        continue

    output_path = os.path.join(
        EMBEDDING_OUTPUT_DIR,
        f"{job_profile_id}.json"
    )

    if os.path.exists(output_path):
        print(f"[{idx}/{len(json_files)}] 이미 존재 → 스킵: {job_profile_id}")
        continue

    job_profile_text = build_job_profile_text(job)
    if not job_profile_text.strip():
        print(f"[{idx}/{len(json_files)}] 텍스트 비어있음 → 스킵: {job_profile_id}")
        continue

    embedding = embed_single_job(job_profile_text)

    embedding_data = {
        "job_profile_id": job_profile_id,
        "embedding": embedding
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(embedding_data, f, ensure_ascii=False)

    print(f"[{idx}/{len(json_files)}] 임베딩 생성 완료: {job_profile_id}")

print("모든 공고 임베딩 처리 완료")



# # 다른 경로에 있는 json 파일 로드
# import json
# JOB_JSON_PATH = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\output\employ_notice\낭만아지트.json"
# with open(JOB_JSON_PATH, "r", encoding="utf-8") as f:
#     job = json.load(f)

# job_profile_text = build_job_profile_text(job)

# embedding = embed_single_job(job_profile_text) 
# job_profile_id = job.get("job_profile_id")

# EMBEDDING_OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\output\embedding"
# os.makedirs(EMBEDDING_OUTPUT_DIR, exist_ok=True)

# embedding_data = {
#     "job_profile_id": job_profile_id,
#     "embedding": embedding
# }

# output_path = os.path.join(
#     EMBEDDING_OUTPUT_DIR,
#     f"{job_profile_id}.json"
# )

# with open(output_path, "w", encoding="utf-8") as f:
#     json.dump(embedding_data, f, ensure_ascii=False)

# print(f"임베딩 JSON 저장 완료: {output_path}")


# # 여러 공고 배치 처리 -> 우선 단일 공고 먼저 테스트 해보자 
# from typing import Dict, List
# import json

# def generate_job_embeddings(jobs: List[Dict]) -> List[Dict]:
#     """
#     여러 채용공고 JSON을 받아
#     job_profile_text + embedding을 생성한다.
#     """
#     embedded_jobs = []

#     for idx, job in enumerate(jobs):
#         job_profile_text = build_job_profile_text(job)
#         embedding = embed_job_profile_text(job_profile_text)

#         embedded_jobs.append({
#             # "job_id": f"job_{idx}", # 나중에 추천 결과와 원본 공고 JSON을 매칭하는 키?
#             "company": job.get("회사명"),
#             "title": job.get("직무"),
#             "job_profile_text": job_profile_text,
#             "embedding": embedding
#         })

#     return embedded_jobs


