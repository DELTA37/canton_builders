import os
from dazl import connect
from .settings import LEDGER_URL
import asyncio, json
from dazl import connect
from .types import RealEstateMeta


class RealEstateClient:
    def __init__(self,
                 registrar="Registrar"):
        self.ledger_url = LEDGER_URL
        self.registrar = registrar
        self.conn = None

    async def __aenter__(self):
        self.conn = await connect(url=self.ledger_url,
                                  act_as=[self.registrar])
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()

    # Создание объекта недвижимости
    async def create_property(self, property_id: str, owner: str, meta: RealEstateMeta):
        # Проверка на уникальность
        existing = await self.conn.find("RealEstate.RealEstate")
        if any(c.payload["propertyId"] == property_id for c in existing):
            raise ValueError(f"Property {property_id} already exists")

        meta_json = meta.json()
        cid = await self.conn.create(
            "RealEstate.RealEstate",
            {
                "registrar": self.registrar,
                "owner": owner,
                "propertyId": property_id,
                "metaJson": meta_json,
                "history": []
            }
        )
        return cid

    # Передача недвижимости новому владельцу
    async def transfer_property(self, contract_id, current_owner: str, new_owner: str):
        result = await self.conn.exercise(
            contract_id,
            "Transfer",
            {"newOwner": new_owner},
            act_as=[current_owner]
        )
        return result

    # Получение всех активных объектов недвижимости
    async def list_properties(self):
        active = await self.conn.find("RealEstate.RealEstate")
        return [c.payload for c in active]
