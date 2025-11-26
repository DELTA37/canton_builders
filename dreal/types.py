from pydantic import BaseModel


class RealEstateMeta(BaseModel):
    address: str
    area_m2: float
    cadastral_number: str
    building_year: int
    owner_name: str
