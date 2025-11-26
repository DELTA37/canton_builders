import argparse
import asyncio
import json
from dreal.settings import LEDGER_URL
from dreal.client import RealEstateClient, RealEstateMeta


def parse_args():
    parser = argparse.ArgumentParser(description="RealEstate Canton CLI")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List all properties")

    # create
    parser_create = subparsers.add_parser("create", help="Create a new property")
    parser_create.add_argument("--property-id", required=True, help="Unique property ID")
    parser_create.add_argument("--owner", required=True, help="Owner name")
    parser_create.add_argument("--address", required=True)
    parser_create.add_argument("--area", type=float, required=True)
    parser_create.add_argument("--cadastral-number", required=True)
    parser_create.add_argument("--building-year", type=int, required=True)

    # transfer
    parser_transfer = subparsers.add_parser("transfer", help="Transfer property to new owner")
    parser_transfer.add_argument("--property-id", required=True)
    parser_transfer.add_argument("--current-owner", required=True)
    parser_transfer.add_argument("--new-owner", required=True)

    # archive all
    subparsers.add_parser("archive_all", help="Archive all properties")

    args = parser.parse_args()
    return args


async def main(command: str, **kwargs):
    async with RealEstateClient() as client:

        if command == "list":
            props = await client.list_properties()
            print(json.dumps(props, indent=2))

        # elif command == "create":
        #     meta = RealEstateMeta(
        #         address=args.address,
        #         area_m2=args.area,
        #         cadastral_number=args.cadastral_number,
        #         building_year=args.building_year,
        #         owner_name=args.owner
        #     )
        #     cid = await client.create_property(args.property_id, args.owner, meta)
        #     print("Created property contract:", cid)
        #
        # elif command == "transfer":
        #     active_props = await client.list_properties()
        #     prop = next((p for p in active_props if p["propertyId"] == args.property_id), None)
        #     if not prop:
        #         print(f"Property {args.property_id} not found")
        #         return
        #     cid = prop.get("contract_id")
        #     result = await client.transfer_property(cid, args.current_owner, args.new_owner)
        #     print("Transfer result:", result)
        #
        # elif command == "archive_all":
        #     await client.archive_all_properties()
        #     print("All properties archived")
        #
        # else:
        #     parser.print_help()


if __name__ == "__main__":
    asyncio.run(main(**vars(parse_args())))
