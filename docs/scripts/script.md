# pytest

```bash
# 전체 테스트 실행
pytest
# 첫 실패 시 중단
pytest -x
# 결과 요약 출력
## --tb: traceback
pytest --tb=short

# 특정 파일
py test tests/test_file.py

# 특정 함수
## -s: Shortcut for --capture=no, print/log 캡처 안 함수
## --log-cli-level=DEBUG: 로그 레벨 설정
pytest tests/test_custom_filter.py::test_execute_find_by_id -s --log-cli-level=DEBUG
```

# bat

```bat
where libvips-42.dll 2>&1 || echo "NOT FOUND in PATH"
```

# bash

```bash
# 전체 환경 변수 확인
env
# 특정 환경변수 확인
echo $HOME
# 환경변수 key 값 목록 출력
## cut 옵션
## -d(delimiter): 구분자 지정
## -f(field): 분리된 필드 중 몇번째 필드를 출력할지
printenv | cut -d '=' -f 1

# 파일 만들기
touch test.txt

```

# npm

```bash
# 최신 버전 있는지 확인
npm outdated @vue-flow/core
```

# claude

```bash
# mcp 서버 목록
/mcp
# model 변경
/model
```

# 기타

```bash
npx tsc --noEmit
```
