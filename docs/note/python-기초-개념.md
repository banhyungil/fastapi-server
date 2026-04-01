# Python 기초 개념

## 제너레이터 함수

함수 실행을 **일시 중단하고 재개**할 수 있는 함수. `yield` 키워드가 포함된 함수는 제너레이터 함수가 된다.

```python
def gen():
    print("1단계")
    yield 10
    print("2단계")
    yield 20
    print("3단계")

g = gen()
next(g)  # "1단계" 출력, 10 반환, yield에서 멈춤
next(g)  # "2단계" 출력, 20 반환, yield에서 멈춤
next(g)  # "3단계" 출력, StopIteration 발생
```

### 일반 함수 vs 제너레이터 함수

|           | 일반 함수      | 제너레이터 함수        |
| --------- | -------------- | ---------------------- |
| 호출 시   | 즉시 실행      | 제너레이터 객체만 반환 |
| 값 반환   | `return` 한 번 | `yield` 여러 번 가능   |
| 실행 상태 | 유지 안 됨     | `yield` 지점에서 유지  |

### pytest fixture에서의 활용

pytest는 fixture에서 `yield`를 감지해 `yield` 전후를 setup/teardown으로 처리한다.

```python
@pytest.fixture(scope="session", autouse=True)
def db_pool():
    pool.open()   # setup: 테스트 전 실행
    yield
    pool.close()  # teardown: 테스트 후 실행
```

## 클래스

### 기본 구조

```python
class Dog:
    species = "개"  # 클래스 변수 (모든 인스턴스 공유)

    def __init__(self, name: str):
        self.name = name  # 인스턴스 변수

    def bark(self) -> str:
        return f"{self.name} 멍멍!"
```

- `new` 키워드 없이 `Dog("멍이")`로 인스턴스 생성
- `__init__`은 초기화 메서드 (생성은 `__new__`가 담당)
- `self`를 항상 첫 번째 인자로 명시

### 상속

```python
class Puppy(Dog):
    def __init__(self, name: str, age: int):
        super().__init__(name)  # 부모 __init__ 호출
        self.age = age
```

- 다중 상속 가능: `class A(B, C):`

### 접근 제어 (관례)

```python
self.name       # public
self._name      # protected (관례, 접근 가능)
self.__name     # private (name mangling으로 외부 접근 어려움)
```

Java처럼 강제는 아니고 **관례**로 동작한다.

### 주요 매직 메서드

| 메서드     | 용도                                  |
| ---------- | ------------------------------------- |
| `__init__` | 초기화                                |
| `__str__`  | `print()` 시 출력 (Java의 `toString`) |
| `__repr__` | 디버깅용 문자열 표현                  |
| `__eq__`   | `==` 비교                             |
| `__len__`  | `len()` 호출 시                       |

### 클래스 변수 vs 인스턴스 변수

```python
class Dog:
    count = 0           # 클래스 변수 (Java의 static)

    def __init__(self, name):
        self.name = name  # 인스턴스 변수
        Dog.count += 1
```

### 데코레이터 메서드

```python
class MyClass:
    def method(self):          # 인스턴스 메서드

    @classmethod
    def from_string(cls, s):   # 클래스 메서드 (팩토리 패턴)
        return cls(s)

    @staticmethod
    def validate(s):           # 정적 메서드 (self/cls 없음)
        return len(s) > 0
```

### Java와 주요 차이점

- 인터페이스 없음 → 덕 타이핑 / Protocol (타입힌트)
- 다중 상속 가능
- `self`를 항상 명시

## 문법

### with

```python
# file을 open하고 close하는 방식
# try ~ catch로 구현
try:
    f = open(...)
    ...
finally:
    f.close()

# 실제로는 file 인스턴스 내부는 try catch 구현이 되어 있음
#
with open("log.txt") as f:
    print(f.readline())


# 실제 with 절 동작 방식
## __enther__, __exit__ 함수를 설정하면  된다.

obj = something
value = obj.__enter__()
try:
    # with 블록
finally:
    obj.__exit__()

class MyContext:
    def __enter__(self):
        print("enter")
        return "value"

    def __exit__(self, exc_type, exc, tb):
        print("exit")
```
