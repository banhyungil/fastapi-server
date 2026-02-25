import time
from functools import wraps

# 호출 방식
# 1. 위치 인자 호출: f(1, 2) → args=(1, 2), kwargs={}
# 2. 키워드 인자 호출: f(a=1, b=2) → args=(), kwargs={"a":1, "b":2}
# 3. 혼합 호출: f(1, b=2) → args=(1,), kwargs={"b":2}

# 데코레이터 함수는 wrapper 함수를 반환한다.
def log_time(func):
    # 래퍼가 호출될 때 실제 인자들은 먼저 args(튜플), kwargs(딕셔너리)로 모입니다.
    # 그 다음 func(*args, **kwargs)에서 */**가 그 인자들을 다시 호출 인자로 언패킹.
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            print(f"[timing] {func.__name__}: {elapsed_ms:.2f} ms")

    return wrapper

def my_decorator(func):
    @wraps(func)
    def abc_wrapper(*args, **kargs):
        print('before call function')
        func(*args, **kargs)
        print("after call function")

    return abc_wrapper


@log_time
def greet(name: str, age: int):
    return f"hello {name} | age:{age}"

@log_time
def greet2(num1, num2):
    return f"hello {num1}, {num2}"

@my_decorator
def greet3(num1, num2):
    print(f"hello {num1}, {num2}")



# 해당 모듈 직접 실행할 때
if __name__ == "__main__":
    result = greet("ban", 20)
    print(result)

    result = greet2(1, 3)
    print(result)

    greet3(num1=4, num2=6)