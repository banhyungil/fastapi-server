# API 경로 정리 (백엔드 + 프론트)

## 백엔드 — 완료

### 엔드포인트 파일 구조
```
app/api/endpoints/
├── file.py        — 파일 관리 + 이미지 처리 (/files)
├── filters.py     — 필터 메타데이터 (/filters)
├── preview.py     — 미리보기, DZI, 다운로드 (/files)
├── preset.py      — 프리셋 (/presets)
├── process.py     — 프로세스 (/processes)
└── custom_filter.py — 커스텀 필터 (/custom-filters)
```

### file.py (`/files`)
| 경로 | Method | 설명 |
|---|---|---|
| `/files` | GET | 이미지 파일 목록 |
| `/files/{id}` | DELETE | 파일 삭제 |
| `/files/{id}` | PATCH | 파일명 수정 |
| `/files/upload` | POST | 파일 업로드 |
| `/files/save` | POST | 처리 이미지 저장 |
| `/files/thumbnail/{id}` | GET | 썸네일 조회 |
| `/files/process` | POST | 단일 필터 처리 |
| `/files/process/batch-tree` | POST | 트리 배치 처리 |

### preview.py (`/files`)
| 경로 | Method | 설명 |
|---|---|---|
| `/files/dzi/{fileId}` | POST | DZI 생성 |
| `/files/download/{fileId}` | POST | 노드 이미지 다운로드 |
| `/files/preview/crop` | POST | crop 생성 |
| `/files/preview/apply` | POST | 필터 적용 |
| `/files/preview/apply-all` | POST | 중간 결과 전체 |
| `/files/preview/crop/{fileId}/{cropId}` | DELETE | crop 캐시 삭제 |

### filters.py (`/filters`)
| 경로 | Method | 설명 |
|---|---|---|
| `/filters/params` | GET | 전체 필터 파라미터 스키마 |
| `/filters/params/{prcType}` | GET | 개별 필터 파라미터 스키마 |

## 프론트 — 진행 예정

### API 파일 분리 + 경로 변경
| 파일 | 역할 | 경로 변경 |
|---|---|---|
| `fileApi.ts` | 파일 관리 + 처리 | `/image-processing/*` → `/files/*` |
| `previewApi.ts` | 미리보기, DZI, 다운로드 | `/image-processing/*` → `/files/*` |
| `filterApi.ts` (선택) | 필터 스키마 | `/image-processing/params` → `/filters/params` |

### 경로 변경 대상
| 현재 (imgPrcApi.ts) | 변경 |
|---|---|
| GET `/image-processing` | GET `/files` |
| DELETE `/image-processing/{id}` | DELETE `/files/{id}` |
| PATCH `/image-processing/{id}` | PATCH `/files/{id}` |
| POST `/image-processing/upload` | POST `/files/upload` |
| POST `/image-processing/save` | POST `/files/save` |
| POST `/image-processing` (단일처리) | POST `/files/process` |
| POST `/image-processing/batch-tree` | POST `/files/process/batch-tree` |
| POST `/image-processing/dzi/{id}` | POST `/files/dzi/{id}` |
| POST `/image-processing/download/{id}` | POST `/files/download/{id}` |
| POST `/image-processing/preview/*` | POST `/files/preview/*` |
| GET `/image-processing/params` | GET `/filters/params` |
