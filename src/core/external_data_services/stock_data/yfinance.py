import re

import yfinance as yf


def get_stock_price(stock_code: str):
    if country_code := re.findall("([a-zA-Z]+).[a-zA-Z]+", stock_code):
        country_code = country_code[0]
        if country_code != "US":
            raise ValueError("Only US stocks are supported at this time")
        stock_code = stock_code.replace(f"{country_code}.", "")
    try:
        ticker = yf.Ticker(stock_code)
        price = ticker.info.get("currentPrice")
        if price is None:
            raise ValueError(f"Could not get current price for {stock_code}")
        return price
    except Exception as e:
        raise ValueError(e)
