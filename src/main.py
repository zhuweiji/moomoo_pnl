"""Main entry point for the PnL application."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.moomoo_client import MoomooClient
from src.core.utilities import SITE_PORT, ensure_opend_running, get_logger
from src.routes.alerts import router as alert_router
from src.routes.orders import router as trailing_stop_router
from src.routes.positions import router as positions_router
from src.routes.stock_data import router as stock_data_router
from src.routes.utils import get_current_username

log = get_logger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()
security = HTTPBasic()

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class LogErrorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code >= 400:
            # Log error details
            log.error(f"Error: {response.status_code}, Path: {request.url.path}, Method: {request.method}, Headers: {dict(request.headers)}")
        return response


app.add_middleware(LogErrorsMiddleware)

# Include routers
app.include_router(trailing_stop_router, prefix="/api/trailing-stop", tags=["trailing-stop"])
app.include_router(positions_router, prefix="/api/positions", tags=["positions"])
app.include_router(stock_data_router, prefix="/api/stock-data", tags=["stock-data"])
app.include_router(alert_router, prefix="/api/alerts", tags=["alerts"])


# Register routes
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(f"{static_dir}/index.html", "r") as file:
        content = file.read()
    return content


@app.get("/sell_orders", response_class=HTMLResponse)
async def sell_orders_page(username: str = Depends(get_current_username)):
    with open(f"{static_dir}/sell-orders.html", "r") as file:
        content = file.read()
    return content


@app.get("/buy_orders", response_class=HTMLResponse)
async def buy_orders_page(username: str = Depends(get_current_username)):
    with open(f"{static_dir}/buy-orders.html", "r") as file:
        content = file.read()
    return content


@app.get("/sell-order-form", response_class=HTMLResponse)
async def order_form_page(username: str = Depends(get_current_username)):
    with open(f"{static_dir}/sell-order-form.html", "r") as file:
        content = file.read()
    return content


@app.get("/buy-order-form", response_class=HTMLResponse)
async def buy_order_form_page(username: str = Depends(get_current_username)):
    with open(f"{static_dir}/buy-order-form.html", "r") as file:
        content = file.read()
    return content


@app.get("/api/data")
async def data():
    orders, current_prices = MoomooClient.get_historical_orders_and_positions_untyped()
    if orders is not None and current_prices is not None:
        return MoomooClient.calculate_pnl(orders, current_prices)
    else:
        log.warning(f"unable to get data: {orders =}\n{current_prices =}")


@app.get("/.well-known/acme-challenge")
async def letsencrypt():
    return {"message": "hello!"}


if __name__ == "__main__":
    try:
        ensure_opend_running()
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=SITE_PORT)
    except Exception as e:
        log.exception(e)
    finally:
        exit(0)
