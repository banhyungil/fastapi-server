
import numpy as np

dict1 = {"name": "ban", "age": 34}

for key in dict1:
    print(key)
print('-----------')

for key in dict1.keys():
    print(key)
print('-----------')

for value in dict1.values():
    print(value)
print('-----------')

for key, value in dict1.items():
    print(key, value)


# dictionary
print('-----------')
obj1 = {"a": 1, "b": 'b'}
obj2 = {"c": False}

## dictionary unpacking & merge
obj3 = {**obj1, **obj2}

for key, val in obj3.items():
    print(key, val)
print('-----------')


for key in dict1:
    print(key)

for key, val in dict1.items():
    print(key, val)

for item in [1,2,3]:
    print(item)
print('-----------')

arr = [1,2,3]
# comprehention map
arr2 = (num * 2 for num in arr)
# comprehention filter
arr3 = (num for num in arr if num % 2 == 0)
for item in arr3:
    print(item)

print('-----------')
print(type([1,2,3]))
print(type(np.array([1,2,3])))
print(type(1))
print(type(True))
print(type(None))
print(type("1"))

print('-----------')
def testTuple():
    return [1, 2]

a, b =testTuple()
print(a, b)