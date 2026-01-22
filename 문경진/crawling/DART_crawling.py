import os
import re
from bs4 import BeautifulSoup
import OpenDartReader

api_key = '5ddf5d0ecda283666603b615b64362aef1e16aee'

dart = OpenDartReader(api_key) 


# 회사명 불러오는 함수
def load_company_names():
    EMPLOY_NOTICE_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\crawling\output\employ_notice"
    companies = []

    for filename in os.listdir(EMPLOY_NOTICE_DIR):
        if not filename.endswith(".json"):
            continue

        name = filename.replace(".json", "")
        # (NAVER), (숨고,Soongo) 제거
        name = re.sub(r"\(.*?\)", "", name).strip()
        companies.append(name)

    return companies

# # 최종 포맷 생성
# def build_reference_text(sections: dict) -> str:
#     texts = []
#     for v in sections.values():
#         texts.append(f"【{v['title']}】\n{v['content']}")
#     return "\n\n".join(texts)
    

# 크롤링 코드
def crawl_dart(company: str):
    print(f"DART 크롤링 시작: {company}")

    try:
        reports = dart.list(company)

        quarter_reports = reports[
            reports['report_nm'].str.contains("분기보고서|반기보고서", na=False)
        ]

        if quarter_reports.empty:
            print(f"분기/반기보고서 없음: {company}")
            return

        latest = quarter_reports.iloc[0]
        rcept_no = latest['rcept_no']

        xml = dart.document(rcept_no)
        soup = BeautifulSoup(xml, "lxml-xml")
        full_text = soup.get_text("\n", strip=True)

        # II. 사업의 내용 추출
        section2_pattern = re.compile(
            r"II\.\s*사업의 내용(.+?)(?=III\.|\Z)",
            re.DOTALL
        )

        section2 = section2_pattern.search(full_text)
        business_section = section2.group(0)


        ### 각 회사 별 보고서 형식 차이로, 해당 부분은 보완 필요(사업의 개요 전체를 llm한테 input으로 준다면 상관 없음. but 비용 문제가 있다면 텍스트 요약 모델로 요약해서 input 줘도 될 듯)
        # # 번호 헤더 기준 분리
        # item_pattern = re.compile(r"\n\s*(\d+)\.\s*([^\n]+)\n")
        # matches = list(item_pattern.finditer(business_section))

        # sections = {}

        # for i, m in enumerate(matches):
        #     num = m.group(1)
        #     title = m.group(2).strip()
        #     start = m.end()
        #     end = matches[i + 1].start() if i + 1 < len(matches) else len(business_section)

        #     sections[num] = {
        #         "title": title,
        #         "content": business_section[start:end].strip()
        #     }

        # # 필요한 항목만 선택
        # TARGET_SECTIONS = ["1", "2", "4"] # 사업의 개요, 주요 제품 및 서비스, 매출 및 수주상황
        # selected = {k: sections[k] for k in TARGET_SECTIONS if k in sections}

        # reference_text = build_reference_text(selected)

        # 저장
        OUTPUT_DIR = r"C:\Users\SSAFY\Desktop\S14P11B111\문경진\crawling\output\dart"
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        output_path = os.path.join(OUTPUT_DIR, f"{company}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(business_section)

        print(f"저장 완료: {output_path}")

    except Exception as e:
        print(f"실패: {company} / {e}")


import time

def main():
    company_list = load_company_names()
    print(f"총 대상 회사 수: {len(company_list)}")

    for company in company_list:
        crawl_dart(company)
        time.sleep(1.0)  # DART rate limit 대비

if __name__ == "__main__":
    main()
