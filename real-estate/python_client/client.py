import argparse
import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import dazl
from dazl.ledger import Boundary, api_types
from dazl.ledger.api_types import CreateEvent

DEFAULT_LEDGER_HOST = os.getenv("LEDGER_HOST", "localhost")
DEFAULT_LEDGER_PORT = int(os.getenv("LEDGER_PORT", "26865"))
DEFAULT_PARTY = os.getenv("LEDGER_PARTY", "")
DEFAULT_APP_NAME = os.getenv("LEDGER_APP_NAME", "real-estate-client")


def _url(host: str, port: int) -> str:
  return f"grpc://{host}:{port}"


async def _resolve_party(conn: dazl.Connection, hint: str) -> str:
  """
  Try to resolve short party hints to fully qualified Canton party ids.
  Falls back to the hint if no match is found.
  """
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
    )
    return {"contractId": cid}


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
    party=party,
    read_as=[party],
    act_as=[party],
    application_name=DEFAULT_APP_NAME,
  ) as client:
    acting_party = await _resolve_party(client, party)
    res = await client.exercise("RealEstate:RealEstate", contract_id, choice, argument, act_as=[acting_party])
    return {"result": res}


async def _list_async(party: str, host: str, port: int) -> Dict[str, Any]:
  async with dazl.connect(
    url=_url(host, port),
    party=party,
    read_as=[party],
    application_name=DEFAULT_APP_NAME,
  ) as client:
    contracts: List[Dict[str, Any]] = []
    async for c in client.query("RealEstate:RealEstate"):
      if isinstance(c, api_types.CreateEvent):
        contracts.append({"contractId": str(c.contract_id), "payload": c.payload})
      elif isinstance(c, api_types.Boundary):
        continue
      elif hasattr(c, "contract_id") and hasattr(c, "payload"):
        contracts.append({"contractId": str(c.contract_id), "payload": c.payload})
      else:
        contracts.append({"raw": str(c)})
    return {"contracts": contracts}


def create_property(
  registrar: str,
  owner: str,
  property_id: str,
  address: str,
  property_type: str,
  area: str,
  meta_json: str,
  host: str = DEFAULT_LEDGER_HOST,
  port: int = DEFAULT_LEDGER_PORT,
) -> Dict[str, Any]:
  return asyncio.run(
    _create_async(registrar, owner, property_id, address, property_type, area, meta_json, host, port)
  )


def transfer_property(contract_id: str, new_owner: str, party: str, host: str, port: int) -> Dict[str, Any]:
  return asyncio.run(
    _exercise_async(party, contract_id, "Transfer", {"newOwner": new_owner}, host=host, port=port)
  )


def update_meta(contract_id: str, new_meta_json: str, party: str, host: str, port: int) -> Dict[str, Any]:
  return asyncio.run(
    _exercise_async(
      party,
      contract_id,
      "UpdateMeta",
      {"newMetaJson": new_meta_json},
      host=host,
      port=port,
    )
  )


def archive_property(contract_id: str, party: str, host: str, port: int) -> Dict[str, Any]:
  return asyncio.run(
    _exercise_async(party, contract_id, "ArchiveProperty", {}, host=host, port=port)
  )


def list_properties(party: str, host: str, port: int) -> Dict[str, Any]:
  return asyncio.run(_list_async(party, host, port))


def main() -> None:
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

  args = parser.parse_args()

  if args.cmd == "create":
    result = create_property(
      registrar=args.registrar,
      owner=args.owner,
      property_id=args.property_id,
      address=args.address,
      property_type=args.property_type,
      area=args.area,
      meta_json=args.meta_json,
      host=args.host,
      port=args.port,
    )
  elif args.cmd == "transfer":
    result = transfer_property(args.cid, args.new_owner, party=args.party, host=args.host, port=args.port)
  elif args.cmd == "update-meta":
    result = update_meta(args.cid, args.meta_json, party=args.party, host=args.host, port=args.port)
  elif args.cmd == "archive":
    result = archive_property(args.cid, party=args.party, host=args.host, port=args.port)
  elif args.cmd == "list":
    list_party = args.party or args.party
    result = list_properties(list_party, host=args.host, port=args.port)
  else:
    raise SystemExit("Unknown command")

  print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
  main()
