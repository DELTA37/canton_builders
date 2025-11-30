import asyncio
import os
import sys
import traceback
from typing import Any, Dict, List

import streamlit as st

from python_client.client import DEFAULT_LEDGER_HOST, DEFAULT_LEDGER_PORT, RealEstateHandler

st.set_page_config(page_title="Canton Real Estate", layout="wide")

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
:root {
  --bg: #050b18;
  --panel: rgba(255, 255, 255, 0.04);
  --panel-strong: rgba(255, 255, 255, 0.08);
  --stroke: rgba(255, 255, 255, 0.12);
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #7dd3fc;
  --accent-2: #fbbf24;
}
html, body, [class*="css"] {
  font-family: "Space Grotesk", "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
}
body {
  background:
    radial-gradient(circle at 10% 20%, rgba(125, 211, 252, 0.12), transparent 25%),
    radial-gradient(circle at 90% 10%, rgba(251, 191, 36, 0.14), transparent 25%),
    radial-gradient(circle at 20% 80%, rgba(56, 189, 248, 0.08), transparent 30%),
    linear-gradient(135deg, #050b18, #0a1530 65%, #051024);
  color: var(--text);
}
.stApp {
  background: black;
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #040915, #071022);
  border-right: 1px solid var(--stroke);
}
[data-testid="stSidebar"] * {
  color: var(--text) !important;
}
.hero {
  position: relative;
  padding: 26px 28px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(125, 211, 252, 0.2), rgba(80, 136, 255, 0.08)), var(--panel);
  border: 1px solid var(--stroke);
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
  margin-bottom: 12px;
}
.hero:before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(125, 211, 252, 0.35), transparent 40%),
    radial-gradient(circle at 80% 10%, rgba(251, 191, 36, 0.45), transparent 35%);
  filter: blur(38px);
  opacity: 0.6;
}
.hero__content { position: relative; z-index: 2; }
.hero__eyebrow { color: var(--accent); font-weight: 600; letter-spacing: 0.12em; font-size: 12px; text-transform: uppercase; }
.hero__title { font-size: 30px; font-weight: 800; margin: 6px 0 4px; letter-spacing: -0.4px; }
.hero__subtitle { opacity: 0.9; max-width: 760px; margin-bottom: 12px; color: var(--muted); }
.hero__meta { display: flex; flex-wrap: wrap; gap: 8px; }
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--stroke);
  font-size: 12px;
  color: var(--text);
}
.pill strong { color: #fff; }
.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  display: inline-block;
}
.toolbar {
  margin: 16px 0 6px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}
.toolbar__item {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--stroke);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
  color: var(--text);
}
.toolbar__label { color: var(--muted); font-size: 12px; letter-spacing: 0.05em; text-transform: uppercase; }
.toolbar__value { font-weight: 700; font-size: 15px; margin-top: 4px; }
.section-title {
  font-size: 18px;
  margin-bottom: 6px;
  font-weight: 700;
  color: var(--text);
}
.muted { color: var(--muted); font-size: 13px; }
.chip {
  background: rgba(255, 255, 255, 0.07);
  padding: 7px 12px;
  border-radius: 10px;
  border: 1px solid var(--stroke);
  font-size: 12px;
  color: var(--text);
}
.stat {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.02));
  border: 1px solid var(--stroke);
  border-radius: 14px;
  padding: 12px 14px;
  color: var(--text);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28);
}
.stat .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.stat .value { font-size: 22px; font-weight: 800; letter-spacing: -0.4px; }
.card {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}
.card-light {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--stroke);
  border-radius: 14px;
  padding: 14px 16px;
  color: var(--text);
}
[data-testid="stExpander"] {
  border-radius: 14px;
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.04);
}
.stButton>button {
  background: linear-gradient(135deg, var(--accent), #4dd4c2);
  color: #041426;
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  font-weight: 700;
}
.stButton>button:hover { transform: translateY(-1px); box-shadow: 0 12px 26px rgba(0,0,0,0.28); }
.stButton>button:active { transform: translateY(0); }
input, textarea {
  color: var(--text) !important;
}
.stTextInput input, .stNumberInput input, .stTextArea textarea {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid var(--stroke) !important;
  border-radius: 12px !important;
}
.stSelectbox [data-baseweb="select"], .stMultiSelect [data-baseweb="select"] {
  background: rgba(255, 255, 255, 0.05) !important;
  border-radius: 12px !important;
  border: 1px solid var(--stroke) !important;
}
.stSelectbox [data-baseweb="popover"], .stMultiSelect [data-baseweb="popover"] {
  background: #0a1425 !important;
  color: var(--text) !important;
}
.stRadio > label { font-weight: 700; color: var(--text); }
.stTabs [data-baseweb="tab"] {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12px 12px 0 0;
  border: 1px solid var(--stroke);
  margin-right: 6px;
}
.stTabs [data-baseweb="tab"]:hover { border-color: var(--accent); }
.stTabs [aria-selected="true"] {
  color: #fff;
  background: linear-gradient(135deg, rgba(125, 211, 252, 0.2), rgba(251, 191, 36, 0.15));
}
.stTable { border-radius: 12px; overflow: hidden; }
.stTable table {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text);
}
.stTable th, .stTable td {
  border-color: var(--stroke) !important;
}
.stTable tbody tr:nth-child(even) {
  background: rgba(255, 255, 255, 0.02);
}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# Sidebar: connection + market view
with st.sidebar:
  st.header("Ledger")
  host = st.text_input("Ledger host", value=os.getenv("LEDGER_HOST", DEFAULT_LEDGER_HOST))
  port = st.number_input(
    "Ledger port",
    value=int(os.getenv("LEDGER_PORT", str(DEFAULT_LEDGER_PORT))),
    step=1,
  )
  market_party = st.text_input("View as (party)", value="Registrar")
  st.caption("Contract listings are fetched as the selected party.")


# Session state for the active user
if "current_party" not in st.session_state:
  st.session_state["current_party"] = os.getenv("LEDGER_PARTY", "Buyer")
if "role" not in st.session_state:
  st.session_state["role"] = "Buyer"


def set_current_party(value: str) -> None:
  st.session_state["current_party"] = value.strip() or st.session_state["current_party"]


def current_party() -> str:
  return st.session_state["current_party"]


def run_with_handler(party_hint: str, action):
  async def _run():
    async with RealEstateHandler(host=host, port=int(port), party=party_hint) as handler:
      return await action(handler)
  return asyncio.run(_run())


def load_properties(view_party: str) -> List[Dict[str, Any]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_properties_async())
  except Exception as ex:
    traceback.print_exc(file=sys.stderr)
    st.error(f"Failed to load contracts: {ex}")
    return []


def load_parties(view_party: str) -> List[Dict[str, str]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_parties_async())
  except Exception as ex:
    traceback.print_exc(file=sys.stderr)
    st.error(f"Failed to load known parties: {ex}")
    return []


def load_cash(view_party: str) -> List[Dict[str, Any]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_cash_async())
  except Exception as ex:
    traceback.print_exc(file=sys.stderr)
    st.error(f"Failed to load wallet: {ex}")
    return []


def price_display(payload: Dict[str, Any]) -> str:
  price = payload.get("price")
  currency = payload.get("currency", "")
  if price is None or currency is None:
    return "-"
  return f"{price} {currency}"


def select_party(label: str, default: str, key: str, options: List[str]) -> str:
  if options:
    idx = options.index(default) if default in options else 0
    return st.selectbox(label, options=options, index=idx, key=key)
  return st.text_input(label, value=default, key=key)


st.markdown(
  f"""
  <div class="hero">
    <div class="hero__content">
      <div class="hero__eyebrow">Digital registry · Canton</div>
      <div class="hero__title">Canton Real Estate Hub</div>
      <div class="hero__subtitle">
        Manage registration, roles (Registrar / Seller / Buyer), listings and settlements through the JSON API.
        Clean, presentation-ready workspace for demos and deal flows.
      </div>
      <div class="hero__meta">
        <span class="pill"><span class="badge-dot"></span><strong>User:</strong> {current_party()}</span>
        <span class="pill"><span class="badge-dot"></span><strong>Viewing as:</strong> {market_party}</span>
        <span class="pill"><span class="badge-dot"></span><strong>Ledger:</strong> {host}:{int(port)}</span>
      </div>
    </div>
  </div>
  """,
  unsafe_allow_html=True,
)

st.markdown(
  f"""
  <div class="toolbar">
    <div class="toolbar__item">
      <div class="toolbar__label">Ledger endpoint</div>
      <div class="toolbar__value">{host}:{int(port)}</div>
      <div class="muted">JSON API connection</div>
    </div>
    <div class="toolbar__item">
      <div class="toolbar__label">Current user</div>
      <div class="toolbar__value">{current_party()}</div>
      <div class="muted">Role: {st.session_state["role"]}</div>
    </div>
    <div class="toolbar__item">
      <div class="toolbar__label">Market view</div>
      <div class="toolbar__value">{market_party}</div>
      <div class="muted">Available listings</div>
    </div>
    <div class="toolbar__item">
      <div class="toolbar__label">Focus</div>
      <div class="toolbar__value">Registry · trades · wallet</div>
      <div class="muted">Canton Real Estate</div>
    </div>
  </div>
  """,
  unsafe_allow_html=True,
)

st.markdown("### Role")
role = st.radio("Select role", ["Buyer", "Seller", "Registrar"], horizontal=True, index=["Buyer", "Seller", "Registrar"].index(st.session_state["role"]))
st.session_state["role"] = role
if role == "Buyer" and current_party() == "Seller":
  set_current_party("Buyer")
elif role == "Seller" and current_party() == "Buyer":
  set_current_party("Seller")
elif role == "Registrar":
  set_current_party("Registrar")

# Market snapshot for dashboard
known_parties = load_parties(market_party)
known_party_ids = [p["id"] for p in known_parties]
market_props = load_properties(market_party)
listed_props = [p for p in market_props if p.get("payload", {}).get("listed")]
stat_cols = st.columns(4)
stat_cols[0].markdown(f"<div class='stat'><div class='label'>Total properties (view)</div><div class='value'>{len(market_props)}</div></div>", unsafe_allow_html=True)
stat_cols[1].markdown(f"<div class='stat'><div class='label'>Listed for sale</div><div class='value'>{len(listed_props)}</div></div>", unsafe_allow_html=True)
stat_cols[2].markdown(f"<div class='stat'><div class='label'>Current role</div><div class='value'>{role}</div></div>", unsafe_allow_html=True)
stat_cols[3].markdown(f"<div class='stat'><div class='label'>Viewing as</div><div class='value'>{market_party}</div></div>", unsafe_allow_html=True)

tab_registrar, tab_seller, tab_buyer = st.tabs(["Registrar", "Seller", "Buyer"])

with tab_registrar:
  st.markdown("#### Registry & onboarding")
  registrar_party = st.text_input("Registrar party", value="Registrar", key="registrar-party")
  reg_cols = st.columns([2, 2, 1])
  new_party_hint = reg_cols[0].text_input("New user hint", value="NewUser")
  allocator_party = reg_cols[1].selectbox("Allocate as (party with rights)", options=["Registrar", "Owner"], index=0, key="alloc-role")
  auto_login = reg_cols[2].checkbox("Make active", value=True)
  if st.button("Register", key="alloc-btn"):
    try:
      created = run_with_handler(
        allocator_party,
        lambda handler: handler.allocate_parties_async([new_party_hint]),
      )
      if created:
        st.success(f"Created: {', '.join(created)}")
        if auto_login:
          set_current_party(created[0])
      else:
        st.info("Party already exists")
    except Exception as ex:
      traceback.print_exc(file=sys.stderr)
      st.error(f"Failed to create party: {ex}")

  if st.button("List known parties", key="list-parties"):
    parties = load_parties(registrar_party)
    if parties:
      st.table(parties)

  st.markdown("#### Create property (Registrar)")
  with st.form("create-reg"):
    owner = st.text_input("Owner party", value="Owner", key="owner-create")
    property_id = st.text_input("Property ID", value="ID-UI-1")
    address = st.text_input("Address", value="Baker St 221b")
    property_type = st.text_input("Property type", value="apartment")
    area = st.text_input("Area (decimal)", value="72.5")
    meta_json = st.text_area("Meta JSON", value='{"address":"Baker St 221b","rooms":3}')
    price = st.text_input("Price", value="500000.0")
    currency = st.selectbox("Currency", options=["USD", "EUR", "GBP", "CHF"], index=0, key="curr-create")
    listed = st.checkbox("List immediately", value=False, key="list-now")
    submit_reg = st.form_submit_button("Create contract")
    if submit_reg:
      try:
        resp = run_with_handler(
          registrar_party,
          lambda handler: handler.create_property_async(
            registrar=registrar_party,
            owner=owner,
            property_id=property_id,
            address=address,
            property_type=property_type,
            area=area,
            meta_json=meta_json,
            price=price,
            currency=currency,
            listed=listed,
          ),
        )
        st.success("Created")
        st.json(resp)
      except Exception as ex:
        traceback.print_exc(file=sys.stderr)
        st.error(f"Create failed: {ex}")

with tab_seller:
  st.markdown("#### Seller workspace")
  seller_party = select_party("Seller party", current_party(), "seller-party", known_party_ids)
  seller_props = [p for p in load_properties(seller_party) if p.get("payload", {}).get("owner") == seller_party]
  seller_listed = [p for p in seller_props if p.get("payload", {}).get("listed")]
  st.markdown(f"<div class='chip'>Owned: {len(seller_props)} • Listed: {len(seller_listed)}</div>", unsafe_allow_html=True)
  if not seller_props:
    st.info("No properties. Ask registrar to create or buy one.")
  else:
    for prop in seller_props:
      cid = prop.get("contractId")
      payload = prop.get("payload", {})
      header = f"{payload.get('propertyId')} — {payload.get('address')}"
      with st.expander(header, expanded=False):
        st.write({
          "contractId": cid,
          "type": payload.get("propertyType"),
          "area": payload.get("area"),
          "price": price_display(payload),
          "listed": payload.get("listed"),
          "history": payload.get("history"),
        })
        with st.form(f"seller-actions-{cid}"):
          col1, col2, col3 = st.columns([1, 1, 1])
          list_price = col1.text_input("Price", value=str(payload.get("price", "")), key=f"list-price-{cid}")
          currency_options = ["USD", "EUR", "GBP", "CHF"]
          cur_default = payload.get("currency", "USD")
          cur_index = currency_options.index(cur_default) if cur_default in currency_options else 0
          list_currency = col2.selectbox("Currency", options=currency_options, index=cur_index, key=f"list-cur-{cid}")
          submit_list = col3.form_submit_button("List / Update")
          submit_delist = col3.form_submit_button("Delist")
          if submit_list:
            try:
              resp = run_with_handler(
                seller_party,
                lambda h: h.list_for_sale_async(contract_id=cid, price=list_price, currency=list_currency),
              )
              st.success("Listed for sale")
              st.json(resp)
            except Exception as ex:
              traceback.print_exc(file=sys.stderr)
              st.error(f"ListForSale failed: {ex}")
          if submit_delist:
            try:
              resp = run_with_handler(
                seller_party,
                lambda h: h.delist_property_async(contract_id=cid),
              )
              st.success("Delisted")
              st.json(resp)
            except Exception as ex:
              traceback.print_exc(file=sys.stderr)
              st.error(f"Delist failed: {ex}")

with tab_buyer:
  st.markdown("#### Buyer workspace")
  buyer_party = select_party("Buyer party", current_party(), "buyer-party", known_party_ids)
  buyer_cash = load_cash(buyer_party)
  wallet_cols = st.columns(2)
  with wallet_cols[0]:
    st.markdown("Wallet")
    if not buyer_cash:
      st.info("Wallet is empty. Mint cash first.")
      if not known_party_ids:
        st.info("Tip: register parties in the Registrar tab, then select them from the dropdown.")
    else:
      st.table([
        {
          "cid": c["contractId"],
          "amount": c["payload"].get("amount"),
          "currency": c["payload"].get("currency"),
          "issuer": c["payload"].get("issuer"),
        }
        for c in buyer_cash
      ])
  with wallet_cols[1]:
    st.markdown("Mint cash")
    issuer = select_party("Issuer (usually seller)", "Seller", "mint-issuer", known_party_ids)
    mint_amount = st.text_input("Amount", value="500000.0", key="mint-amount")
    mint_currency = st.selectbox("Currency", options=["USD", "EUR", "GBP", "CHF"], index=0, key="mint-curr")
    if st.button("Mint cash", key="mint-btn"):
      try:
        resp = run_with_handler(
          buyer_party,
          lambda h: h.mint_cash_async(
            issuer=issuer,
            owner=buyer_party,
            amount=mint_amount,
            currency=mint_currency,
          ),
        )
        st.success("Cash minted")
        st.json(resp)
      except Exception as ex:
        traceback.print_exc(file=sys.stderr)
        st.error(f"Mint failed: {ex}")

  st.markdown("#### Marketplace")
  listings = [
    p for p in market_props
    if p.get("payload", {}).get("listed") and p.get("payload", {}).get("owner") != buyer_party
  ]
  if not listings:
    st.info("No listings. Ask a seller to list a property.")
  else:
    currency_filter = st.multiselect(
      "Filter by currency",
      options=sorted(list({p.get("payload", {}).get("currency", "") for p in listings})),
      default=[],
      key="market-filter",
    )
    filtered = [
      p for p in listings
      if not currency_filter or p.get("payload", {}).get("currency") in currency_filter
    ]
    for prop in filtered:
      cid = prop.get("contractId")
      payload = prop.get("payload", {})
      cols = st.columns([2, 2, 1, 1])
      cols[0].markdown(f"**{payload.get('propertyId')}** — {payload.get('address')}")
      cols[1].markdown(f"Type: {payload.get('propertyType')} | Area: {payload.get('area')}")
      cols[2].markdown(f"Price: {price_display(payload)}")
      cols[3].markdown(f"Owner: `{payload.get('owner')}`")

      eligible_cash = [
        c for c in buyer_cash
        if c["payload"].get("currency") == payload.get("currency")
        and str(c["payload"].get("amount")) == str(payload.get("price"))
      ]
      with st.form(f"buy-{cid}"):
        st.caption("Purchase: buyer + seller co-sign (cash + property)")
        seller_party = payload.get("owner")
        payment_cid = None
        if eligible_cash:
          payment_cid = st.selectbox(
            "Pick payment (exact amount)",
            options=[c["contractId"] for c in eligible_cash],
            format_func=lambda cid_opt: f"{cid_opt} ({eligible_cash[[c['contractId'] for c in eligible_cash].index(cid_opt)]['payload']['amount']} {payload.get('currency')})",
            key=f"pay-{cid}",
          )
        else:
          st.info("No matching cash: mint exact amount/currency first.")
        buy_btn = st.form_submit_button("Buy property")
        if buy_btn:
          if not payment_cid:
            st.error("Cash with exact price/currency is required.")
          else:
            try:
              resp = run_with_handler(
                buyer_party,
                lambda h: h.buy_property_async(
                  contract_id=cid,
                  price=str(payload.get("price", "")),
                  currency=payload.get("currency", "USD"),
                  buyer=buyer_party,
                  payment_cid=payment_cid,
                  seller=seller_party,
                ),
              )
              st.success("Trade completed, you are the owner")
              st.json(resp)
            except Exception as ex:
              traceback.print_exc(file=sys.stderr)
              st.error(f"Purchase failed: {ex}")
