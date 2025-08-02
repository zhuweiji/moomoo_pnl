# Global task service instance

from src.alerts.task_service import TaskService
from src.core.external_data_services.currency_rates import (
    get_usd_to_bitcoin_rate,
    get_usd_to_sgd_rate,
)
from src.core.external_data_services.stock_data.yfinance import get_stock_price
from src.core.utilities import get_logger

log = get_logger(__name__)

global_task_service = TaskService()

# registering the USD to bitcoin rate task
# global_task_service.register_task(
#     func=lambda: get_stock_price("US.ASTS"),
#     interval_seconds=60 * 60,  # one hour
#     condition=lambda result: result < 46,
#     name="ASTS less than $46",
#     alert_message="ASTS price:",
# )

log.info("Starting background tasks")
for task_id, task_config in global_task_service.tasks.items():
    log.info(f"Starting task: {task_config.name}")
    global_task_service.start_task(task_id)
