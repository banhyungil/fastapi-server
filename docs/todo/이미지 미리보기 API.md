# 이미지 미리보기 (Preview) API

## 개요
확대 팝업 미니 에디터에서 사용할 crop 기반 미리보기 API.
현재 뷰포트 영역만 잘라서 필터를 적용하고, 노드 이미지 crop + 처리 crop을 반환한다.
crop 이미지는 서버에 캐시하여 필터 변경 시 재사용한다.

## 엔드포인트

### POST /api/image-processing/preview/crop
뷰포트 영역의 crop 이미지를 생성하고 캐시한다.
```
Request (multipart/form-data):
  fileId: string              — 원본 파일 ID
  nodeSteps: string (JSON)    — 해당 노드까지의 기존 steps (트리 체인)
  nodeId: string              — 대상 노드 ID
  viewport: string (JSON)     — crop 영역 { x, y, w, h } (px)
  padding: number (optional)  — 경계 아티팩트 방지 여유 영역 (px, 기본 50)

Response (JSON):
  {
    cropId: string,          — 캐시된 crop 식별자 (이후 요청에서 사용)
    nodeImageUrl: string,    — 노드 이미지 crop URL
    width: number,           — crop 이미지 가로 (px)
    height: number           — crop 이미지 세로 (px)
  }
```

### POST /api/image-processing/preview/apply
캐시된 crop 이미지에 tempSteps를 적용한 결과를 반환한다.
```
Request (multipart/form-data):
  cropId: string              — crop 캐시 ID
  tempSteps: string (JSON)    — 임시 필터 steps (선형 체인, 순서대로 적용)
  padding: number (optional)  — crop 시 사용한 padding 값

Response:
  처리된 crop 이미지 (blob, image/png)
```

## 캐시 전략
```
캐시 키:    fileId + nodeSteps hash + viewport 좌표
캐시 위치:  uploads/cache/{fileId}/preview_{cropId}.png
캐시 유효:  동일 뷰포트에서 필터만 변경 시 → 캐시 유효, apply만 재호출
캐시 무효:  팬/줌 변경 시 → 새 crop 요청 (crop API 재호출)
캐시 정리:  팝업 닫힘 시 프론트에서 delete 요청, 또는 TTL 기반 자동 정리
```

### 프론트 호출 흐름
```
1. 팝업 열림 + 필터 추가
   → POST /preview/crop (viewport 전달) → cropId 획득

2. 필터 파라미터 변경 (debounce)
   → POST /preview/apply (cropId + tempSteps) → 처리 이미지 반환
   → crop 재생성 불필요

3. 팬/줌 변경 (debounce)
   → POST /preview/crop (새 viewport) → 새 cropId 획득
   → POST /preview/apply (새 cropId + tempSteps) → 처리 이미지 반환

4. 필터 추가/삭제
   → POST /preview/apply (cropId + 변경된 tempSteps) → 처리 이미지 반환

5. 팝업 닫힘
   → DELETE /preview/crop/{cropId} (캐시 정리)
```

## 처리 흐름 (서버)
```
[/preview/crop]
1. fileId → 원본 파일 경로 조회
2. 원본 이미지 로드 (cv2.imread)
3. nodeSteps 적용 → 노드 이미지 생성 (해당 노드까지의 처리 결과)
4. viewport + padding 영역으로 crop (범위 초과 시 clamp)
5. crop 이미지를 캐시 파일로 저장
6. padding 제거한 노드 이미지 crop도 저장 (비교 표시용)
7. cropId + nodeImageUrl 반환

[/preview/apply]
1. cropId → 캐시된 crop 이미지 로드
2. tempSteps 순차 적용
   - 각 step: { prcType, parameters }
3. padding 영역 제거
4. 처리된 crop 이미지 blob 반환
```

## 서비스 함수
```python
def create_preview_crop(
    file_path: str,
    node_steps: list[dict[str, Any]],
    node_id: str,
    viewport: dict,    # { x, y, w, h }
    padding: int = 50,
) -> PreviewCropResult:
    """노드 이미지를 생성하고 viewport 영역을 crop하여 캐시한다."""

    # 노드 이미지 생성 (기존 _process_chain_to_node 재사용)
    if node_steps:
        node_image = _process_chain_to_node(file_path, node_steps, node_id)
    else:
        node_image = cv2.imread(file_path, cv2.IMREAD_COLOR)

    # viewport + padding으로 crop (clamp)
    h_img, w_img = node_image.shape[:2]
    x1 = max(0, viewport['x'] - padding)
    y1 = max(0, viewport['y'] - padding)
    x2 = min(w_img, viewport['x'] + viewport['w'] + padding)
    y2 = min(h_img, viewport['y'] + viewport['h'] + padding)
    cropped = node_image[y1:y2, x1:x2]

    # 캐시 저장
    crop_id = uuid4().hex
    cache_path = CACHE_DIR / file_id / f"preview_{crop_id}.png"
    cv2.imwrite(str(cache_path), cropped)

    # padding 제거한 노드 이미지 crop (비교 표시용)
    px, py = viewport['x'] - x1, viewport['y'] - y1
    node_crop = cropped[py:py+viewport['h'], px:px+viewport['w']]
    node_crop_path = CACHE_DIR / file_id / f"preview_{crop_id}_node.png"
    cv2.imwrite(str(node_crop_path), node_crop)

    return PreviewCropResult(crop_id=crop_id, node_image_url=f"/{node_crop_path}", ...)


def apply_preview_filter(
    crop_id: str,
    file_id: str,
    temp_steps: list[dict[str, Any]],
    viewport: dict,
    padding: int = 50,
) -> bytes:
    """캐시된 crop 이미지에 tempSteps를 적용하여 결과를 반환한다."""

    cache_path = CACHE_DIR / file_id / f"preview_{crop_id}.png"
    cropped = cv2.imread(str(cache_path), cv2.IMREAD_COLOR)

    # tempSteps 순차 적용
    result = cropped.copy()
    for step in temp_steps:
        op = OPERATIONS[step['prcType']]
        params = PARAM_MODELS[step['prcType']].model_validate(step.get('parameters', {}))
        result = op(result, params)

    # padding 제거
    px, py = padding, padding  # clamp 고려 필요
    result = result[py:py+viewport['h'], px:px+viewport['w']]

    _, encoded = cv2.imencode('.png', result)
    return encoded.tobytes()
```

## viewport 좌표 형식
프론트(OsdViewer)에서 전달하는 viewport 좌표 변환이 필요함.
- OpenSeadragon viewport 좌표는 0~1 비율 기반
- 서버에서는 px 기반으로 처리
- 변환: `px_x = viewport_x * image_width`

```typescript
// 프론트에서 viewport 좌표 추출
const bounds = viewer.viewport.getBounds();
const imageSize = viewer.world.getItemAt(0).getContentSize();
const viewport = {
  x: Math.round(bounds.x * imageSize.x),
  y: Math.round(bounds.y * imageSize.x),  // OSD는 width 기준 비율
  w: Math.round(bounds.width * imageSize.x),
  h: Math.round(bounds.height * imageSize.x),
};
```

## 고려사항
- **padding**: blur, median 등 커널 기반 필터는 경계에서 아티팩트 발생 → padding 포함 후 결과에서 제거
- **최대 crop 크기**: 줌 아웃 시 crop이 너무 크면 처리 부하 → 최대 크기 제한 (예: 2000x2000)
- **응답 형식**: apply는 처리 이미지 blob 반환 (단일 이미지), crop은 JSON + URL
- **캐시 정리**: TTL 기반 자동 정리 또는 프론트에서 팝업 닫을 때 DELETE 요청
- **기존 API와 분리**: batch-tree API는 트리 구조 + 썸네일, preview API는 선형 체인 + crop + 캐시
- **노드 이미지 생성**: 기존 `_process_chain_to_node` 함수 재사용 가능
