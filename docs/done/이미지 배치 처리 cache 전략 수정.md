# 이미지 배치 처리 캐시 전략 수정

## 기존 문제

- 캐시 키: `sha256(parent_key + prcType + params_json)`
- 파라미터를 조금만 바꿔도 새로운 캐시 파일 생성
- 파라미터 조정이 빈번하므로 조합이 기하급수적으로 증가
- TTL/LRU 정리로도 단시간 파일 폭증을 막기 어려움

## 수정 전략: node_id 기반 파일 덮어쓰기

캐시(재사용) 목적이 아닌, **URL 반환용 임시 파일** 방식으로 전환한다.

### 핵심 아이디어
- 파일 경로: `uploads/cache/{file_id}/{node_id}.png`
- 파라미터가 바뀌면 **동일 파일을 덮어쓰기**
- 파일 수 = 노드 수 (고정)
- URL이 동일하므로 base64 대비 응답 크기 절감 효과 유지

### 파일 경로 규칙
```
uploads/cache/{file_id}/          ← 원본 파일별 디렉토리
  ├── {nodeId_1}.png
  ├── {nodeId_2}.png
  └── {nodeId_3}.png
```

### API 변경

#### 요청 (변경 없음)
```
POST /api/image-processing/batch-tree
  - file: 원본 이미지
  - steps: JSON 배열 (nodeId, prcType, parameters, parentId)
  - fileId: 원본 파일 ID
```

#### 응답
```json
{
  "totalExecutionMs": 120.5,
  "results": [
    {
      "nodeId": "abc-123",
      "imageUrl": "/uploads/cache/{fileId}/abc-123.png?t=1709945123",
      "executionMs": 45.2
    }
  ]
}
```

- `?t=` 타임스탬프: 브라우저 이미지 캐시 무효화용
- `cached` 필드 제거 (항상 연산 수행)

### 서버 구현 변경

#### process_image_batch_tree
```
1. 각 노드 DFS 순회
2. 부모 이미지 → 현재 노드 필터 적용
3. 결과를 uploads/cache/{file_id}/{node_id}.png 에 저장 (덮어쓰기)
4. URL 반환 (타임스탬프 쿼리 파라미터 포함)
```

#### 제거 항목
- `_make_cache_key()` (SHA-256 해시 키 생성)
- `_cache_path()` (해시 기반 경로)
- `_touch_cache()` (LRU mtime 갱신)
- `_save_cache()` (해시 기반 저장)
- `_make_thumbnail_base64()`, `_make_full_base64()` (base64 변환)
- 캐시 히트 판별 로직

#### 추가 항목
- `_save_node_image(file_id, node_id, image, full_size)` — node_id 기반 파일 저장 + URL 반환

#### 유지 항목 (정책 변경)
- `CACHE_TTL_SECONDS` → 1시간 (file_id 디렉토리 단위)
- `CACHE_MAX_BYTES` → 1GB (전체 cache 폴더)
- `cleanup_cache()` → file_id 디렉토리 단위 정리로 변경
  - TTL: mtime 기준 1시간 초과한 file_id 디렉토리 통째로 삭제
  - 용량: 전체 cache 폴더가 1GB 초과 시, 가장 오래된 file_id 디렉토리부터 삭제

### 클라이언트 변경

#### 이미지 표시
```ts
// 기존: 동일 URL이면 브라우저가 캐시된 이전 이미지를 표시할 수 있음
// 수정: 서버가 ?t= 타임스탬프를 포함하여 반환하므로 추가 처리 불필요
data.imageUrl = API_HOST + nr.imageUrl;
```

#### 스키마 변경
- `TreeNodeResultResponse`에서 `cached` 필드 제거
- `TreeBatchResult`에서 `cached` 필드 제거

### 기존 대비 비교

| 항목 | 기존 (해시 기반) | 수정 (node_id 기반) |
|------|:---:|:---:|
| 파일 수 | 파라미터 조합 수 | 노드 수 (고정) |
| 파라미터 변경 시 | 새 파일 생성 | 기존 파일 덮어쓰기 |
| 동일 파라미터 재요청 | 캐시 히트 (연산 스킵) | 재연산 |
| 정리 복잡도 | TTL + LRU 이중 정책 | file_id 디렉토리 단위 삭제 |
| 파일 폭증 위험 | 있음 | 없음 |

### 트레이드오프
- 동일 파라미터로 재요청해도 매번 연산 수행 (캐시 히트 없음)
- 썸네일 해상도가 작으므로 연산 비용 자체가 낮아 허용 가능
- 전체 해상도(zoom) 요청은 별도 경로이므로 영향 없음
