# PK 만들기

# 임베딩용 텍스트 생성 함수
def build_repo_analysis_embedding_text(analysis: dict) -> str:
    parts = []

    # 1. 프로젝트 도메인
    project_domain = analysis.get("project_domain")
    if project_domain:
        parts.append(f"This project focuses on {project_domain}.")

    # 2. 기술 스택
    tech_stack = analysis.get("tech_stack", {})

    languages = tech_stack.get("languages", [])
    frameworks = tech_stack.get("frameworks", [])
    libraries = tech_stack.get("libraries", [])

    if languages:
        parts.append(f"Programming Languages: {', '.join(languages)}.")
    if frameworks:
        parts.append(f"Frameworks: {', '.join(frameworks)}.")
    if libraries:
        parts.append(f"Libraries and Tools: {', '.join(libraries)}.")

    # 3. 핵심 기능
    key_features = analysis.get("key_features", [])
    if key_features:
        parts.append("Key Features implemented in this project:")
        for feature in key_features:
            name = feature.get("feature")
            desc = feature.get("description")
            if name and desc:
                parts.append(f"- {name}: {desc}")

    # 4. 협업 및 개발 스타일
    collaboration = analysis.get("collaboration_analysis", {})
    if collaboration:
        parts.append("Development and Collaboration Style:")

        collab_type = collaboration.get("collaboration")
        if collab_type:
            parts.append(f"- Collaboration Type: {collab_type}")

        dev_style = collaboration.get("development_style", {})
        if isinstance(dev_style, dict):
            for k, v in dev_style.items():
                parts.append(f"- {k.replace('_', ' ').title()}: {v}")

        traits = collaboration.get("developer_traits", [])
        if traits:
            parts.append("- Developer Traits:")
            for t in traits:
                parts.append(f"  • {t}")

    return "\n".join(parts)


