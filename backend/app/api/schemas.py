from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

class WorkerInput(Input):
    name: str = Field(min_length=2, max_length=160)

class LoginInput(Input):
    model_config = ConfigDict(str_strip_whitespace=False)
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)

class TripInput(Input):
    id: UUID
    truck_id: str = Field(min_length=1, max_length=40)
    truck_province: str | None = Field(default=None, min_length=2, max_length=60)
    truck_type: Literal['4 ล้อ','6 ล้อ','8 ล้อ','12 ล้อ','เทรลเลอร์']
    shipment_number: str = Field(min_length=1, max_length=80)
    store_code: str = Field(min_length=1, max_length=40)

class ShipmentInput(Input):
    id: UUID
    number: str = Field(min_length=1, max_length=80)
    store_code: str = Field(min_length=1, max_length=40)

class PalletInput(Input):
    id: UUID

class StoreInput(Input):
    code: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=160)
    active: bool = True

