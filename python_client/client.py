import asyncio
import datetime
import decimal
import os
from typing import Any, Dict, List, Optional

import dazl
from dazl import Party
from dazl.ledger.api_types import CreateEvent


DEFAULT_LEDGER_HOST = os.getenv("LEDGER_HOST", "localhost")
DEFAULT_LEDGER_PORT = int(os.getenv("LEDGER_PORT", "26865"))
DEFAULT_PARTY = os.getenv("LEDGER_PARTY", "")
DEFAULT_APP_NAME = os.getenv("LEDGER_APP_NAME", "real-estate-client")


def to_jsonable(val: Any) -> Any:
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    if isinstance(val, decimal.Decimal):
        return str(val)
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [to_jsonable(v) for v in val]
    if isinstance(val, CreateEvent):
        return {
            "contractId": str(val.contract_id),
            "payload": to_jsonable(val.payload),
        }
    return str(val)


class RealEstateHandler:
    """
    Теперь работает так:

        async with RealEstateHandler(party="Registrar") as h:
            await h.create_property_async(...)

    Один connect на весь контекст.
    """

    def __init__(
        self,
        host: str = DEFAULT_LEDGER_HOST,
        port: int = DEFAULT_LEDGER_PORT,
        party: str = DEFAULT_PARTY,
        app_name: str = DEFAULT_APP_NAME,
    ):
        self.host = host
        self.port = port
        self.party_hint = party or "Observer"
        self.app_name = app_name

        self.client = None
        self.party = None  # resolved party id

    def _url(self) -> str:
        return f"grpc://{self.host}:{self.port}"

    # =============================
    # CONTEXT MANAGER
    # =============================

    async def __aenter__(self):
        # First: connect with hint
        raw_conn = dazl.connect(
            url=self._url(),
            party=Party(self.party_hint),
            application_name=self.app_name,
        )
        resolver = await raw_conn.__aenter__()

        # Resolve actual party
        self.party = await self._resolve_party(resolver, self.party_hint)

        # resolver is no longer needed
        await raw_conn.__aexit__(None, None, None)

        # Second: open real session with resolved party
        conn = dazl.connect(
            url=self._url(),
            party=Party(self.party),
            read_as=[Party(self.party)],
            act_as=[Party(self.party)],
            application_name=self.app_name,
        )
        self.client = await conn.__aenter__()
        self._conn_cm = conn  # to close on exit

        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.client is not None:
            await self._conn_cm.__aexit__(exc_type, exc, tb)
        self.client = None

    # =============================
    # HELPERS
    # =============================

    async def _resolve_party(self, conn, hint: str) -> str:
        if "::" in hint:
            return hint
        try:
            infos = await conn.list_known_parties()
            for info in infos:
                if str(info.party).startswith(f"{hint}-") or info.display_name == hint:
                    return str(info.party)
        except Exception:
            pass
        return hint

    async def _exercise(self, contract_id: str, choice: str, argument: Dict[str, Any], extra_act_as=None):
        act_as = [Party(self.party)]
        if extra_act_as:
            act_as.extend(extra_act_as)
        res = await self.client.exercise(
            "RealEstate:RealEstate",
            contract_id,
            choice,
            argument,
            act_as=act_as,
            read_as=act_as,
        )
        return to_jsonable(res)

    # =============================
    # MAIN METHODS
    # =============================

    async def create_property_async(
        self,
        registrar: str,
        owner: str,
        property_id: str,
        address: str,
        property_type: str,
        area: str,
        meta_json: str,
        price: str,
        currency: str,
        listed: bool = False,
    ):
        registrar_id = await self._resolve_party(self.client, registrar)
        owner_id = await self._resolve_party(self.client, owner)

        event = await self.client.create(
            "RealEstate:RealEstate",
            {
                "registrar": registrar_id,
                "owner": owner_id,
                "propertyId": property_id,
                "address": address,
                "propertyType": property_type,
                "area": area,
                "metaJson": meta_json,
                "status": "Active",
                "history": [],
                "listed": listed,
                "price": price,
                "currency": currency,
            },
            act_as=[Party(registrar_id)],
        )
        return to_jsonable(event)

    async def transfer_property_async(self, contract_id: str, new_owner: str):
        return await self._exercise(contract_id, "Transfer", {"newOwner": new_owner})

    async def update_meta_async(self, contract_id: str, meta_json: str):
        return await self._exercise(contract_id, "UpdateMeta", {"newMetaJson": meta_json})

    async def archive_property_async(self, contract_id: str):
        return await self._exercise(contract_id, "ArchiveProperty", {})

    async def list_properties_async(self):
        result = []
        async for event in self.client.query("RealEstate:RealEstate"):
            if isinstance(event, CreateEvent):
                result.append({
                    "contractId": str(event.contract_id),
                    "payload": to_jsonable(event.payload),
                })
        return result

    async def mint_cash_async(self, issuer: str, owner: str, amount: str, currency: str):
        issuer_id = await self._resolve_party(self.client, issuer)
        owner_id = await self._resolve_party(self.client, owner)
        event = await self.client.create(
            "RealEstate:Cash",
            {
                "issuer": issuer_id,
                "owner": owner_id,
                "currency": currency,
                "amount": amount,
            },
            act_as=[Party(owner_id)],
        )
        return to_jsonable(event)

    async def list_cash_async(self):
        result = []
        async for event in self.client.query("RealEstate:Cash"):
            if isinstance(event, CreateEvent):
                result.append({
                    "contractId": str(event.contract_id),
                    "payload": to_jsonable(event.payload),
                })
        return result

    async def list_for_sale_async(self, contract_id: str, price: str, currency: str):
        return await self._exercise(
            contract_id,
            "ListForSale",
            {"newPrice": price, "newCurrency": currency},
        )

    async def delist_property_async(self, contract_id: str):
        return await self._exercise(contract_id, "Delist", {})

    async def buy_property_async(self, contract_id: str, price: str, currency: str, buyer: str, payment_cid: str, seller: str):
        buyer_id = await self._resolve_party(self.client, buyer)
        seller_id = await self._resolve_party(self.client, seller)
        return await self._exercise(
            contract_id,
            "Buy",
            {
                "offeredPrice": price,
                "offeredCurrency": currency,
                "buyer": buyer_id,
                "paymentCid": payment_cid,
            },
            extra_act_as=[Party(buyer_id), Party(seller_id)],
        )

    async def list_parties_async(self):
        infos = await self.client.list_known_parties()
        return [
            {"id": str(info.party), "displayName": info.display_name}
            for info in infos
        ]

    async def allocate_parties_async(self, hints: List[str]):
        infos = await self.client.list_known_parties()

        created = []
        for hint in hints:
            if any(str(info.party).startswith(f"{hint}-") or info.display_name == hint for info in infos):
                continue
            p = await self.client.allocate_party(identifier_hint=hint, display_name=hint)
            created.append(str(p.party))

        return to_jsonable(created)
