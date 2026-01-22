import os
import json
import requests
from datetime import datetime

# ==============================
# 설정값
# ==============================
OWNER = 'HTTP501'
REPO = 'idk'

# 저장 경로
SAVE_DIR = rf"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl\{REPO}"
SAVE_FILE = f"{OWNER}_{REPO}_commit_metadata.json"
SAVE_PATH = os.path.join(SAVE_DIR, SAVE_FILE)

# ==============================
# GitHub 커밋 수집 함수
# ==============================
def get_all_commits(owner, repo):
    page = 1
    all_commits = []

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-analysis-bot"
    }

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {
            "per_page": 100,
            "page": page
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        commits = response.json()
        if not commits:
            break

        all_commits.extend(commits)
        page += 1

    return all_commits

# ==============================
# 메타데이터 구조화
# ==============================
def structure_commits(commits):
    structured = []

    for c in commits:
        commit_info = c.get("commit", {})
        author_info = commit_info.get("author", {}) or {}
        committer_info = commit_info.get("committer", {}) or {}

        structured.append({
            "message": commit_info.get("message"),
            "author_name": author_info.get("name"),
            "author_date": author_info.get("date")
        })

    return structured

# ==============================
# JSON 저장
# ==============================
def save_to_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "repository": f"{OWNER}/{REPO}",
                "generated_at": datetime.utcnow().isoformat(),
                "total_commits": len(data),
                "commits": data
            },
            f,
            ensure_ascii=False,
            indent=2
        )

# ==============================
# 실행
# ==============================
if __name__ == "__main__":
    print("GitHub 커밋 수집 시작...")
    commits = get_all_commits(OWNER, REPO)

    print(f"총 커밋 수: {len(commits)}")

    print("커밋 메타데이터 구조화 중...")
    structured_commits = structure_commits(commits)

    print("JSON 파일 저장 중...")
    save_to_json(structured_commits, SAVE_PATH)

    print(f"저장 완료. 저장 위치:\n{SAVE_PATH}")
