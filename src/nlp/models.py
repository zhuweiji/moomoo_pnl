from sqlalchemy import Column, Integer, String, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from langextract.data import AlignmentStatus
import langextract as lx

from src.core.database import BaseModel
from src.core.utilities import get_logger

log = get_logger(__name__)


class Document(BaseModel):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    document_id = Column(String, unique=True, nullable=False)
    text = Column(String, nullable=False)
    additional_context = Column(String)

    # Relationships
    annotations = relationship("AnnotatedDocument", back_populates="document")

    @classmethod
    def from_langextract(cls, document: lx.data.Document) -> "Document":
        """Create a Document model instance from a langextract Document."""
        return cls(document_id=document.document_id, text=document.text, additional_context=document.additional_context)


class AnnotatedDocument(BaseModel):
    __tablename__ = "annotated_documents"

    id = Column(Integer, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False)
    text = Column(String)

    # Relationships
    document = relationship("Document", back_populates="annotations")
    extractions = relationship("Extraction", back_populates="annotated_document")

    @classmethod
    def from_langextract(cls, document: lx.data.AnnotatedDocument) -> "AnnotatedDocument":
        """Create an AnnotatedDocument model instance from a langextract AnnotatedDocument."""
        instance = cls(document_id=document.document_id, text=document.text)
        if document.extractions:
            instance.extractions = [Extraction.from_langextract(extraction) for extraction in document.extractions]
        return instance


class CharInterval(BaseModel):
    __tablename__ = "char_intervals"

    id = Column(Integer, primary_key=True)
    start_pos = Column(Integer)
    end_pos = Column(Integer)
    extraction_id = Column(Integer, ForeignKey("extractions.id"))

    # Relationships
    extraction = relationship("Extraction", back_populates="char_interval")

    @classmethod
    def from_langextract(cls, char_interval: lx.data.CharInterval) -> "CharInterval":
        """Create a CharInterval model instance from a langextract CharInterval."""
        return cls(start_pos=char_interval.start_pos, end_pos=char_interval.end_pos)


class Extraction(BaseModel):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True)
    extraction_class = Column(String, nullable=False)
    extraction_text = Column(String, nullable=False)
    alignment_status = Column(Enum(AlignmentStatus))
    extraction_index = Column(Integer)
    group_index = Column(Integer)
    description = Column(String)
    attributes = Column(JSON)
    annotated_document_id = Column(Integer, ForeignKey("annotated_documents.id"))

    # Relationships
    char_interval = relationship("CharInterval", back_populates="extraction", uselist=False)
    annotated_document = relationship("AnnotatedDocument", back_populates="extractions")

    @classmethod
    def from_langextract(cls, extraction: lx.data.Extraction) -> "Extraction":
        """Create an Extraction model instance from a langextract Extraction."""
        instance = cls(
            extraction_class=extraction.extraction_class,
            extraction_text=extraction.extraction_text,
            alignment_status=extraction.alignment_status,
            extraction_index=extraction.extraction_index,
            group_index=extraction.group_index,
            description=extraction.description,
            attributes=extraction.attributes,
        )

        if extraction.char_interval:
            instance.char_interval = CharInterval.from_langextract(extraction.char_interval)

        return instance
