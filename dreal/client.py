import os
from typing import Optional

from .settings import LEDGER_URL
import dazl
from .types import RealEstateMeta


class RealEstateClient:
    def __init__(self,
                 registrar="Registrar"):
        self.ledger_url = LEDGER_URL
        self.registrar = dazl.Party(registrar)
        self.conn: Optional[dazl.Connection] = None

    async def __aenter__(self):
        self.conn = await dazl.connect(url=self.ledger_url,
                                       act_as=[self.registrar]).__aenter__()
        # print(await self.conn.get_version())
        parties = await self.conn.list_known_parties()
        print(parties)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.__aexit__(exc_type, exc_val, exc_tb)

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
        async with self.conn.query_many('*') as stream:
            async for event in stream.creates():
                print(event.contract_id, event.payload)
