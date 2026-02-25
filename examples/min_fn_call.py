def min(str: str, num: int):
    print(f"{str}, {num}")

if __name__ == "__main__":
    min("위치 인자 호출", 1)
    min(str="키워드 인자 호출", num=2)