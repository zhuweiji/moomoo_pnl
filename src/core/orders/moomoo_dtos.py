from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class HistoricalOrder:
    """moomoo data object"""

    code: str
    stock_name: str

    trd_side: str
    order_type: str
    order_status: str
    order_id: str
    qty: float
    price: float
    create_time: str
    updated_time: str
    dealt_qty: float
    dealt_avg_price: float
    last_err_msg: Optional[str]  # Can be empty
    remark: Optional[str]  # Can be empty
    time_in_force: str
    fill_outside_rth: bool
    aux_price: Union[str, float]  # "N/A" or a float
    trail_type: str  # "N/A" or specific values
    trail_value: Union[str, float]  # "N/A" or a float
    trail_spread: Union[str, float]  # "N/A" or a float
    currency: str


@dataclass
class CurrentPosition:
    """moomoo data object"""

    code: str
    stock_name: str
    qty: float
    can_sell_qty: float
    cost_price: float
    cost_price_valid: bool
    market_val: float
    nominal_price: float
    pl_ratio: float
    pl_ratio_valid: bool
    pl_val: float
    pl_val_valid: bool
    today_buy_qty: float
    today_buy_val: float
    today_pl_val: float
    today_trd_val: float
    today_sell_qty: float
    today_sell_val: float
    position_side: str
    unrealized_pl: Union[str, float]  # N/A treated as str, or it could be float if parsed differently
    realized_pl: Union[str, float]  # Same as unrealized_pl
    currency: str

    position_market: str | None = None
    average_cost: float | None = None
    diluted_cost: float | None = None
    pl_ratio_avg_cost: float | None = None
