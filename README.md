# Screenplay Converter

TXT 또는 DOCX 원고를 읽어 개발용 메타 텍스트를 제거하고,
씬 / 지문 / 인물명 / 대사 구조로 재분류한 뒤,
헐리우드 표준에 가까운 DOCX 시나리오 파일로 출력하는 Streamlit 앱입니다.

## 주요 기능
- `.txt`, `.docx` 입력 지원
- Beat 요약, 작법 메모, 구분선 제거
- Scene Heading / Action / Character / Dialogue / Parenthetical 분류
- DOCX 출력
- `template.docx`가 있으면 템플릿 사용
- 템플릿이 없어도 기본 DOCX 생성 가능

## 파일 구성
- `main.py` : 앱 실행 파일
- `prompt.py` : 향후 AI 보조 규칙
- `requirements.txt` : 패키지 목록
- `template.docx` : 선택 템플릿
- `.gitignore`

## 설치
```bash
pip install -r requirements.txt
