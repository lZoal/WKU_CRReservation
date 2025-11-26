from pydantic import BaseModel

class Room(BaseModel):
    id: int
    name: str
    building_id: int
    floor: int
    capacity: int