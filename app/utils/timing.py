import inspect
import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    # 비동기 함수(coroutine) 판별 함수
    ## co-routine = “협력(co)하는 루틴(routine)”.
    ## 일반 함수(routine)는 호출되면 끝까지 실행되고 제어권 반환
    ## co-routinge은 실행 중간에 스스로 제어권을 양보(yield/await),
    ## 나중에 그 지점부터 다시 이어서 실행.
    ## 즉, 여러 루틴이 **선점(preemptive)**이 아닌 
    ## **협력적(cooperative)**으로 번갈아 실행되는 모델
    if inspect.iscoroutinefunction(func):

        # 1. @wraps(func)
        ## 아래 함수(async_wrapper)를 func로 Wrapping,
        ## 이름/문서문자열/시그니처 같은 메타데이터는 최대한 원본처럼 유지.
        ## 그래서 로그, 디버깅, 문서화에서 래퍼 흔적이 덜 남아요.
        # 2. *args:
        ## 위치 인자를 튜플로 받음
        # 3. **kwargs:
        ## 키워드 인자를 딕셔너리로 받음
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                # cast 함수: 타입 캐스팅 용도
                #  coroutine 함수이므로 Awaitable 반환 타입으로 지정
                return await cast(Callable[P, Awaitable[R]], func)(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info("[timing] %s: %.2f ms", func.__name__, elapsed_ms)

        return cast(Callable[P, R], async_wrapper)

    @wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("[timing] %s: %.2f ms", func.__name__, elapsed_ms)

    return sync_wrapper