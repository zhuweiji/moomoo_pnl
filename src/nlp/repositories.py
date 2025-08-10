from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError

from src.core.database import BaseRepository
from src.core.utilities import get_logger
from .models import Document, AnnotatedDocument, Extraction, CharInterval

log = get_logger(__name__)


class DocumentRepository(BaseRepository):
    def create(self, document_id: str, text: str, additional_context: Optional[str] = None) -> Document:
        try:
            document = Document(document_id=document_id, text=text, additional_context=additional_context)
            self.session.add(document)
            self.session.commit()
            return document
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating document: {str(e)}")
            raise

    def get_by_id(self, document_id: str) -> Optional[Document]:
        return self.session.query(Document).filter(Document.document_id == document_id).first()

    def get_all(self) -> List[Document]:
        return self.session.query(Document).all()


class AnnotatedDocumentRepository(BaseRepository):
    def create(self, document_id: str, text: Optional[str] = None) -> AnnotatedDocument:
        try:
            annotated_doc = AnnotatedDocument(document_id=document_id, text=text)
            self.session.add(annotated_doc)
            self.session.commit()
            return annotated_doc
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating annotated document: {str(e)}")
            raise

    def get_by_document_id(self, document_id: str) -> Optional[AnnotatedDocument]:
        return self.session.query(AnnotatedDocument).filter(AnnotatedDocument.document_id == document_id).first()

    def get_all(self) -> List[AnnotatedDocument]:
        return self.session.query(AnnotatedDocument).all()


class ExtractionRepository(BaseRepository):
    def create(
        self,
        extraction_class: str,
        extraction_text: str,
        annotated_document_id: int,
        alignment_status: Optional[str] = None,
        extraction_index: Optional[int] = None,
        group_index: Optional[int] = None,
        description: Optional[str] = None,
        attributes: Optional[dict] = None,
    ) -> Extraction:
        try:
            extraction = Extraction(
                extraction_class=extraction_class,
                extraction_text=extraction_text,
                annotated_document_id=annotated_document_id,
                alignment_status=alignment_status,
                extraction_index=extraction_index,
                group_index=group_index,
                description=description,
                attributes=attributes,
            )
            self.session.add(extraction)
            self.session.commit()
            return extraction
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating extraction: {str(e)}")
            raise

    def get_by_annotated_document_id(self, annotated_document_id: int) -> List[Extraction]:
        return self.session.query(Extraction).filter(Extraction.annotated_document_id == annotated_document_id).all()


class CharIntervalRepository(BaseRepository):
    def create(self, extraction_id: int, start_pos: Optional[int] = None, end_pos: Optional[int] = None) -> CharInterval:
        try:
            char_interval = CharInterval(extraction_id=extraction_id, start_pos=start_pos, end_pos=end_pos)
            self.session.add(char_interval)
            self.session.commit()
            return char_interval
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating char interval: {str(e)}")
            raise

    def get_by_extraction_id(self, extraction_id: int) -> Optional[CharInterval]:
        return self.session.query(CharInterval).filter(CharInterval.extraction_id == extraction_id).first()
