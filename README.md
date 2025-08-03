# Moomoo P&L Dashboard (MPNL)

Moomoo P&L Dashboard is a simple website to view your overall Profit and Loss for securities, execute custom orders (both sell & buy orders) and providing alerting based on custom metrics.

This was created to supplement the Moomoo app's functionality.

Some of the errors I faced were:

1. There is no way to track your total Profit and Loss for securities which you have no position in (i.e. you have completely sold all shares of that stock.)

1. The total P&L shown on your Moomoo's accounts page also changes wildly when you add or remove funds from your account, and is not really reflective of your true P&L.

1. Some of the order types that I would want are not supported, such as a trailing-stop order with a minimum amount.

## Features

### Page showing overall profit/loss per stock ticker

![The MPNL dashboard](docs/dashboard.png)

### Sell page with custom sell order types

![A page showing various custom sell orders](docs/sell_orders.png)


### Buy page with custom buy order types

![A page showing various custom buy orders](docs/buy_orders.png)

### Notifications for custom alerts

Set up custom alerts to send push notifications to your phone via ntfy.sh. Some examples are for when the USD exchange rate changes, when the price of bitcoin changes, when there is news about your stock, etc.

![A sample notification on an Android device](docs/notification.png)


### Telemetry

This app has NO telemetry on its own, but services that it uses may capture/send data. We use a couple of services:

1. Moomoo
1. Ntfy.sh - we send notifications using this service, so you can expect that the data you send in custom alerts may be logged.

I wrote it for my own use, but you are heavily advised to dive into the source to verify yourself.


# Setup

You have to complete all of the tasks below to setup the application.

### Moomoo OpenD Client

We require the Moomoo OpenD client to interface with Moomoo (the Moomoo docs state that the API is not sufficient). A copy of the OpenD client is vendored with the repository, but you would probably want to download a copy straight from Moomoo for security.

It can be downloaded here (select OpenD client) for your operation system. 

https://www.moomoo.com/download/OpenAPI

Once downloaded, copy the OpenD client folder into the app.

---


### Using your credentials

You will need to update your Moomoo credentials and also credentials for this site. None of the data is captured, stored or sent as telemetry

```
SITE_MAIN_USER_USERNAME - The username used for HTTP basic auth for the sell/buy order page
SITE_MAIN_USER_PASSWORD - The password used for HTTP basic auth for the sell/buy order page


MOOMOO_ACCOUNT_ID       - Your moomoo account id more information here(https://www.moomoo.com/ca/support/topic10_24)
MOOMOO_PASSWORD         - Your moomoo account password
MOOMOO_TRADING_PASSWORD - The 6 digit password used for authorizing trades
```

Once you've done that, run `scripts/replace_moomoo_xml_details.py` to replace the Moomoo OpenD client config with your values. 

#### I don't want to run your script with my Moomoo account details!
If you did the above, you don't have to do this. This segment has more information about performing the changes manually. 

If you would rather change it manually, replace the values in the OpenD.xml file in the OpenD client folder with your Moomoo account credentials.

```
<api_port>11111</api_port>
<login_account>100000</login_account>
<login_pwd>123456</login_pwd>
```

---



### Running the web server


This project uses `uv` to manage python dependencies. Run the application and a webserver will start.

```bash
uv run python -m src.main
```

# Tests 

This project uses pytest for testing.

Run tests using `uv run pytest`

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
