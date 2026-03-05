from pydantic import BaseModel

# 1. 타입 정의 해보시오
class Item(BaseModel):
    id: int
    name: str
    price: float
    is_available: bool

external_data = {
    "id": "100",
    "name": "모니터",
    "price": "4500.50",
    "is_available": "true",
    "아무거나": "ㅁㅁㅁ"
}

item = Item.model_validate(external_data)

print()