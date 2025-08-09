from src.core.utilities import JsonFileRepository
from .models import FinancialNewsItem


class FinancialNewItemJsonFileRepository(JsonFileRepository[FinancialNewsItem]):
    pass
