## 코딩 가이드라인

아래 파일을 반드시 읽고 따를 것

- [docs/coding-guideline.md]

## 프로젝트 구조

- [docs/architecture.md]

## DB 구조

- alembic/versions 하위에서 구조 확인

## Plan 관리 규칙

- Notion "프로젝트 작업" DB에 작성
  - 작업 유형: `plan`
  - 상태: `완료`
  - 나머지 속성은 Notion 정리 지침 따름
- 본문: 배경, 방안(UI 구조/구현 포인트 등), 핵심 구성 요소를 정리
- 사용자가 Notion에서 검토 후 승인할 때까지 구현 시작하지 말 것

## 학습 노트 규칙

- 사용자가 개념/용어를 질문하면, 대화 마지막에 해당 내용을 docs/note/ 하위 관련 md 파일에 정리할지 물어볼 것
- 기존 파일에 관련 섹션이 있으면 추가, 없으면 새 섹션 생성

## 수정 규칙

- `npx pyright`를 실행하여 0 errors를 확인할 것
- 코드 수정 후에는 Notion에 정리한다.
  - 문서 수정은 제외하고 기록

### Notion 정리 지침

- DB: 개발 > 프로젝트 > 프로젝트 작업
- 데이터 소스 ID: `336705ff-d265-80a6-860d-000b6e9262ad`
- 속성 매핑:
  - `제목` (Title): 작업 제목
  - `프로젝트 정보` (Relation): `["https://www.notion.so/338705ffd2658112b2c3cb65104b125a"]` (image-processing Backend)
  - `작업 유형` (Multi-select): plan / feature / refactoring / bugfix / config / test / style / docs
  - `상태` (Status): 요청전 / 요청 / 작업중 / 승인대기 / PR 리뷰 / 승인 / 완료
  - `우선순위` (Select): 높음 / 보통 / 낮음
  - `시작일` (Date): 작업 시작일
  - `종료일` (Date): 작업 종료일
  - `Git Branch명` (Text): 작업 브랜치명 (있는 경우)
  - `Git Process Type` (Select): auto-merge / create-pr / push-only
  - `PR URL` (URL): PR 링크 (있는 경우)
  - `상위 작업` (Relation): 상위 작업 페이지 (있는 경우, self-relation)
- 페이지 아이콘: 작업 유형에 따라 지정
  - plan: 📋 / feature: ✨ / refactoring: ♻️ / bugfix: 🐛 / config: ⚙️ / test: 🧪 / style: 🎨 / docs: 📝
  - Multi-select 시 첫 번째 유형 기준
- 본문: 배경(왜), 변경 내용, 결과를 간결하게 작성
- 작업 단위는 하루가 아니라 "의미 단위" — 하루에 2건이면 2페이지, 이틀 걸렸으면 1페이지
