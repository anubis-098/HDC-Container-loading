from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

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
    truck_type: Literal['4 ล้อ','6 ล้อ','10 ล้อ','Dock Tailer','18 ล้อ','รถเทรลเลอร์']
    shipment_number: str | None = Field(default=None, min_length=1, max_length=80)
    store_code: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode='after')
    def legacy_pair(self):
        if (self.shipment_number is None) != (self.store_code is None):
            raise ValueError('Legacy Shipment and Store must be provided together')
        return self

class ShipmentInput(Input):
    id: UUID
    number: str = Field(min_length=1, max_length=80)
    store_code: str = Field(min_length=1, max_length=40)

class PalletInput(Input):
    id: UUID

class TripPalletInput(Input):
    id: UUID
    store_code: str = Field(min_length=1, max_length=40)
    orders: list[str] = Field(min_length=1, max_length=100)

    @field_validator('orders')
    @classmethod
    def clean_orders(cls, values):
        result = [value.strip() for value in values]
        if any(not value or len(value)>80 or any(ord(c)<32 for c in value) for value in result):
            raise ValueError('Order numbers must contain 1–80 characters')
        if len(set(result)) != len(result):
            raise ValueError('Duplicate Order in the same Pallet')
        return result

class StoreInput(Input):
    code: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(min_length=1, max_length=160)
    active: bool = True

