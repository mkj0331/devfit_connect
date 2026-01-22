import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# IT 기준 채용공고 목록 페이지
LIST_URL = (
    "https://jasoseol.com/search?"
    "dutyGroupIds=160%2C164%2C165%2C166%2C167%2C168%2C169%2C170%2C171"
    "%2C172%2C173%2C174%2C175%2C176%2C177%2C178%2C179%2C180%2C181"
    "%2C182&excludeClosed=true"
)

print("채용공고 목록 수집 중")
res = requests.get(LIST_URL, headers=HEADERS)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")

# recruit ID 수집
recruit_ids = set()

for a in soup.find_all("a", href=True):
    match = re.match(r"^/recruit/(\d+)$", a["href"])
    if match:
        recruit_ids.add(match.group(1))

recruit_ids = sorted(recruit_ids)

print(f"수집된 채용공고 수: {len(recruit_ids)}")

# 3️⃣ 각 공고 상세 페이지 순회하며 이미지 URL 수집
recruit_image_map = {}  # {recruit_id: image_url}

for rid in recruit_ids:
    detail_url = f"https://jasoseol.com/recruit/{rid}"
    print(f"➡️ 공고 {rid} 처리 중...")

    try:
        res = requests.get(detail_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        json_ld_tags = soup.find_all("script", type="application/ld+json")

        image_url = None

        for tag in json_ld_tags:
            if not tag.string:
                continue

            data = json.loads(tag.string)
            graph = data.get("@graph", [])

            for node in graph:
                if node.get("@type") == "ImageObject":
                    image_url = node.get("url")
                    break

            if image_url:
                break

        if image_url:
            recruit_image_map[rid] = image_url
            print(f"   ✅ 이미지 URL 추출 성공")
        else:
            print(f"   ⚠️ 이미지 URL 없음")

        # 서버 부담 방지
        time.sleep(0.3)

    except Exception as e:
        print(f"   ❌ 오류 발생: {e}")

# 4️⃣ 결과를 JSON 파일로 저장
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

output_path = os.path.join(OUTPUT_DIR, "recruit_image_map.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(recruit_image_map, f, ensure_ascii=False, indent=2)

print(f"\n💾 결과 JSON 저장 완료: {output_path}")
