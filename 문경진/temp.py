import requests
from bs4 import BeautifulSoup
import re

LIST_URL = "https://jasoseol.com/search?dutyGroupIds=160%2C164%2C165%2C166%2C167%2C168%2C169%2C170%2C171%2C172%2C173%2C174%2C175%2C176%2C177%2C178%2C179%2C180%2C181%2C182&excludeClosed=true"  # ← 실제 IT 필터 URL로 수정
headers = {
    "User-Agent": "Mozilla/5.0"
}

res = requests.get(LIST_URL, headers=headers)
res.raise_for_status()

soup = BeautifulSoup(res.text, "html.parser")

recruit_ids = set()

# 모든 a 태그 중 /recruit/숫자 패턴 찾기
for a in soup.find_all("a", href=True):
    match = re.match(r"^/recruit/(\d+)$", a["href"])
    if match:
        recruit_ids.add(match.group(1))

recruit_ids = sorted(recruit_ids)

print("✅ 수집된 채용공고 ID:")
for rid in recruit_ids:
    print(rid)
