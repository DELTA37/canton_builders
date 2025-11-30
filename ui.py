import asyncio
import os
from typing import Any, Dict, List

import streamlit as st

from python_client.client import DEFAULT_LEDGER_HOST, DEFAULT_LEDGER_PORT, RealEstateHandler

st.set_page_config(page_title="Real Estate Hub", layout="wide")

_CSS = """
<style>
.hero {
  padding: 20px 24px;
  border-radius: 14px;
  background: linear-gradient(120deg, #0f1b2d, #1b3c73);
  color: #f5f7ff;
  margin-bottom: 18px;
}
.hero__title {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}
.hero__subtitle {
  opacity: 0.85;
  margin-bottom: 10px;
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
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #e8ecf1;
  background: #ffffff;
  box-shadow: 0 6px 14px rgba(15, 27, 45, 0.05);
}
.section-title {
  font-size: 18px;
  margin-bottom: 6px;
  font-weight: 700;
}
.muted { color: #546478; font-size: 13px; }
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
  market_party = st.text_input("Обзор как (party)", value="Registrar")
  st.caption("Просмотр списка контрактов выполняется от имени выбранного party.")


# Session state for the active user
if "current_party" not in st.session_state:
  st.session_state["current_party"] = os.getenv("LEDGER_PARTY", "Buyer")


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
    st.error(f"Не удалось получить список контрактов: {ex}")
    return []


def load_parties(view_party: str) -> List[Dict[str, str]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_parties_async())
  except Exception as ex:
    st.error(f"Не удалось запросить список известных party: {ex}")
    return []


def load_cash(view_party: str) -> List[Dict[str, Any]]:
  try:
    return run_with_handler(view_party, lambda h: h.list_cash_async())
  except Exception as ex:
    st.error(f"Не удалось получить список кошелька: {ex}")
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
    <div class="hero__title">Real Estate Hub</div>
    <div class="hero__subtitle">Регистрация, вход, управление объектами и сделки на Canton</div>
    <div class="pill">Текущий пользователь: {current_party()}</div>
    <div class="pill">Ledger: {host}:{int(port)}</div>
    <div class="pill">Обзор как: {market_party}</div>
  </div>
  """,
  unsafe_allow_html=True,
)

# Auth & registration
auth_col, reg_col = st.columns(2)
with auth_col:
  st.markdown("#### Вход")
  login_party = st.text_input("Кто вы?", value=current_party(), key="login-party")
  if st.button("Сменить пользователя"):
    set_current_party(login_party)
    st.success(f"Текущий пользователь: {current_party()}")

  if st.button("Показать известные party"):
    parties = load_parties(market_party)
    if parties:
      st.table(parties)

with reg_col:
  st.markdown("#### Регистрация")
  new_party_hint = st.text_input("Имя/подсказка", value="NewUser")
  allocator_party = st.selectbox(
    "Allocate as (party with rights)",
    options=["Registrar", "Owner"],
    index=0,
  )
  auto_login = st.checkbox("Сделать новым текущим пользователем", value=True)
  if st.button("Зарегистрировать party"):
    try:
      created = run_with_handler(
        allocator_party,
        lambda handler: handler.allocate_parties_async([new_party_hint]),
      )
      if created:
        st.success(f"Создано: {', '.join(created)}")
        if auto_login:
          set_current_party(created[0])
      else:
        st.info("Party уже существовала, ничего не создали.")
    except Exception as ex:
      st.error(f"Не удалось создать party: {ex}")

# Load data for dashboard
all_props = load_properties(market_party)
my_props = [p for p in all_props if p.get("payload", {}).get("owner") == current_party()]
my_listed = [p for p in my_props if p.get("payload", {}).get("listed")]
market_props = [
  p for p in all_props
  if p.get("payload", {}).get("listed") and p.get("payload", {}).get("owner") != current_party()
]
my_cash = load_cash(current_party())

st.markdown("### Панель")
stat_cols = st.columns(4)
stat_cols[0].metric("Моя недвижимость", len(my_props))
stat_cols[1].metric("Я продаю", len(my_listed))
stat_cols[2].metric("Доступно купить", len(market_props))
stat_cols[3].metric("Всего в обзоре", len(all_props))


tab_my, tab_market, tab_create = st.tabs(["Мои объекты", "Маркетплейс", "Создать объект"])
st.markdown("### Кошелёк")
wallet_cols = st.columns(2)
with wallet_cols[0]:
  if not my_cash:
    st.info("Кошелёк пуст. Выпустите наличные.")
  else:
    st.table([
      {
        "cid": c["contractId"],
        "amount": c["payload"].get("amount"),
        "currency": c["payload"].get("currency"),
        "issuer": c["payload"].get("issuer"),
      }
      for c in my_cash
    ])
with wallet_cols[1]:
  st.markdown("**Выпустить наличные**")
  issuer = st.text_input("Issuer (обычно продавец)", value="Seller", key="mint-issuer")
  mint_owner = st.text_input("Owner", value=current_party(), key="mint-owner")
  mint_amount = st.text_input("Amount", value="500000.0")
  mint_currency = st.selectbox("Currency", options=["USD", "EUR", "GBP", "CHF"], index=0, key="mint-curr")
  if st.button("Mint cash"):
    try:
      resp = run_with_handler(
        mint_owner,
        lambda h: h.mint_cash_async(
          issuer=issuer,
          owner=mint_owner,
          amount=mint_amount,
          currency=mint_currency,
        ),
      )
      st.success("Кэш выпущен")
      st.json(resp)
    except Exception as ex:
      st.error(f"Mint failed: {ex}")

with tab_my:
  st.markdown("#### Мои объекты")
  if not my_props:
    st.info("У вас пока нет объектов. Создайте новый или купите готовый.")
  else:
    for prop in my_props:
      cid = prop.get("contractId")
      payload = prop.get("payload", {})
      header = f"{payload.get('propertyId')} — {payload.get('address')}"
      with st.expander(header, expanded=False):
        st.markdown(f"**ContractId:** `{cid}`")
        st.write(
          {
            "owner": payload.get("owner"),
            "propertyType": payload.get("propertyType"),
            "area": payload.get("area"),
            "price": price_display(payload),
            "listed": payload.get("listed"),
            "history": payload.get("history"),
            "status": payload.get("status"),
          }
        )

        with st.form(f"market-actions-{cid}"):
          col1, col2, col3 = st.columns([1, 1, 1])
          list_price = col1.text_input(
            "Цена, если продаем",
            value=str(payload.get("price", "")),
            key=f"list-price-{cid}",
          )
          currency_options = ["USD", "EUR", "GBP", "CHF"]
          cur_default = payload.get("currency", "USD")
          cur_index = currency_options.index(cur_default) if cur_default in currency_options else 0
          list_currency = col2.selectbox(
            "Валюта",
            options=currency_options,
            index=cur_index,
            key=f"list-cur-{cid}",
          )
          col3.markdown(" ")
          submit_list = col3.form_submit_button("Выставить / Обновить цену")
          submit_delist = col3.form_submit_button("Снять с продажи")

          if submit_list:
            try:
              resp = run_with_handler(
                current_party(),
                lambda h: h.list_for_sale_async(
                  contract_id=cid,
                  price=list_price,
                  currency=list_currency,
                ),
              )
              st.success("Обновили цену и выставили на продажу")
              st.json(resp)
            except Exception as ex:
              st.error(f"ListForSale failed: {ex}")

          if submit_delist:
            try:
              resp = run_with_handler(
                current_party(),
                lambda h: h.delist_property_async(contract_id=cid),
              )
              st.success("Сняли с продажи")
              st.json(resp)
            except Exception as ex:
              st.error(f"Delist failed: {ex}")

with tab_market:
  st.markdown("#### Маркетплейс: на продаже")
  if not market_props:
    st.info("Нет активных объявлений. Попросите владельца выставить объект.")
  else:
    currency_filter = st.multiselect(
      "Фильтр по валюте",
      options=sorted(list({p.get("payload", {}).get("currency", "") for p in market_props})),
      default=[],
    )
    filtered = [
      p for p in market_props
      if not currency_filter or p.get("payload", {}).get("currency") in currency_filter
    ]
    for prop in filtered:
      cid = prop.get("contractId")
      payload = prop.get("payload", {})
      card = st.container()
      with card:
        cols = st.columns([2, 2, 1, 1])
        cols[0].markdown(f"**{payload.get('propertyId')}** — {payload.get('address')}")
        cols[1].markdown(f"Тип: {payload.get('propertyType')} | Площадь: {payload.get('area')}")
        cols[2].markdown(f"Цена: {price_display(payload)}")
        cols[3].markdown(f"Владелец: `{payload.get('owner')}`")

        eligible_cash = [
          c for c in my_cash
          if c["payload"].get("currency") == payload.get("currency")
          and str(c["payload"].get("amount")) == str(payload.get("price"))
        ]
        with st.form(f"buy-{cid}"):
          st.caption("Покупка: подписывает покупатель (владелец cash)")
          buyer_party = st.text_input("Покупатель (новый владелец)", value=current_party(), key=f"buyer-{cid}")
          seller_party = payload.get("owner")
          payment_cid = None
          if eligible_cash:
            payment_cid = st.selectbox(
              "Выберите оплату (точная сумма)",
              options=[c["contractId"] for c in eligible_cash],
              format_func=lambda cid_opt: f"{cid_opt} ({eligible_cash[[c['contractId'] for c in eligible_cash].index(cid_opt)]['payload']['amount']} {payload.get('currency')})",
              key=f"pay-{cid}",
            )
          else:
            st.info("Нет подходящих средств: выпустите Cash на нужную сумму и валюту.")
          buy_btn = st.form_submit_button("Купить")
          if buy_btn:
            if not payment_cid:
              st.error("Нужен Cash с точной ценой и валютой.")
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
                st.success("Сделка прошла, вы новый владелец")
                st.json(resp)
              except Exception as ex:
                st.error(f"Purchase failed: {ex}")

with tab_create:
  st.markdown("#### Создать новый объект")
  with st.form("create"):
    registrar = st.text_input("Registrar party", value="Registrar")
    owner = st.text_input("Owner party", value=current_party())
    property_id = st.text_input("Property ID", value="ID-UI-1")
    address = st.text_input("Address", value="Baker St 221b")
    property_type = st.text_input("Property type", value="apartment")
    area = st.text_input("Area (decimal)", value="72.5")
    meta_json = st.text_area("Meta JSON", value='{"address":"Baker St 221b","rooms":3}')
    price = st.text_input("Цена", value="500000.0")
    currency = st.selectbox("Валюта", options=["USD", "EUR", "GBP", "CHF"], index=0)
    listed = st.checkbox("Сразу выставить на продажу", value=False)
    submitted = st.form_submit_button("Создать")
    if submitted:
      try:
        resp = run_with_handler(
          registrar,
          lambda handler: handler.create_property_async(
            registrar=registrar,
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
        st.success("Создано")
        st.json(resp)
      except Exception as ex:
        st.error(f"Create failed: {ex}")
