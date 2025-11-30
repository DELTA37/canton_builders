# Real Estate Sample

Python helpers for the RealEstate Daml template live in `python_client/client.py` (exposed as `RealEstateHandler`). The commands below assume the Canton sandbox is running via `./run-sandbox.sh` (ledger gRPC on port 26865 by default).

## Prepare parties
Allocate the parties you plan to use (registrar, current owner, and future owner):
```
python main.py allocate-parties --parties Registrar Owner Buyer
```

## Add a property (create)
Registers a new property on the ledger. The command returns a `contractId` you can use in later steps.
```
python main.py --host localhost --port 26865 create \
  --registrar Registrar \
  --owner Owner \
  --property-id PROP-001 \
  --address "221B Baker Street" \
  --property-type apartment \
  --area 72.5 \
  --meta-json '{"notes":"first listing"}' \
  --price 500000.0 \
  --currency USD \
  --listed
```

## Transfer a property to a new owner
The current owner exercises `Transfer` to hand over the contract. Replace `<cid>` with the `contractId` from the create step.
```
python main.py --host localhost --port 26865 transfer \
  --cid <cid> \
  --new-owner Buyer \
  --party Owner
```

## List property for sale / delist
```
python main.py --host localhost --port 26865 list-for-sale \
  --cid <cid> \
  --price 510000.0 \
  --currency USD \
  --party Owner

python main.py --host localhost --port 26865 delist \
  --cid <cid> \
  --party Owner
```

## Buy a listed property
The seller exercises `Buy` (as controller) and references the buyer's cash contract (exact amount/currency).
```
python main.py --host localhost --port 26865 buy \
  --cid <cid> \
  --price 510000.0 \
  --currency USD \
  --buyer Buyer \
  --payment-cid <cash-cid> \
  --seller Seller \
  --party Buyer    # acting party includes buyer; seller added via --seller
```

## Remove a property (archive)
The registrar archives the property contract. Replace `<cid>` with the `contractId` you want to close.
```
python main.py --host localhost --port 26865 archive \
  --cid <cid> \
  --party Registrar
```

## Cash (demo money)
Mint cash for a user (issuer + owner sign):
```
python main.py --host localhost --port 26865 mint-cash \
  --issuer Seller \
  --owner Buyer \
  --amount 510000.0 \
  --currency USD
```

List cash visible to a party:
```
python main.py --host localhost --port 26865 list-cash --party Buyer
```

## Inspect current properties
List the active `RealEstate` contracts visible to a party.
```
python main.py list --party Registrar
```
