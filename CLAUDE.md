# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Canton-based real estate property registry and marketplace application. It demonstrates Daml smart contracts for property ownership, transfer, and sales with integrated cash payment handling. The stack includes:
- **Daml smart contracts**: Property registration, ownership transfer, marketplace listings, and cash contracts
- **Canton ledger**: Distributed ledger runtime (SDK 2.10.2)
- **Python client**: CLI and Streamlit UI using dazl library for gRPC interaction
- **Streamlit web UI**: Interactive real estate marketplace dashboard

## Build and Run Commands

### Daml Development

Build the DAR package:
```bash
cd real-estate
daml build
```

Start Canton sandbox with auto-build and init script:
```bash
cd real-estate
daml start --sandbox-option --config=sandbox.conf
```

Or use the convenience wrapper:
```bash
cd real-estate
./run-sandbox.sh
```

Run Daml test scripts against a running ledger:
```bash
cd real-estate
daml script --dar .daml/dist/real-estate-0.0.1.dar --script-name Test:test --ledger-host localhost --ledger-port 26865
```

Run scenario tests (pre-push sanity check):
```bash
cd real-estate
daml test --project-root .
```

### Python Client

Install dependencies:
```bash
pip install -e .
# or with poetry
poetry install
```

CLI examples (see README.md for full command reference):
```bash
# Allocate parties
python main.py allocate-parties --parties Registrar Owner Buyer

# Create a property
python main.py create --registrar Registrar --owner Owner --property-id PROP-001 --address "221B Baker Street" --property-type apartment --area 72.5 --meta-json '{"notes":"first listing"}' --price 500000.0 --currency USD --listed

# Transfer property
python main.py transfer --cid <contract-id> --new-owner Buyer --party Owner

# List properties
python main.py list --party Registrar
```

### Full Stack (UI)

Run the complete application (sandbox + JSON API + Streamlit):
```bash
./run-app.sh
```

Environment variables:
- `JSON_API_PORT` (default: 17575)
- `SANDBOX_CONFIG` (default: sandbox.conf)
- `UI_PORT` (default: 8501)
- `WAIT_SECONDS` (default: 60)
- `LEDGER_HOST` (default: localhost)
- `LEDGER_PORT` (default: 26865)

Skip sandbox startup and use existing ledger:
```bash
SKIP_SANDBOX=true ./run-app.sh
```

## Architecture

### Daml Smart Contracts (`real-estate/daml/`)

**RealEstate.daml**: Core templates and workflow choices
- `Cash` template: Represents fungible payment with `CashTransfer` choice (owner + newOwner signatories)
- `RealEstate` template: Property contract with registrar (signatory) and owner (observer + controller)
  - Choices: `Transfer`, `UpdateMeta`, `ListForSale`, `Delist`, `Buy`, `ArchiveProperty`
  - `Buy` choice requires both owner (seller) and buyer as controllers; validates payment contract (exact amount/currency match), archives buyer's cash, creates new cash for seller, and transfers property ownership
  - `listed` flag gates the `Buy` choice; `ListForSale`/`Delist` toggle this flag
  - `history` field accumulates previous owners on each transfer

**Main.daml**: Ledger initialization script (`setup`)
- Allocates default parties (Registrar, Owner)
- Seeds example RealEstate contract
- Invoked automatically via `daml.yaml` `init-script` field on `daml start`

**Test.daml**: Daml Script test scenarios
- Add new test scripts here for behavior coverage
- Name scripts `test<Behavior>` and keep deterministic

### Python Client Layer

**python_client/client.py**: `RealEstateHandler` class
- Async context manager wrapping dazl connection lifecycle
- Resolves party hints to canonical party IDs via `list_known_parties()` lookup
- Single connection per handler instance (opened in `__aenter__`, closed in `__aexit__`)
- Methods for create, exercise (transfer, update-meta, list-for-sale, delist, buy), and query operations
- `buy_property_async` uses `extra_act_as` to include both buyer and seller parties for multi-controller choice

**main.py**: CLI entry point with argparse subcommands
- Maps CLI args to `RealEstateHandler` async methods
- `party_for_command()` determines acting party based on command type
- All commands run async via `asyncio.run()`

**ui.py**: Streamlit interactive UI
- Three-tab interface: Registrar (party allocation, property creation), Seller (listings management), Buyer (cash wallet, marketplace)
- Role-based views with current_party session state
- `run_with_handler()` utility creates temporary handler per action
- Marketplace filter by currency, cash wallet display, buy flow with payment contract selection

### Canton Configuration

**real-estate/sandbox.conf**: Canton participant configuration
- Ledger API on port 26865
- Admin API on port 25011
- In-memory storage (no persistence)

**real-estate/daml.yaml**: Daml project metadata
- SDK version 2.10.2
- Init script `Main:setup` auto-runs on `daml start`
- Dependencies: daml-prim, daml-stdlib, daml-script

### Ledger Ports

- **Ledger gRPC (participant)**: 26865 (configurable via `LEDGER_PORT`)
- **Admin API**: 25011
- **JSON API (HTTP)**: 17575 (configurable via `JSON_API_PORT`)

## Key Design Patterns

### Party Resolution
Party hints (e.g., "Buyer") are resolved to canonical IDs (e.g., "Buyer-123::abc...") via `list_known_parties()` lookup matching either display name or prefix. This allows the UI and CLI to use human-readable names while the ledger uses stable identifiers.

### Multi-Controller Choices
The `Buy` choice requires both `owner` (seller) and `buyer` as controllers. The Python client uses `extra_act_as` to include both parties in the submission. The UI collects buyer party input and infers seller from the property payload.

### Cash Payment Flow
1. Buyer mints `Cash` contract (issuer + owner sign) via `mint_cash_async`
2. Seller lists property via `ListForSale` choice (sets `listed=True`, price, currency)
3. Buyer exercises `Buy` choice with payment contract ID
4. `Buy` choice validates payment (owner, currency, amount match), archives buyer's cash, creates new cash for seller, transfers property

### History Tracking
The `history` field in `RealEstate` is a list of previous owners. On each `Transfer` or `Buy`, the current owner is appended before the ownership change. This creates an immutable audit trail of ownership changes on-ledger.

## Development Notes

### Commit Message Style
Follow short, imperative style (e.g., "update daml", "fix create property"). Keep subject lines under 50 characters.

### Testing New Choices
When adding or modifying Daml choices:
1. Update `RealEstate.daml` template
2. Add corresponding test in `Test.daml`
3. Run `daml build` and `daml script` against fresh sandbox
4. Add client method in `python_client/client.py` if needed
5. Add CLI subcommand in `main.py` if needed
6. Update UI in `ui.py` if needed

### Port Conflicts
If ports 26865 (ledger) or 17575 (JSON API) are in use, override with environment variables:
```bash
LEDGER_PORT=27865 JSON_API_PORT=18575 ./run-app.sh
```

### Debugging
- Canton sandbox logs: `real-estate/log/app-sandbox.log` (when using `run-app.sh`)
- Streamlit logs: stdout from `streamlit run ui.py`
- Python client errors: Check party resolution (hint vs canonical ID mismatch)
- Daml contract validation failures: Check ensure clauses and choice preconditions (assertMsg)
