import numpy as np

# ── 1. 배열 생성 ──────────────────────────────────────────
a = np.array([1, 2, 3, 4, 5])          # 1차원
b = np.array([[1, 2, 3], [4, 5, 6]])   # 2차원 (2행 3열)

print("1차원:", a)
print("2차원:\n", b)
print("shape:", b.shape)   # (2, 3)
print("dtype:", a.dtype)   # int64
print()

# ── 2. 초기화 배열 ────────────────────────────────────────
print(np.zeros((2, 3)))     # 0으로 채운 2x3
print(np.ones((2, 3)))      # 1으로 채운 2x3
print(np.eye(3))            # 3x3 단위행렬
print(np.arange(0, 10, 2)) # [0 2 4 6 8]
print(np.linspace(0, 1, 5)) # [0. 0.25 0.5 0.75 1.]
print()

# ── 3. 인덱싱 & 슬라이싱 ──────────────────────────────────
c = np.array([[10, 20, 30],
              [40, 50, 60],
              [70, 80, 90]])

print("1,0", c[1,0])
print("1열", c[0, :])
print("2행", c[:, 1])

print("(1,2):", c[1, 2])        # 60
print("1행:", c[1, :])          # [40 50 60]
print("2열:", c[:, 2])          # [30 60 90]
print("부분:\n", c[0:2, 1:3])   # [[20 30][50 60]]
print()

# ── 4. 브로드캐스팅 연산 ──────────────────────────────────
x = np.array([1, 2, 3])
print("x * 2:", x * 2)          # [2 4 6]  — 스칼라 브로드캐스팅
print("x + x:", x + x)          # [2 4 6]  — 요소별 덧셈
print("x ** 2:", x ** 2)        # [1 4 9]

row = np.array([[1], [2], [3]]) # (3,1)
col = np.array([10, 20, 30])    # (3,)  → (1,3) 으로 확장
print("브로드캐스팅 덧셈:\n", row + col)  # (3,3) 결과
print()

# ── 5. 집계 함수 ──────────────────────────────────────────
m = np.array([[1, 2, 3],
              [4, 5, 6]])

print("전체 합:", m.sum())           # 21
print("열 합:", m.sum(axis=0))       # [5 7 9]
print("행 합:", m.sum(axis=1))       # [6 15]
print("평균:", m.mean())             # 3.5
print("최대:", m.max())              # 6
print("최대 인덱스:", m.argmax())    # 5
print()

# ── 6. 형태 변환 ──────────────────────────────────────────
flat = np.arange(1, 7)              # [1 2 3 4 5 6]
reshaped = flat.reshape(2, 3)       # (2,3)
print("reshape:\n", reshaped)
print("flatten:", reshaped.flatten())
print("transpose:\n", reshaped.T)   # (3,2)
print()

# ── 7. 불리언 인덱싱 (필터) ───────────────────────────────
data = np.array([10, 25, 3, 47, 8, 60])
mask = data > 20
print("mask:", mask)                        # [F T F T F T]
print("필터 결과:", data[mask])             # [25 47 60]
print("한 줄로:", data[data > 20])          # 동일
print()

# ── 8. OpenCV 연동 패턴 (이미지 처리에서 자주 사용) ────────
# OpenCV 이미지는 np.ndarray (H, W, C) 형태
img = np.zeros((4, 4, 3), dtype=np.uint8)  # 4x4 검정 이미지 (BGR)
img[1:3, 1:3] = [255, 0, 0]                # 중앙 2x2 픽셀을 파란색으로
print("이미지 shape:", img.shape)           # (4, 4, 3)
print("중앙 픽셀:", img[1, 1])             # [255 0 0]

gray = np.mean(img, axis=2).astype(np.uint8)  # 채널 평균 → 그레이스케일
print("그레이 shape:", gray.shape)             # (4, 4)
