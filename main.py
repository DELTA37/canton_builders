import argparse
import asyncio
import json

from python_client.client import (
    DEFAULT_LEDGER_HOST,
    DEFAULT_LEDGER_PORT,
    DEFAULT_PARTY,
    RealEstateHandler,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="dazl gRPC client for RealEstate template.")
    parser.add_argument("--host", default=DEFAULT_LEDGER_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_LEDGER_PORT)
    parser.add_argument("--party", default=DEFAULT_PARTY, help="Default party for list; required for exercises.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create_cmd = sub.add_parser("create", help="Create a RealEstate contract")
    create_cmd.add_argument("--registrar", required=True)
    create_cmd.add_argument("--owner", required=True)
    create_cmd.add_argument("--property-id", required=True)
    create_cmd.add_argument("--address", required=True)
    create_cmd.add_argument("--property-type", required=True)
    create_cmd.add_argument("--area", required=True, help="decimal, e.g. 72.5")
    create_cmd.add_argument("--meta-json", required=True, help='e.g. \'{"address":"Baker St"}\'')
    create_cmd.add_argument("--price", required=True, help="asking price, decimal")
    create_cmd.add_argument("--currency", required=True, help="currency code, e.g. USD")
    create_cmd.add_argument("--listed", action="store_true", help="mark as listed on creation")

    transfer_cmd = sub.add_parser("transfer", help="Transfer a RealEstate contract to a new owner")
    transfer_cmd.add_argument("--cid", required=True)
    transfer_cmd.add_argument("--new-owner", required=True)
    transfer_cmd.add_argument("--party", required=True, help="Current owner")

    update_cmd = sub.add_parser("update-meta", help="Update metadata JSON for a RealEstate contract")
    update_cmd.add_argument("--cid", required=True)
    update_cmd.add_argument("--meta-json", required=True)
    update_cmd.add_argument("--party", required=True, help="Current owner")

    archive_cmd = sub.add_parser("archive", help="Archive a RealEstate contract")
    archive_cmd.add_argument("--cid", required=True)
    archive_cmd.add_argument("--party", required=True, help="Registrar")

    list_cmd = sub.add_parser("list", help="List RealEstate contracts visible to the party")
    list_cmd.add_argument("--party", help="Party to query as; defaults to --party")

    alloc_cmd = sub.add_parser("allocate-parties", help="Ensure parties exist on ledger")
    alloc_cmd.add_argument("--parties", nargs="+", required=True, help="Party hints/display names to ensure")

    sub.add_parser("list-parties", help="List known parties")

    list_for_sale_cmd = sub.add_parser("list-for-sale", help="List a property for sale")
    list_for_sale_cmd.add_argument("--cid", required=True)
    list_for_sale_cmd.add_argument("--price", required=True)
    list_for_sale_cmd.add_argument("--currency", required=True)
    list_for_sale_cmd.add_argument("--party", required=True, help="Current owner")

    delist_cmd = sub.add_parser("delist", help="Remove a property from sale")
    delist_cmd.add_argument("--cid", required=True)
    delist_cmd.add_argument("--party", required=True, help="Current owner")

    buy_cmd = sub.add_parser("buy", help="Purchase a listed property")
    buy_cmd.add_argument("--cid", required=True)
    buy_cmd.add_argument("--price", required=True, help="expected price")
    buy_cmd.add_argument("--currency", required=True, help="expected currency")
    buy_cmd.add_argument("--party", required=True, help="Acting party (seller/owner)")
    buy_cmd.add_argument("--buyer", required=True, help="New owner")
    buy_cmd.add_argument("--seller", required=True, help="Current owner/seller")
    buy_cmd.add_argument("--payment-cid", required=True, help="Cash contract to transfer to seller")

    mint_cash_cmd = sub.add_parser("mint-cash", help="Mint cash for a user")
    mint_cash_cmd.add_argument("--issuer", required=True)
    mint_cash_cmd.add_argument("--owner", required=True)
    mint_cash_cmd.add_argument("--amount", required=True)
    mint_cash_cmd.add_argument("--currency", required=True)

    list_cash_cmd = sub.add_parser("list-cash", help="List cash visible to a party")
    list_cash_cmd.add_argument("--party", help="Party to query as; defaults to --party")
    return parser.parse_args()


def party_for_command(args: argparse.Namespace) -> str:
    if args.cmd == "create":
        return args.registrar or args.party
    if args.cmd in {"transfer", "update-meta", "archive", "list", "list-for-sale", "delist", "list-cash"}:
        return args.party
    if args.cmd == "allocate-parties":
        return args.party or (args.parties[0] if args.parties else DEFAULT_PARTY)
    if args.cmd == "list-parties":
        return args.party
    if args.cmd == "mint-cash":
        return args.owner
    if args.cmd == "buy":
        return args.buyer
    return DEFAULT_PARTY


async def run_command(args: argparse.Namespace) -> dict:
    party_hint = party_for_command(args)
    async with RealEstateHandler(host=args.host, port=args.port, party=party_hint) as handler:
        if args.cmd == "create":
            return await handler.create_property_async(
                registrar=args.registrar,
                owner=args.owner,
                property_id=args.property_id,
                address=args.address,
                property_type=args.property_type,
                area=args.area,
                meta_json=args.meta_json,
                price=args.price,
                currency=args.currency,
                listed=args.listed,
            )
        if args.cmd == "transfer":
            return await handler.transfer_property_async(
                contract_id=args.cid,
                new_owner=args.new_owner,
            )
        if args.cmd == "update-meta":
            return await handler.update_meta_async(
                contract_id=args.cid,
                meta_json=args.meta_json,
            )
        if args.cmd == "archive":
            return await handler.archive_property_async(contract_id=args.cid)
        if args.cmd == "list":
            return await handler.list_properties_async()
        if args.cmd == "list-for-sale":
            return await handler.list_for_sale_async(
                contract_id=args.cid,
                price=args.price,
                currency=args.currency,
            )
        if args.cmd == "delist":
            return await handler.delist_property_async(contract_id=args.cid)
        if args.cmd == "buy":
            return await handler.buy_property_async(
                contract_id=args.cid,
                price=args.price,
                currency=args.currency,
                buyer=args.buyer,
                payment_cid=args.payment_cid,
                seller=args.seller,
            )
        if args.cmd == "allocate-parties":
            return await handler.allocate_parties_async(hints=args.parties)
        if args.cmd == "list-parties":
            return await handler.list_parties_async()
        if args.cmd == "mint-cash":
            return await handler.mint_cash_async(
                issuer=args.issuer,
                owner=args.owner,
                amount=args.amount,
                currency=args.currency,
            )
        if args.cmd == "list-cash":
            return await handler.list_cash_async()
    raise SystemExit("Unknown command")


def main() -> None:
    args = parse_args()
    output = asyncio.run(run_command(args))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
