from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.core.database.repository import BaseRepository
from src.core.utilities import JsonFileRepository
from src.core.utilities.logger import get_logger

from .models import FinancialNewsItem, FinancialNewsItemModel, NewsSourceModel

log = get_logger(__name__)


# this thing can be replaced soon - the database model has been implemented
class FinancialNewsItemJsonFileRepository(JsonFileRepository[FinancialNewsItem]):
    pass


class NewsSourceRepository(BaseRepository):
    def get_by_name(self, name: str) -> NewsSourceModel | None:
        try:
            stmt = select(NewsSourceModel).where(NewsSourceModel.name == name)
            result = self.session.execute(stmt).scalar_one_or_none()
            return result
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error getting news source: {str(e)}")
            raise

    def create(self, name: str) -> NewsSourceModel:
        try:
            source = NewsSourceModel(name=name)
            self.session.add(source)
            self.session.commit()
            return source
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating news source: {str(e)}")
            raise

    def get_or_create(self, name: str) -> NewsSourceModel:
        source = self.get_by_name(name)
        if not source:
            source = self.create(name)
        return source


class FinancialNewsItemModelRepository(BaseRepository):
    def create_from_model(self, object: FinancialNewsItemModel):
        try:
            self.session.add(object)
            self.session.commit()
            return object
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating char interval: {str(e)}")
            raise

    def get_by_source(self, source_name: str):
        try:
            stmt = select(FinancialNewsItemModel).join(NewsSourceModel).where(NewsSourceModel.name == source_name)
            result = self.session.execute(stmt).scalars().all()
            return result
        except SQLAlchemyError as e:
            log.error(f"Error getting news items by source: {str(e)}")
            raise
