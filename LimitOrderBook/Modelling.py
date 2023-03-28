from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass, replace
from typing import Sequence, Tuple, Optional, List
import pandas as pd
import numpy as np
import streamlit as st


@dataclass(frozen=True)
class DollarsAndShares:

    dollars: float
    shares: int


PriceSizePairs = Sequence[DollarsAndShares]


@dataclass(frozen=True)
class OrderBook:

    descending_bids: PriceSizePairs
    ascending_asks: PriceSizePairs


    def bid_price(self) -> float:
        return self.descending_bids[0].dollars

    def ask_price(self) -> float:
        return self.ascending_asks[0].dollars

    def mid_price(self) -> float:
        return (self.bid_price() + self.ask_price()) / 2

    def bid_ask_spread(self) -> float:
        return self.ask_price() - self.bid_price()

    def market_depth(self) -> float:
        return self.ascending_asks[-1].dollars - \
            self.descending_bids[-1].dollars

    @staticmethod
    def eat_book(
        ps_pairs: PriceSizePairs,
        shares: int
    ) -> Tuple[DollarsAndShares, PriceSizePairs]:
        '''
        Returned DollarsAndShares represents the pair of
        dollars transacted and the number of shares transacted
        on ps_pairs (with number of shares transacted being less
        than or equal to the input shares).
        Returned PriceSizePairs represents the remainder of the
        ps_pairs after the transacted number of shares have eaten into
        the input ps_pairs.
        '''
        rem_shares: int = shares
        dollars: float = 0.
        for i, d_s in enumerate(ps_pairs):
            this_price: float = d_s.dollars
            this_shares: int = d_s.shares
            dollars += this_price * min(rem_shares, this_shares)
            if rem_shares < this_shares:
                return (
                    DollarsAndShares(dollars=dollars, shares=shares),
                    [DollarsAndShares(
                        dollars=this_price,
                        shares=this_shares - rem_shares
                    )] + list(ps_pairs[i+1:])
                )
            else:
                rem_shares -= this_shares

        return (
            DollarsAndShares(dollars=dollars, shares=shares - rem_shares),
            []
        )

    def sell_limit_order(self, price: float, shares: int) -> \
            Tuple[DollarsAndShares, OrderBook]:
        index: Optional[int] = next((i for i, d_s
                                     in enumerate(self.descending_bids)
                                     if d_s.dollars < price), None)
        eligible_bids: PriceSizePairs = self.descending_bids \
            if index is None else self.descending_bids[:index]
        ineligible_bids: PriceSizePairs = [] if index is None else \
            self.descending_bids[index:]

        d_s, rem_bids = OrderBook.eat_book(eligible_bids, shares)
        new_bids: PriceSizePairs = list(rem_bids) + list(ineligible_bids)
        rem_shares: int = shares - d_s.shares

        if rem_shares > 0:
            new_asks: List[DollarsAndShares] = list(self.ascending_asks)
            index1: Optional[int] = next((i for i, d_s
                                          in enumerate(new_asks)
                                          if d_s.dollars >= price), None)
            if index1 is None:
                new_asks.append(DollarsAndShares(
                    dollars=price,
                    shares=rem_shares
                ))
            elif new_asks[index1].dollars != price:
                new_asks.insert(index1, DollarsAndShares(
                    dollars=price,
                    shares=rem_shares
                ))
            else:
                new_asks[index1] = DollarsAndShares(
                    dollars=price,
                    shares=new_asks[index1].shares + rem_shares
                )
            return d_s, OrderBook(
                ascending_asks=new_asks,
                descending_bids=new_bids
            )
        else:
            return d_s, replace(
                self,
                descending_bids=new_bids
            )

    def sell_market_order(
        self,
        shares: int
    ) -> Tuple[DollarsAndShares, OrderBook]:
        d_s, rem_bids = OrderBook.eat_book(
            self.descending_bids,
            shares
        )
        return (d_s, replace(self, descending_bids=rem_bids))

    def buy_limit_order(self, price: float, shares: int) -> \
            Tuple[DollarsAndShares, OrderBook]:
        index: Optional[int] = next((i for i, d_s
                                     in enumerate(self.ascending_asks)
                                     if d_s.dollars > price), None)
        eligible_asks: PriceSizePairs = self.ascending_asks \
            if index is None else self.ascending_asks[:index]
        ineligible_asks: PriceSizePairs = [] if index is None else \
            self.ascending_asks[index:]

        d_s, rem_asks = OrderBook.eat_book(eligible_asks, shares)
        new_asks: PriceSizePairs = list(rem_asks) + list(ineligible_asks)
        rem_shares: int = shares - d_s.shares

        if rem_shares > 0:
            new_bids: List[DollarsAndShares] = list(self.descending_bids)
            index1: Optional[int] = next((i for i, d_s
                                          in enumerate(new_bids)
                                          if d_s.dollars <= price), None)
            if index1 is None:
                new_bids.append(DollarsAndShares(
                    dollars=price,
                    shares=rem_shares
                ))
            elif new_bids[index1].dollars != price:
                new_bids.insert(index1, DollarsAndShares(
                    dollars=price,
                    shares=rem_shares
                ))
            else:
                new_bids[index1] = DollarsAndShares(
                    dollars=price,
                    shares=new_bids[index1].shares + rem_shares
                )
            return d_s, replace(
                self,
                ascending_asks=new_asks,
                descending_bids=new_bids
            )
        else:
            return d_s, replace(
                self,
                ascending_asks=new_asks
            )

    def buy_market_order(
        self,
        shares: int
    ) -> Tuple[DollarsAndShares, OrderBook]:
        d_s, rem_asks = OrderBook.eat_book(
            self.ascending_asks,
            shares
        )
        return (d_s, replace(self, ascending_asks=rem_asks))

    def send_order(self, side, typ, price, qty):
        if side == "Bid":
            if typ == "Limit":
                self.buy_limit_order(price, qty)
            else:
                self.buy_market_order(qty)
        else:
            if typ == "Limit":
                self.sell_limit_order(price, qty)
            else:
                self.sell_market_order(qty) 
        return

    def order_book_dataframe(self):
        df = pd.DataFrame()
        bid_prices, bid_shares = np.array([(pair.dollars, pair.shares) for pair in self.descending_bids]).T
        ask_prices, ask_shares = np.array([(pair.dollars, pair.shares) for pair in self.ascending_asks]).T
        df["prices"] = np.concatenate((bid_prices, ask_prices))
        df["shares"] = np.concatenate((bid_shares, ask_shares))
        df["side"] = ["bid" if price < self.mid_price() else "ask" for price in df.prices]
        return df

    def plot_summary(self):
        fig = go.Figure()
        fig.add_hline(0, line_color = "black", layer = "below")
        fig.add_trace(go.Scatter(x = [self.bid_price()], y = [0], name = "Best Bid", marker = dict(color = "green")))
        fig.add_trace(go.Scatter(x = [self.mid_price()], y = [0], name = "Mid", marker = dict(color = "#636EFA")))
        fig.add_trace(go.Scatter(x = [self.k_vamp(4)], y = [0], name = "4-VAMP", marker = dict(color = "#FECB52")))
        fig.add_trace(go.Scatter(x = [self.ask_price()], y = [0], name = "Best Ask", marker = dict(color = "crimson")))

        
        fig.update_traces(marker_size=12)
        fig.update_yaxes(visible = False)
        fig.update_layout(xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=False),
                        autosize=False,
                        height=200, legend = dict(orientation = "h", y  = -1, x = 0.2), 
                        showlegend = True)
        return fig

    def plot_order_book(self):
        """First, transform the book in a DataFrame"""
        df = self.order_book_dataframe()
        fig = px.bar(df, x="prices", y="shares", color= "side", 
                     text="shares", color_discrete_map={"bid":"green", "ask": "crimson"})
        fig.update_xaxes(tickvals = df.prices, ticktext = df.prices)
        fig.update_layout(height = 300)
        return fig
    
    def k_vamp(self, k):
        """Return the mid point of the vwaps until the k depth"""
        df = self.order_book_dataframe()
        bid = df[df["side"] == "bid"].loc[:k]
        ask = df[df["side"] == "ask"].reset_index().iloc[:k]
        vwap_bid  = (np.cumsum(bid.shares * bid.prices) / np.cumsum(bid.shares))[k - 1]

        vwap_ask = (np.cumsum(ask.shares * ask.prices) / np.cumsum(ask.shares))[k - 1]

        return (vwap_ask + vwap_bid)/2

        
