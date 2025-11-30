# Repository Guidelines

## Project Structure & Module Organization
- `daml/RealEstate.daml`: Core template with `Transfer` choice; keep new templates small and isolate domain logic per module.
- `daml/Main.daml`: Init script `setup` invoked by `daml start`; allocates default parties and seeds an example contract.
- `daml/Test.daml`: Daml Script entrypoint `test`; add more scripts here to cover new flows and reuse shared setup.
- `daml.yaml`: Project settings (SDK 3.4.8, package name, `init-script`); update when adding new modules or bumping version.
- `sandbox.conf`: Canton sandbox config (ledger-api 16865, admin-api 15011, http-ledger 7575, sequencer public/admin 19017/19018, mediator admin 19019) used by `daml start`.
- `log/`: Local runtime logs; useful for debugging, but do not commit changes. Build outputs live in `.daml/dist/`.

## Build, Test, and Development Commands
- `daml build`: Compile and package DAR to `.daml/dist/real-estate-0.0.1.dar`.
- `daml start --sandbox-option --config=sandbox.conf`: Start local Canton sandbox using `sandbox.conf` (ports: ledger 16865, admin 15011, http-ledger 7575, sequencer 19017/19018, mediator 19019); auto-builds and uploads the DAR, then runs `Main:setup`.
- `./run-sandbox.sh`: Convenience wrapper for the above; env vars: `JSON_API_PORT` (default 17575), `SANDBOX_CONFIG` (default `sandbox.conf`), `WAIT_FOR_SIGNAL` (`yes`/`no`).
- `./run-app.sh`: Full stack (sandbox + JSON API + Streamlit UI). Env vars: `JSON_API_PORT` (default 17575), `SANDBOX_CONFIG` (default `sandbox.conf`), `UI_PORT` (default 8501), `WAIT_SECONDS` (default 60).
- `daml script --dar .daml/dist/real-estate-0.0.1.dar --script-name Test:test --ledger-host localhost --ledger-port 16865`: Run the scripted create/transfer flow against the running sandbox.
- `daml test --project-root .`: Scenario test runner (none today); keeps compilation tight and is a good pre-push sanity check.
- JSON API (for Python/UI) runs from `daml start` on port 17575 by default; use `--json-api-port` to override if needed.

## Coding Style & Naming Conventions
- Daml modules/templates use `CamelCase`; record fields and variables use `lowerCamel`; choice names are verbs (`Transfer`, `Archive`).
- Indent with two spaces; keep imports minimal and prefer explicit exports when modules grow.
- Keep template comments concise and domain-focused; encode history updates in the contract rather than imperative comments.

## Testing Guidelines
- Add new Daml Scripts in `daml/Test.daml` for each behavior; name scripts `test<Behavior>` and keep them deterministic.
- Use `allocateParty` for fresh principals in scripts; avoid sharing party names across tests unless intentional.
- When changing choices or ledger-facing behavior, rerun `daml build` and the relevant `daml script` against a fresh sandbox instance.

## Python Client & UI
- Dependencies in `python_client/requirements.txt` (`requests`, `streamlit`); install with `pip install -r python_client/requirements.txt`.
- CLI: `python main.py create --registrar Registrar --owner Owner --property-id ID-42 --address "Main St" --property-type apartment --area 50.0 --meta-json '{}' --host localhost --port 26865`.
- UI: `streamlit run ui.py` (uses `LEDGER_HOST`/`LEDGER_PORT` or sidebar fields).

## Commit & Pull Request Guidelines
- Commit messages follow the existing short, imperative style (`fix canton net`, `canton initial`); keep subject lines under ~50 chars.
- Include PR descriptions with: what changed, why, how to verify (commands above), and any ledger port/config adjustments.
- Exclude generated artifacts (`.daml/dist`, `log/`) from commits; attach screenshots or log snippets only when they clarify behavior.
