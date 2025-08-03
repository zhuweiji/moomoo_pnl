"""Moomoo API client wrapper for trading operations."""

from typing import Any, Dict, Optional, Tuple

import pandas
from moomoo import RET_OK, OpenSecTradeContext, SecurityFirm, TrdMarket, TrdSide

from src.core.orders.models import CurrentPosition, HistoricalOrder
from src.core.utilities import get_logger
from src.core.utilities.datetime_utils import FIRST_ORDER_DATE, get_current_datetime

log = get_logger(__name__)


class MoomooClient:
    """Wrapper for Moomoo API operations."""

    @staticmethod
    def get_trade_context():
        """Get a configured trade context."""
        return OpenSecTradeContext(
            filter_trdmarket=TrdMarket.US,
            host="127.0.0.1",
            port=18091,
            security_firm=SecurityFirm.FUTUSG,
        )

    @classmethod
    def get_historical_orders_and_positions_untyped(
        cls,
    ) -> Tuple[Optional[Any], Optional[Dict]]:
        """Get historical orders and current positions."""
        with cls.get_trade_context() as trd_ctx:
            # Get historical orders
            result_order_query, orders_data = trd_ctx.history_order_list_query(start=FIRST_ORDER_DATE, end=get_current_datetime())

            # Get current positions
            result_position_query, positions_data = trd_ctx.position_list_query()

            if result_order_query == RET_OK and result_position_query == RET_OK and not isinstance(positions_data, str):
                # Create a dictionary of current positions for easy lookup
                positions_dict = {row["code"]: row for _, row in positions_data.iterrows()}
                return orders_data, positions_dict
            else:
                log.error(
                    "Error in retrieving data: %s %s",
                    f"Orders: {orders_data if result_order_query != RET_OK else 'OK'}",
                    f"Positions: {positions_data if result_position_query != RET_OK else 'OK'}",
                )
                return None, None

    @classmethod
    def get_historical_orders(cls):
        with cls.get_trade_context() as trd_ctx:
            result, orders_data = trd_ctx.history_order_list_query(start=FIRST_ORDER_DATE, end=get_current_datetime())

            if result == RET_OK and isinstance(orders_data, pandas.DataFrame):
                data_list = orders_data.to_dict(orient="records")
                return [HistoricalOrder(**i) for i in data_list]  # type: ignore
            else:
                log.error(
                    "Error in retrieving data: %s %s",
                    f"Orders: {orders_data if result != RET_OK else 'OK'}",
                )
                return None

    @classmethod
    def get_current_positions(cls):
        with cls.get_trade_context() as trd_ctx:
            result, positions_data = trd_ctx.position_list_query()

            if result == RET_OK and not isinstance(positions_data, str):
                data_list = positions_data.to_dict(orient="records")

                return [CurrentPosition(**i) for i in data_list]  # type: ignore
            else:
                log.error(
                    "Error in retrieving data: %s %s",
                    f"Orders: {positions_data if result != RET_OK else 'OK'}",
                )
                return None

    @staticmethod
    def calculate_pnl(orders, positions):
        pnl_dict = {}

        for _, order in orders.iterrows():
            code = order["code"]
            dealt_qty = order["dealt_qty"]
            dealt_avg_price = order["dealt_avg_price"]
            trd_side = order["trd_side"]

            if code not in pnl_dict:
                pnl_dict[code] = {
                    "total_buy": 0,
                    "total_sell": 0,
                    "net_quantity": 0,
                    "current_price": 0,
                    "closed_position_value": 0,
                    "current_position_value": 0,
                    "total_profit": 0,
                }
            if trd_side == TrdSide.BUY:
                pnl_dict[code]["total_buy"] += dealt_qty * dealt_avg_price
                pnl_dict[code]["net_quantity"] += dealt_qty
            elif trd_side == TrdSide.SELL:
                pnl_dict[code]["total_sell"] += dealt_qty * dealt_avg_price
                pnl_dict[code]["net_quantity"] -= dealt_qty

        for code in pnl_dict:
            pnl_dict[code]["closed_position_value"] = pnl_dict[code]["total_sell"] - pnl_dict[code]["total_buy"]

        # # Update with current position information
        for code, position in positions.items():
            if code in pnl_dict:
                pnl_dict[code]["current_price"] = position["nominal_price"]
                if pnl_dict[code]["net_quantity"]:
                    pnl_dict[code]["current_position_value"] = pnl_dict[code]["net_quantity"] * pnl_dict[code]["current_price"]

                    if not position["qty"] == pnl_dict[code]["net_quantity"]:
                        log.warning(
                            f"""Historical transaction quantity does not tally with current position quantity:
                            From transaction list : {pnl_dict[code]["net_quantity"]}
                            From current positions: {position["qty"]}"""
                        )

        for code in pnl_dict:
            pnl_dict[code]["total_profit"] = pnl_dict[code]["closed_position_value"] + pnl_dict[code]["current_position_value"]

            for k, v in pnl_dict[code].items():
                if isinstance(v, float):
                    pnl_dict[code][k] = round(v, 2)

        return pnl_dict
