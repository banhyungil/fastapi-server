"""캐시 디렉토리 관리."""

import shutil
import time
from pathlib import Path

CACHE_DIR = Path("uploads/cache")
CACHE_TTL_SECONDS = 60 * 60            # 1시간 (file_id 디렉토리 단위)
CACHE_MAX_BYTES = 1024 * 1024 * 1024   # 1GB (전체 cache 폴더)


def cleanup_cache() -> None:
    """file_id 디렉토리 단위 TTL 삭제 + 전체 폴더 크기 제한."""
    if not CACHE_DIR.exists():
        return

    now = time.time()
    dirs = [d for d in CACHE_DIR.iterdir() if d.is_dir()]

    # 1) TTL 기반 삭제
    remaining: list[Path] = []
    for d in dirs:
        if now - d.stat().st_mtime > CACHE_TTL_SECONDS:
            shutil.rmtree(d, ignore_errors=True)
        else:
            remaining.append(d)

    # 2) 전체 폴더 크기 제한 (LRU)
    def _dir_size(d: Path) -> int:
        return sum(f.stat().st_size for f in d.rglob("*") if f.is_file())

    remaining.sort(key=lambda d: d.stat().st_mtime)
    total = sum(_dir_size(d) for d in remaining)
    while total > CACHE_MAX_BYTES and remaining:
        old = remaining.pop(0)
        total -= _dir_size(old)
        shutil.rmtree(old, ignore_errors=True)
