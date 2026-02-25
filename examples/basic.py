# comprehention
## map, filter 구현
list1 = [1,2,3,4,5]
list_map = (n*2 for n in list1)
list_filter = (n for n in list1 if n % 2 == 0)

print(f"list_map: {list_map}")
print(f"list_filter: {list_filter}")

# 가변인자 구현
def my_sum(*nums):
    return sum(n for n in nums)

if __name__ == "__main__":
    print(my_sum(1,2,3))
    print(my_sum(4,5,6))