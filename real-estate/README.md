# Real Estate Sample

Python helpers for the RealEstate Daml template live in `python_client/client.py`. The commands below assume the Canton sandbox is running via `./run-sandbox.sh` (ledger gRPC on port 26865 by default).

## Prepare parties
Allocate the parties you plan to use (registrar, current owner, and future owner):
```
python python_client/client.py allocate-parties --parties Registrar Owner Buyer
```

## Add a property (create)
Registers a new property on the ledger. The command returns a `contractId` you can use in later steps.
```
python python_client/client.py --host localhost --port 26865 create \
  --registrar Registrar \
  --owner Owner \
  --property-id PROP-001 \
  --address "221B Baker Street" \
  --property-type apartment \
  --area 72.5 \
  --meta-json '{"notes":"first listing"}'
```

## Transfer a property to a new owner
The current owner exercises `Transfer` to hand over the contract. Replace `<cid>` with the `contractId` from the create step.
```
python python_client/client.py --host localhost --port 26865 transfer \
  --cid <cid> \
  --new-owner Buyer \
  --party Owner
```

## Remove a property (archive)
The registrar archives the property contract. Replace `<cid>` with the `contractId` you want to close.
```
python python_client/client.py --host localhost --port 26865 archive \
  --cid <cid> \
  --party Registrar
```

## Inspect current properties
List the active `RealEstate` contracts visible to a party.
```
python python_client/client.py list --party Registrar
```
