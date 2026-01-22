import os
import subprocess
import re

OWNER = 'HTTP501'
REPO = 'idk'

base_dir = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\github_crawl" # 레포 생성 경로
repo_url = rf"https://github.com/{OWNER}/{REPO}.git" # 가져올 레포 url

# 레포 클론해서 가져오기
def clone_github_repo(repo_url: str, base_dir="repos") -> str:

    os.makedirs(base_dir, exist_ok=True)

    repo_name = re.sub(r"\.git$", "", repo_url.split("/")[-1])
    repo_path = os.path.join(base_dir, repo_name)

    if os.path.exists(repo_path):
        print(f"이미 존재함: {repo_path}")
        return repo_path

    print(f"Cloning {repo_url}")
    subprocess.run(
        ["git", "clone", repo_url, repo_path],
        check=True
    )

    return repo_path

clone_github_repo(repo_url=repo_url, base_dir=base_dir)


