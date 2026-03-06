# TODO: 트리 구조 배치 처리 API

## 현재 상황 (완료)

- `t_preset_step`, `t_process_step` 테이블 `parent_id` 컬럼 추가 완료
- Preset/Process CRUD API `parent_id` 지원 완료
- 배치 처리 API는 아직 flat list 순차 처리만 지원

---

## 구현 과제

### 1. 트리 구조 배치 처리 API

- [ ] 기존 배치 처리 API를 트리 구조 입력으로 확장
  - 요청: 트리 형태의 steps (parentId 포함) + 원본 이미지
  - 루트 노드부터 DFS/BFS 순회, 부모 결과를 자식 입력으로 전달
  - 분기(같은 parent의 siblings): 동일 입력에 서로 다른 알고리즘 적용
- [ ] 응답 구조 설계
  - 노드별 결과: `{ nodeId, thumbnail, executionMs }[]`
  - 중간 노드: 메모리에서 저해상도 썸네일(~150px) base64로 반환 (파일 저장 안 함)
  - 리프 노드: 최종 결과만 파일 저장 (`t_file` 레코드 생성) + Process 기록
- [ ] 썸네일 생성 유틸: OpenCV resize로 프리뷰용 저해상도 이미지 생성

### 2. 부분 재실행 API (서버 무상태, 캐시 불필요)

- [ ] 기존 batch API를 그대로 활용
  - 클라이언트가 전체 실행 시 노드별 결과 이미지를 보유
  - 파라미터 변경 시 클라이언트가 **부모 노드의 결과 이미지 + 변경된 서브트리 steps**를 전송
  - 서버는 받은 이미지에 서브트리 필터만 적용 → 기존 batch 처리와 동일 구조
  - 별도 캐시/세션 관리 불필요
- [ ] `POST /image-processing/batch-tree` (트리 배치 처리)
  ```
  Body: {
    file: File,              // 입력 이미지 (전체 실행=원본, 부분 실행=부모 결과)
    steps: JSON              // 트리 형태 steps (parentId 포함)
  }
  Response: {
    results: [{ nodeId, thumbnail(base64), executionMs }],
    leafResults: [{ nodeId, fileId, imageUrl }]   // 리프 노드만 파일 저장
  }
  ```
  - 전체 실행: 원본 이미지 + 전체 트리
  - 부분 실행: 부모 결과 이미지 + 변경 노드부터의 서브트리
