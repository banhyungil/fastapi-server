# 트리구성 필요성

- 알고리즘 순서대로 진행시 특정 스텝에서 여러 알고리즘을 적용하여 비교할 필요성이 생긴다
- 이때 리스트로만 구성가능하면 동일한 스텝에 대해서 중복이 많이 발생하게 된다.
- 그러므로 알고리즘 노드는 트리형태로 구성되어야한다.

# 구현 완료

- [x] t_process_step, t_preset_step ddl 수정 (parent_id 컬럼 추가)
- [x] process, preset 관련 api 전면 수정
  - schemas: parent_id 필드 추가 (preset_step은 step_order/is_enabled 제거)
  - repos: parent_id INSERT/SELECT 반영
  - endpoints: 스키마 변경 자동 반영 (model_dump/model_validate)

# 트리 구조

```
노드A (parent_id: null) → 루트
├── 노드B (parent_id: A)
│   ├── 노드D (parent_id: B)
│   └── 노드E (parent_id: B)
└── 노드C (parent_id: A)
    └── 노드F (parent_id: C)
```

- parent_id가 NULL이면 루트 노드 (시작점)
- 같은 parent를 가진 노드들은 분기 (비교 연산)
- t_preset_step: 순수 트리 (step_order 없음, 순서는 트리 구조로 결정)
- t_process_step: 트리 + step_order (실행 순서 유지)
