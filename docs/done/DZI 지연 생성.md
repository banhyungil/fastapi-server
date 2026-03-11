# DZI 지연 생성 — API 분리

## 변경 배경

배치 처리 시 `fullSize=true`이면 모든 고해상도 노드에 대해 DZI 타일을 즉시 생성했다.
- 8K 이미지 기준 `dzsave` 1회에 수초 소요
- 사용자가 줌을 안 해도 타일이 생성됨 → 불필요한 I/O + 처리 시간 낭비
- 줌 클릭 시 배치 재처리 + 이미지 재업로드까지 발생

## 변경 내용

배치 처리와 DZI 생성을 완전히 분리.

### 기존
```
줌 클릭 → fullSize=true로 배치 재처리 (이미지 재업로드 포함)
        → 경로상 모든 노드 DZI 생성
        → dziUrl 반환
```

### 변경 후
```
배치 처리 → 썸네일(base64) 전용. fullSize/dzi 관련 로직 없음

줌 클릭 → POST /image-processing/dzi/{file_id} (steps + nodeId)
        → 서버가 file_id로 원본 이미지 직접 로드 (재업로드 불필요)
        → 타겟 노드까지만 체인 처리 → 타겟 노드만 DZI 생성
        → 고해상도: dziUrl 반환 / 저해상도: imageUrl 반환
```

## 파일 변경 목록

### 백엔드

| 파일 | 변경 |
|------|------|
| `app/repos/file_repo.py` | `find_by_id()` 추가 |
| `app/services/file_service.py` | `find_file_by_id()` 추가 |
| `app/services/image_processing_service.py` | `process_image_batch_tree()`에서 `full_size`/`file_id` 제거. `generate_dzi_for_node()` 추가 |
| `app/api/endpoints/image_processing.py` | `batch-tree`에서 `fileId`/`fullSize` 제거. `POST /dzi/{file_id}` 추가 |
| `app/schemas/file.py` | `TreeNodeResultResponse`에서 `dzi_url`/`is_high_res` 제거. `DziResponse` 추가 |

### 프론트엔드

| 파일 | 변경 |
|------|------|
| `src/apis/imgPrcApi.ts` | `batchTreeProcessing()` options 제거. `generateDzi(fileId, steps, nodeId)` 수정 |
| `src/types/imgPrcType.ts` | `TreeNodeResult`에서 `dziUrl`/`isHighRes` 제거 |
| `src/pages/ImgPrcPage.vue` | 줌 팝업: 배치 재처리 제거 → `generateDzi()` 단독 호출 |

## 기대 효과

- 배치 처리 속도: DZI 생성 시간 0 (썸네일 base64만 반환)
- 줌 클릭 시 **타겟 노드만** DZI 생성 (경로상 다른 노드 DZI 미생성)
- 프론트에서 이미지 재업로드 불필요 (서버가 file_id로 직접 로드)
