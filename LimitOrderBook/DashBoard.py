from Modelling import OrderBook, DollarsAndShares, PriceSizePairs
import streamlit as st
import plotly.express as px

from numpy.random import normal


@st.cache
def initialize_order_book():
    bids: PriceSizePairs = [DollarsAndShares(
        dollars=x,
        shares=round(normal(100, 25))
    ) for x in range(100, 90, -1)]
    asks: PriceSizePairs = [DollarsAndShares(
        dollars=x,
        shares=round(normal(100, 20))
    ) for x in range(105, 115, 1)]

    ob: OrderBook = OrderBook(descending_bids=bids, ascending_asks=asks)

    return ob

def send_order(ob, side, typ, price, qty):
    if side == "Bid":
        if typ == "Limit":
            ob.buy_limit_order(price, qty)
        else:
            ob.buy_market_order(qty)
    else:
        if typ == "Limit":
            ob.sell_limit_order(price, qty)
        else:
            ob.sell_market_order(qty) 
    return ob

########
st.set_page_config(layout="wide")

st.title("Limit Order Book")
ob = initialize_order_book()
col1, col2 = st.beta_columns([3, 2])
with col1:
    st.plotly_chart(ob.plot_summary(), use_container_width = True)
    st.plotly_chart(ob.plot_order_book(),  use_container_width = True)

with col2: 
    st.subheader("Modify Book")
    with st.form("Order"):
        side = st.selectbox("Side", ["Bid", "Ask"])
        typ = st.selectbox("Type", ["Limit", "Market"])
        mid = ob.mid_price()
        price = st.slider("Price", 0.9*mid, 1.1*mid)
        qty = st.slider("Qty", 1, 5_000)
        st.form_submit_button("Send Order", on_click = send_order, args=(ob, side, typ, price, qty,))
        
        







    