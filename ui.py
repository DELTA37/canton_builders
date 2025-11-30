import asyncio
import os
from typing import Any, Dict, List

import streamlit as st

from python_client.client import DEFAULT_LEDGER_HOST, DEFAULT_LEDGER_PORT, RealEstateHandler

st.set_page_config(page_title="Canton Real Estate", layout="wide")

_CSS = """
<style>
body {
  background: #0b1021;
}
.hero {
  padding: 22px 26px;
  border-radius: 16px;
  background: radial-gradient(circle at 10% 20%, #1f4b99 0, #0b1021 45%), linear-gradient(120deg, #0f1b2d, #0b1021);
  color: #f5f7ff;
  margin-bottom: 18px;
}
.hero__title {
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 6px;
  letter-spacing: -0.5px;
}
.hero__subtitle {
  opacity: 0.85;
  margin-bottom: 12px;
}
.pill {
  display: inline-block;
  padding: 6px 12px;
  margin-right: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
}
.card {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,0.08);
  background: #0f172a;
  color: #eef2ff;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
}
.section-title {
  font-size: 18px;
  margin-bottom: 6px;
  font-weight: 700;
  color: #e2e8f0;
}
.muted { color: #94a3b8; font-size: 13px; }
.chip {
  background: #1e293b;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  font-size: 12px;
  color: #cbd5f5;
}
.stat {
  background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 12px 14px;
  color: #e2e8f0;
}
.stat .label { font-size: 12px; color: #cbd5e1; }
.stat .value { font-size: 20px; font-weight: 800; }
.card-light {
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 14px 16px;
  color: #e2e8f0;
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
    st.error(f"Failed to load contracts: {ex}")
    return []


def load_parties(view_party: str) -> List[Dict[str, str]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_parties_async())
  except Exception as ex:
    st.error(f"Failed to load known parties: {ex}")
    return []


def load_cash(view_party: str) -> List[Dict[str, Any]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_cash_async())
  except Exception as ex:
    st.error(f"Failed to load wallet: {ex}")
    return []


def price_display(payload: Dict[str, Any]) -> str:
  price = payload.get("price")
  currency = payload.get("currency", "")
  if price is None or currency is None:
    return "-"
  return f"{price} {currency}"


st.markdown(
  f"""
  <div class="hero">
    <div class="hero__title">Canton Real Estate Hub</div>
    <div class="hero__subtitle">Registration, roles (Registrar / Seller / Buyer), trades and wallets</div>
    <div class="pill">Current user: {current_party()}</div>
    <div class="pill">Ledger: {host}:{int(port)}</div>
    <div class="pill">View as: {market_party}</div>
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
market_props = load_properties(market_party)
listed_props = [p for p in market_props if p.get("payload", {}).get("listed")]
stat_cols = st.columns(4)
stat_cols[0].markdown(f"<div class='stat'><div class='label'>Total properties (view)</div><div class='value'>{len(market_props)}</div></div>", unsafe_allow_html=True)
stat_cols[1].markdown(f"<div class='stat'><div class='label'>Listed for sale</div><div class='value'>{len(listed_props)}</div></div>", unsafe_allow_html=True)
stat_cols[2].markdown(f"<div class='stat'><div class='label'>Current role</div><div class='value'>{role}</div></div>", unsafe_allow_html=True)
stat_cols[3].markdown(f"<div class='stat'><div class='label'>View as</div><div class='value'>{market_party}</div></div>", unsafe_allow_html=True)

tab_registrar, tab_seller, tab_buyer = st.tabs(["Registrar", "Seller", "Buyer"])

with tab_registrar:
  st.markdown("#### Registration & registry")
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
      st.error(f"Failed to create party: {ex}")

  if st.button("List known parties", key="list-parties"):
    parties = load_parties(registrar_party)
    if parties:
      st.table(parties)

  st.markdown("#### Create property (as registrar)")
  with st.form("create-reg"):
    owner = st.text_input("Owner party", value="Owner", key="owner-create")
    property_id = st.text_input("Property ID", value="ID-UI-1")
    address = st.text_input("Address", value="Baker St 221b")
    property_type = st.text_input("Property type", value="apartment")
    area = st.text_input("Area (decimal)", value="72.5")
    meta_json = st.text_area("Meta JSON", value='{"address":"Baker St 221b","rooms":3}')
    price = st.text_input("Цена", value="500000.0")
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
        st.error(f"Create failed: {ex}")

with tab_seller:
  st.markdown("#### Seller workspace")
  seller_party = st.text_input("Seller party", value=current_party(), key="seller-party")
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
              st.error(f"Delist failed: {ex}")

with tab_buyer:
  st.markdown("#### Buyer workspace")
  buyer_party = st.text_input("Buyer party", value=current_party(), key="buyer-party")
  buyer_cash = load_cash(buyer_party)
  wallet_cols = st.columns(2)
  with wallet_cols[0]:
    st.markdown("Wallet")
    if not buyer_cash:
      st.info("Wallet is empty. Mint cash first.")
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
    issuer = st.text_input("Issuer (usually seller)", value="Seller", key="mint-issuer")
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
      cols[1].markdown(f"Тип: {payload.get('propertyType')} | Площадь: {payload.get('area')}")
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
              st.error(f"Purchase failed: {ex}")
