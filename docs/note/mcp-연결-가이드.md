# MCP (Model Context Protocol) 연결 가이드

## MCP란?

AI 도구(Claude Code 등)가 외부 서비스(Figma, GitHub, Slack 등)와 통신할 수 있게 해주는 표준 프로토콜.
MCP 서버를 설정하면 AI가 해당 서비스의 데이터를 직접 조회/활용할 수 있다.

```
Claude Code (클라이언트) ←→ MCP 서버 ←→ 외부 서비스 (Gmail, Figma, DB 등)
```

## 핵심 개념

### MCP 서버가 제공하는 3가지

| 종류 | 설명 | 예시 |
|------|------|------|
| **Tools** | Claude가 호출할 수 있는 함수 | `gmail_search_messages`, `get_figma_data` |
| **Resources** | 읽을 수 있는 데이터/콘텐츠 | 파일, API 응답 등 |
| **Prompts** | 재사용 가능한 프롬프트 템플릿 | `/code-review` 같은 명령 |

### 전송 방식 (Transport)

| 방식 | 동작 | 용도 |
|------|------|------|
| **stdio** | 로컬 프로세스로 실행, stdin/stdout 통신 | Figma, 로컬 도구 |
| **HTTP/SSE** | 원격 서버에 HTTP 연결 | 클라우드 서비스, 공유 인프라 |

### 서버 생명주기

- **세션 시작** → stdio 서버는 자동으로 프로세스 실행
- **세션 중** → 연결 유지, 크래시 시 재연결 시도
- **세션 종료** → 자동 종료

## Claude Code에서 MCP 설정

- Claude Desktop에서 커넥터 연결을 완료하면 VSCode Claude 확장에서도 사용가능하다.

### 유용한 명령어

```
/mcp              # 연결된 서버 목록 및 상태 확인
/mcp <서버이름>    # 특정 서버 상세 정보
```

## 커스텀 MCP 서버 만들기

자신의 프로그램을 MCP 서버로 만들면 Claude가 해당 프로그램을 직접 제어할 수 있다.

### Python SDK 설치

```bash
pip install mcp
```

### 예시: FastAPI 서버용 MCP 서버

```python
# mcp_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-fastapi-tools")

@mcp.tool()
def get_users():
    """사용자 목록 조회"""
    import httpx
    res = httpx.get("http://localhost:8000/api/users")
    return res.json()

@mcp.tool()
def create_user(name: str, email: str):
    """사용자 생성"""
    import httpx
    res = httpx.post("http://localhost:8000/api/users", json={"name": name, "email": email})
    return res.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### `.mcp.json`에 등록

```json
{
  "mcpServers": {
    "my-api": {
      "command": "python",
      "args": ["mcp_server.py"]
    }
  }
}
```

### 활용 예

- DB 조회/수정
- API 호출
- 배포 트리거
- 로그 확인

> `@mcp.tool()` 데코레이터로 함수를 정의하면 Claude가 자동으로 도구로 인식한다.
> 함수의 docstring이 도구 설명으로 사용되므로 명확하게 작성할 것.

## 참고

- 설정 변경 후 Claude Code **재시작 필요**
- VS Code의 MCP Discovery 설정(Chat > Mcp > Discovery)은 Copilot Chat용이며, Claude Code와는 별개
