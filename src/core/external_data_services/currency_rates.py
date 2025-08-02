import requests


def get_usd_to_sgd_rate():
    """Get exchange rate from Frankfurter (completely free, no API key needed)"""
    url = "https://api.frankfurter.app/latest?from=USD&to=SGD"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "rates" in data and "SGD" in data["rates"]:
        return {
            "rate": data["rates"]["SGD"],
            "timestamp": data.get("date", "Unknown"),
        }


def get_usd_to_bitcoin_rate():
    url = "https://blockchain.info/ticker"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "USD" in data and "15m" in data["USD"]:
        return {
            "rate": data["USD"]["15m"],
        }


if __name__ == "__main__":
    print(get_usd_to_bitcoin_rate())
