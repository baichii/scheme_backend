from datetime import date
from pydantic import BaseModel


def main(user_id: str):
    return user_id


class User(BaseModel):
    id: int
    name: str
    joined: date


my_user = User(id=3, name="jzj", joined=date(2021, 12, 31))

print(my_user)
print(my_user.id)
print(my_user.name)
print(my_user.joined)
