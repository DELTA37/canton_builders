import argparse
import asyncio
import datetime
import decimal
import json
import os
from typing import Any, Dict, List, Optional

import dazl
from dazl import Party
from dazl.ledger import Boundary, api_types
from dazl.ledger.api_types import CreateEvent

DEFAULT_LEDGER_HOST = os.getenv("LEDGER_HOST", "localhost")
DEFAULT_LEDGER_PORT = int(os.getenv("LEDGER_PORT", "26865"))
DEFAULT_PARTY = os.getenv("LEDGER_PARTY", "")
DEFAULT_APP_NAME = os.getenv("LEDGER_APP_NAME", "real-estate-client")


def _url(host: str, port: int) -> str:
    return f"grpc://{host}:{port}"


def _to_jsonable(val: Any) -> Any:
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    if isinstance(val, decimal.Decimal):
        return str(val)
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _to_jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_to_jsonable(v) for v in val]
    if isinstance(val, CreateEvent):
        return {"contractId": str(val.contract_id), "payload": _to_jsonable(val.payload)}
    return str(val)


async def _ensure_parties(party_hints: List[str], host: str, port: int) -> List[str]:
    created: List[str] = []
    bootstrap = party_hints[0] if party_hints else "Observer"
    async with dazl.connect(url=_url(host, port), party=bootstrap, application_name=DEFAULT_APP_NAME) as conn:
        existing = await conn.list_known_parties()
        for hint in party_hints:
            found = None
            for info in existing:
                pid = str(info.party)
                if pid.startswith(f"{hint}-") or info.display_name == hint:
                    found = pid
                    break
            if found:
                continue
            allocated = await conn.allocate_party(identifier_hint=hint, display_name=hint)
            created.append(str(allocated.party))
        return created


async def _resolve_party(conn: dazl.Connection, hint: str) -> str:
    if "::" in hint:
        return hint
    try:
        infos = await conn.list_known_parties()
        for info in infos:
            party_id = str(info.party)
            if party_id.startswith(f"{hint}-") or info.display_name == hint:
                return party_id
    except Exception:
        pass
    return hint


async def _create_async(
    registrar: str,
    owner: str,
    property_id: str,
    address: str,
    property_type: str,
    area: str,
    meta_json: str,
    host: str,
    port: int,
) -> Dict[str, Any]:
    async with dazl.connect(
        url=_url(host, port),
        party=registrar,
        read_as=[registrar],
        act_as=[registrar],
        application_name=DEFAULT_APP_NAME,
    ) as client:
        registrar_id = await _resolve_party(client, registrar)
        owner_id = await _resolve_party(client, owner)
        cid = await client.create(
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
            },
            act_as=[Party(registrar_id)],
            read_as=[Party(registrar_id)],
        )
        return _to_jsonable({"contractId": cid})


async def _exercise_async(
    party: str,
    contract_id: str,
    choice: str,
    argument: Dict[str, Any],
    host: str,
    port: int,
) -> Dict[str, Any]:
    async with dazl.connect(
        url=_url(host, port),
        party=Party(party),
        read_as=[Party(party)],
        act_as=[Party(party)],
        application_name=DEFAULT_APP_NAME,
    ) as client:
        acting_party = await _resolve_party(client, party)
        res = await client.exercise(
            "RealEstate:RealEstate",
            contract_id,
            choice,
            argument,
            act_as=[Party(acting_party)],
            read_as=[Party(acting_party)],
        )
        return _to_jsonable({"result": res})


async def _list_async(party: str, host: str, port: int) -> Dict[str, Any]:
    async with dazl.connect(
        url=_url(host, port),
        party=party,
        read_as=[party],
        application_name=DEFAULT_APP_NAME,
    ) as client:
        contracts: List[Dict[str, Any]] = []
        async for c in client.query("RealEstate:RealEstate"):
            if isinstance(c, CreateEvent):
                contracts.append({"contractId": str(c.contract_id), "payload": c.payload})
            elif isinstance(c, Boundary):
                continue
            elif hasattr(c, "contract_id") and hasattr(c, "payload"):
                contracts.append({"contractId": str(c.contract_id), "payload": c.payload})
            else:
                contracts.append({"raw": str(c)})
        return _to_jsonable({"contracts": contracts})


async def _list_parties_async(host: str, port: int, party: str) -> Dict[str, Any]:
    async with dazl.connect(
        url=_url(host, port),
        party=Party(party),
        application_name=DEFAULT_APP_NAME,
    ) as conn:
        infos = await conn.list_known_parties()
        return _to_jsonable({"parties": [{"id": str(i.party), "displayName": i.display_name} for i in infos]})


async def main(cmd: str, **kwargs) -> Dict[str, Any]:
    host = kwargs.get("host", DEFAULT_LEDGER_HOST)
    port = kwargs.get("port", DEFAULT_LEDGER_PORT)
    party = kwargs.get("party", DEFAULT_PARTY)

    if cmd == "create":
        return await _create_async(
            registrar=kwargs["registrar"],
            owner=kwargs["owner"],
            property_id=kwargs["property_id"],
            address=kwargs["address"],
            property_type=kwargs["property_type"],
            area=kwargs["area"],
            meta_json=kwargs["meta_json"],
            host=host,
            port=port,
        )
    if cmd == "transfer":
        return await _exercise_async(kwargs["party"],
                                     kwargs["cid"],
                                     "Transfer",
                                     {"newOwner": kwargs["new_owner"]}, host, port)
    if cmd == "update-meta":
        return await _exercise_async(kwargs["party"],
                                     kwargs["cid"],
                                     "UpdateMeta",
                                     {"newMetaJson": kwargs["meta_json"]}, host, port)
    if cmd == "archive":
        return await _exercise_async(kwargs["party"],
                                     kwargs["cid"],
                                     "ArchiveProperty",
                                     {}, host, port)
    if cmd == "list":
        list_party = kwargs.get("party") or party
        return await _list_async(list_party,
                                 host, port)
    if cmd == "allocate-parties":
        return {"created": await _ensure_parties(kwargs["parties"],
                                                 host=host, port=port)}
    if cmd == "list-parties":
        return await _list_parties_async(host=host, port=port, party=party)
    raise SystemExit("Unknown command")


def parse_args():
    parser = argparse.ArgumentParser(description="dazl gRPC client for RealEstate template.")
    parser.add_argument("--host", default=DEFAULT_LEDGER_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_LEDGER_PORT)
    parser.add_argument("--party", default=DEFAULT_PARTY, help="Default party for list; required for exercises.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create_cmd = sub.add_parser("create")
    create_cmd.add_argument("--registrar", required=True)
    create_cmd.add_argument("--owner", required=True)
    create_cmd.add_argument("--property-id", required=True)
    create_cmd.add_argument("--address", required=True)
    create_cmd.add_argument("--property-type", required=True)
    create_cmd.add_argument("--area", required=True, help="decimal, e.g. 72.5")
    create_cmd.add_argument("--meta-json", required=True, help='e.g. \'{"address":"Baker St"}\'')

    transfer_cmd = sub.add_parser("transfer")
    transfer_cmd.add_argument("--cid", required=True)
    transfer_cmd.add_argument("--new-owner", required=True)
    transfer_cmd.add_argument("--party", required=True, help="Current owner")

    update_cmd = sub.add_parser("update-meta")
    update_cmd.add_argument("--cid", required=True)
    update_cmd.add_argument("--meta-json", required=True)
    update_cmd.add_argument("--party", required=True, help="Current owner")

    archive_cmd = sub.add_parser("archive")
    archive_cmd.add_argument("--cid", required=True)
    archive_cmd.add_argument("--party", required=True, help="Registrar")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--party", help="Party to query as; defaults to --party")

    alloc_cmd = sub.add_parser("allocate-parties")
    alloc_cmd.add_argument("--parties", nargs="+", required=True, help="Party hints/display names to ensure")

    sub.add_parser("list-parties")
    return parser.parse_args()


if __name__ == "__main__":
    output = asyncio.run(main(**vars(parse_args())))
    print(json.dumps(output, indent=2))
