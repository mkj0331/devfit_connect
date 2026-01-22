from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
import json
import os

### 개발 직군 공고 상세 페이지 가져오기 ###

# 개발 직군 공고들 url
LIST_URL = "https://www.wanted.co.kr/wdlist/518?country=kr&job_sort=job.popularity_order&years=-1&locations=all"

# url의 hash 반환(primary key job id 설정 위함)
import hashlib
def make_job_profile_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]

# 개발 직군 공고 url의 id 가져오기
def get_job_ids():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(LIST_URL, wait_until="networkidle")

        # 스크롤 여러 번 내려서 카드 로드(횟수 지정)
        for _ in range(1):
            page.mouse.wheel(0, 3000)
            time.sleep(1.5)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    job_ids = []

    for a in soup.select("div[data-cy='job-card'] a[href^='/wd/']"):
        href = a.get("href")   # /wd/328431
        job_id = href.split("/")[-1]
        job_ids.append(job_id)

    return list(set(job_ids))   # 중복 제거


# 특정 공고의 elements 가져오기
def crawl_one_job(job_id):
    URL = f"https://www.wanted.co.kr/wd/{job_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ko-KR"
        )
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        try:
            # 우대사항 등 안보이는 것까지 가져오도록
            page.get_by_role("button", name="상세 정보 더 보기").click()
            page.wait_for_timeout(1500)
        except:
            pass

        html = page.content()
        browser.close()

    return html


### 크롤링 실행

job_ids = get_job_ids()

for job_id in job_ids:
    print(f"크롤링: {job_id}")

    # job_profile_id (url hash)
    URL = f"https://www.wanted.co.kr/wd/{job_id}"
    job_profile_id = make_job_profile_id(URL) 

    html = crawl_one_job(job_id)
    soup = BeautifulSoup(html, "html.parser")

    # 회사명
    company_name = soup.select_one(".JobHeader_JobHeader__Tools__Company__Link__NoBQI")
    company_name_text = company_name.get_text("\n", strip=True) if company_name else ""

    # 직무
    job_name = soup.select_one('.wds-58fmok')
    job_name_text = job_name.get_text('\n', strip=True)

    # 본문(포지션 상세, 자격요건, ...)
    article = soup.select_one(".JobDescription_JobDescription__s2Keo")
    article_text = article.get_text("\n", strip=True) if article else ""

    # 마감일
    deadline = soup.select_one(".JobDueTime_JobDueTime__yvhtg")
    deadline_text = deadline.get_text("\n", strip=True) if deadline else ""

    full_text = article_text + f"\n{deadline_text}"


    
    # 파싱한 내용 중에 원하는 문구 사이의 내용들 추출
    def extract_section(text, start, end=None):
        if end:
            pattern = rf"{start}\n(.*?)(?=\n{end})"
        else:
            pattern = rf"{start}\n(.*)"

        match = re.search(pattern, text, re.S)
        return match.group(1).strip() if match else None

    #  • 기준으로 리스트화
    def split_bullets(section_text):
        if not section_text:
            return []
        return [line.strip(" •") for line in section_text.split("\n") if line.strip()]


    data = {
        "job_profile_id": job_profile_id,
        "회사명": company_name_text,
        "직무": job_name_text,
        "포지션 상세": split_bullets(
            extract_section(full_text, "포지션 상세", "주요업무")
        ),
        "주요업무": split_bullets(
            extract_section(full_text, "주요업무", "자격요건")
        ),
        "자격요건": split_bullets(
            extract_section(full_text, "자격요건", "우대사항")
        ),
        "우대사항": split_bullets(
            extract_section(full_text, "우대사항", "혜택 및 복지")
        ),
        "혜택 및 복지": split_bullets(
            extract_section(full_text, "혜택 및 복지", "채용 전형")
        ),
        "채용 전형": split_bullets(
            extract_section(full_text, "채용 전형", "마감일")
        ),
        "마감일": extract_section(full_text, "마감일")
    }

    ### output/employ_notice 경로로 회사명.json 파일 로딩
    output_dir = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\crawling\output\employ_notice"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{company_name_text}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"JSON 저장 완료: {output_path}")