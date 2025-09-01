from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.core.database import BaseRepository
from src.core.utilities import JsonFileRepository
from src.core.utilities.logger import get_logger

from .models import FinancialNewsItem, FinancialNewsItemModel, NewsSourceModel

log = get_logger(__name__)


# this thing can be replaced soon - the database model has been implemented
class FinancialNewsItemJsonFileRepository(JsonFileRepository[FinancialNewsItem]):
    pass


class NewsSourceRepository(BaseRepository):
    @classmethod
    def get_by_name(cls, name: str, session: Session) -> NewsSourceModel | None:
        try:
            stmt = select(NewsSourceModel).where(NewsSourceModel.name == name)
            result = session.execute(stmt).scalar_one_or_none()
            return result
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error getting news source: {str(e)}")
            raise

    @classmethod
    def create(cls, name: str, session: Session) -> NewsSourceModel:
        try:
            source = NewsSourceModel(name=name)
            session.add(source)
            session.commit()
            return source
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error creating news source: {str(e)}")
            raise

    @classmethod
    def get_or_create(cls, name: str, session: Session) -> NewsSourceModel:
        source = cls.get_by_name(name, session=session)
        if not source:
            source = cls.create(name, session=session)
        return source


class FinancialNewsItemModelRepository(BaseRepository):
    @classmethod
    def create_from_model(cls, object: FinancialNewsItemModel, session: Session):
        try:
            session.add(object)
            session.commit()
            return object
        except SQLAlchemyError as e:
            session.rollback()
            log.error(f"Error creating char interval: {str(e)}")
            raise

    @classmethod
    def get_by_source(cls, source_name: str, session: Session):
        try:
            stmt = select(FinancialNewsItemModel).join(NewsSourceModel).where(NewsSourceModel.name == source_name)
            result = session.execute(stmt).scalars().all()
            return result
        except SQLAlchemyError as e:
            log.error(f"Error getting news items by source: {str(e)}")
            raise
