import os

import streamlit as st

from client import (
  DEFAULT_LEDGER_HOST,
  DEFAULT_LEDGER_PORT,
  archive_property,
  create_property,
  list_properties,
  transfer_property,
  update_meta,
)

st.set_page_config(page_title="Real Estate Ledger", layout="wide")
st.title("Real Estate Ledger (dazl/gRPC)")

with st.sidebar:
  st.header("Connection")
  host = st.text_input("Ledger host", value=os.getenv("LEDGER_HOST", DEFAULT_LEDGER_HOST))
  port = st.number_input("Ledger port", value=int(os.getenv("LEDGER_PORT", str(DEFAULT_LEDGER_PORT))), step=1)
  st.caption("Defaults match `sandbox.conf` ledger-api (e.g., 26865).")

st.subheader("Create Property")
with st.form("create"):
  registrar = st.text_input("Registrar party", value="Registrar")
  owner = st.text_input("Owner party", value="Owner")
  property_id = st.text_input("Property ID", value="ID-UI-1")
  address = st.text_input("Address", value="Baker St 221b")
  property_type = st.text_input("Property type", value="apartment")
  area = st.text_input("Area (decimal)", value="72.5")
  meta_json = st.text_area("Meta JSON", value='{"address":"Baker St 221b","rooms":3}')
  submitted = st.form_submit_button("Create")
  if submitted:
    try:
      resp = create_property(
        registrar=registrar,
        owner=owner,
        property_id=property_id,
        address=address,
        property_type=property_type,
        area=area,
        meta_json=meta_json,
        host=host,
        port=int(port),
      )
      st.success("Created")
      st.json(resp)
    except Exception as ex:
      st.error(f"Create failed: {ex}")

st.subheader("Transfer Property")
with st.form("transfer"):
  cid = st.text_input("Contract ID")
  new_owner = st.text_input("New owner party", value="Buyer")
  transfer_party = st.text_input("Party (current owner)", value="Owner")
  submitted = st.form_submit_button("Transfer")
  if submitted:
    try:
      resp = transfer_property(cid, new_owner, party=transfer_party, host=host, port=int(port))
      st.success("Transferred")
      st.json(resp)
    except Exception as ex:
      st.error(f"Transfer failed: {ex}")

st.subheader("Update Metadata")
with st.form("update_meta"):
  cid_meta = st.text_input("Contract ID (meta)")
  new_meta_json = st.text_area("New Meta JSON", value='{"address":"Baker St 221b","rooms":4}')
  update_party = st.text_input("Party (current owner)", value="Buyer")
  submitted = st.form_submit_button("Update Meta")
  if submitted:
    try:
      resp = update_meta(cid_meta, new_meta_json, party=update_party, host=host, port=int(port))
      st.success("Updated meta")
      st.json(resp)
    except Exception as ex:
      st.error(f"Update failed: {ex}")

st.subheader("Archive Property")
with st.form("archive"):
  cid_archive = st.text_input("Contract ID (archive)")
  archive_party = st.text_input("Party (registrar)", value="Registrar")
  submitted = st.form_submit_button("Archive")
  if submitted:
    try:
      resp = archive_property(cid_archive, party=archive_party, host=host, port=int(port))
      st.success("Archived")
      st.json(resp)
    except Exception as ex:
      st.error(f"Archive failed: {ex}")

st.subheader("Active Properties")
list_party = st.text_input("Party for list", value="Registrar", key="list-party")
if st.button("Refresh"):
  try:
    resp = list_properties(party=list_party, host=host, port=int(port))
    st.json(resp)
  except Exception as ex:
    st.error(f"List failed: {ex}")
