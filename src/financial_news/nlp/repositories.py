from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from src.core.database import BaseRepository
from src.core.utilities import get_logger

from .models import (
    AnnotatedDocumentModel,
    CharIntervalModel,
    DocumentModel,
    ExtractionModel,
    LanguageExtractionExampleModel,
    LanguageExtractionJobTypeModel,
)

log = get_logger(__name__)


class DocumentRepository(BaseRepository):
    def create(self, document_id: str, text: str, additional_context: Optional[str] = None) -> DocumentModel:
        try:
            document = DocumentModel(document_id=document_id, text=text, additional_context=additional_context)
            self.session.add(document)
            self.session.commit()
            return document
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating document: {str(e)}")
            raise

    def get_by_id(self, document_id: str) -> Optional[DocumentModel]:
        return self.session.query(DocumentModel).filter(DocumentModel.document_id == document_id).first()

    def get_all(self) -> List[DocumentModel]:
        return self.session.query(DocumentModel).all()


class AnnotatedDocumentRepository(BaseRepository):
    def create_with_relations(self, annotated_doc: AnnotatedDocumentModel) -> AnnotatedDocumentModel:
        """
        Persists an AnnotatedDocumentModel instance along with its related Extractions and CharIntervals.

        Args:
            annotated_doc: The AnnotatedDocumentModel instance to persist

        Returns:
            The persisted AnnotatedDocumentModel with all relations

        Raises:
            SQLAlchemyError: If there's an error during persistence
        """
        try:
            # First persist the annotated document
            self.session.add(annotated_doc)

            # If there are extractions, persist them
            if annotated_doc.extractions:
                for extraction in annotated_doc.extractions:
                    self.session.add(extraction)

                    # If the extraction has char_intervals, persist them
                    if extraction.char_interval:
                        self.session.add(extraction.char_interval)

            self.session.commit()
            return annotated_doc

        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error persisting annotated document with relations: {str(e)}")
            raise

    def create(self, document_id: str, text: Optional[str] = None) -> AnnotatedDocumentModel:
        try:
            annotated_doc = AnnotatedDocumentModel(document_id=document_id, text=text)
            self.session.add(annotated_doc)
            self.session.commit()
            return annotated_doc
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating annotated document: {str(e)}")
            raise

    def get_by_document_id(self, document_id: str) -> Optional[AnnotatedDocumentModel]:
        return self.session.query(AnnotatedDocumentModel).filter(AnnotatedDocumentModel.document_id == document_id).first()

    def get_all(self) -> List[AnnotatedDocumentModel]:
        return self.session.query(AnnotatedDocumentModel).all()


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
    ) -> ExtractionModel:
        try:
            extraction = ExtractionModel(
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

    def get_by_annotated_document_id(self, annotated_document_id: int) -> List[ExtractionModel]:
        return self.session.query(ExtractionModel).filter(ExtractionModel.annotated_document_id == annotated_document_id).all()


class CharIntervalRepository(BaseRepository):
    def create(self, extraction_id: int, start_pos: Optional[int] = None, end_pos: Optional[int] = None) -> CharIntervalModel:
        try:
            char_interval = CharIntervalModel(extraction_id=extraction_id, start_pos=start_pos, end_pos=end_pos)
            self.session.add(char_interval)
            self.session.commit()
            return char_interval
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating char interval: {str(e)}")
            raise

    def get_by_extraction_id(self, extraction_id: int) -> Optional[CharIntervalModel]:
        return self.session.query(CharIntervalModel).filter(CharIntervalModel.extraction_id == extraction_id).first()


class LanguageExtractionExampleRepository(BaseRepository):
    def create(self, text: str, job_type_id: int, extractions: Optional[List[ExtractionModel]] = None) -> LanguageExtractionExampleModel:
        try:
            example = LanguageExtractionExampleModel(text=text, job_type_id=job_type_id)
            if extractions:
                example.extractions = extractions

            self.session.add(example)
            self.session.commit()
            return example
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating language extraction example: {str(e)}")
            raise

    def get_by_job_type_id(self, job_type_id: int) -> List[LanguageExtractionExampleModel]:
        return self.session.query(LanguageExtractionExampleModel).filter(LanguageExtractionExampleModel.job_type_id == job_type_id).all()


class LanguageExtractionJobTypeRepository(BaseRepository):
    def create(self, name: str, prompt: str, examples: Optional[List[LanguageExtractionExampleModel]] = None) -> LanguageExtractionJobTypeModel:
        try:
            job_type = LanguageExtractionJobTypeModel(name=name, prompt=prompt)
            if examples:
                job_type.examples = examples

            self.session.add(job_type)
            self.session.commit()
            return job_type
        except SQLAlchemyError as e:
            self.session.rollback()
            log.error(f"Error creating language extraction job type: {str(e)}")
            raise

    def get_by_name(self, name: str) -> Optional[LanguageExtractionJobTypeModel]:
        return self.session.query(LanguageExtractionJobTypeModel).filter(LanguageExtractionJobTypeModel.name == name).first()

    def get_all(self) -> List[LanguageExtractionJobTypeModel]:
        return self.session.query(LanguageExtractionJobTypeModel).all()
