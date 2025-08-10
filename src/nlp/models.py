from dataclasses import dataclass

import langextract as lx
from langextract.data import AlignmentStatus
from sqlalchemy import JSON, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.core.database import BaseModel, engine
from src.core.utilities import get_logger

log = get_logger(__name__)


class DocumentModel(BaseModel):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    document_id = Column(String, unique=True, nullable=False)
    text = Column(String, nullable=False)
    additional_context = Column(String)

    # Relationships
    annotations = relationship("AnnotatedDocumentModel", back_populates="document")

    @classmethod
    def from_langextract(cls, document: lx.data.Document) -> "DocumentModel":
        """Create a Document model instance from a langextract Document."""
        return cls(document_id=document.document_id, text=document.text, additional_context=document.additional_context)

    def to_langextract(self) -> lx.data.Document:
        """Convert this model instance to a langextract Document."""
        return lx.data.Document(text=str(self.text), document_id=str(self.document_id), additional_context=str(self.additional_context))


class AnnotatedDocumentModel(BaseModel):
    __tablename__ = "annotated_documents"

    id = Column(Integer, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False)
    text = Column(String)

    # Relationships
    document = relationship("DocumentModel", back_populates="annotations")
    extractions = relationship("ExtractionModel", back_populates="annotated_document")

    @classmethod
    def from_langextract(cls, document: lx.data.AnnotatedDocument) -> "AnnotatedDocumentModel":
        """Create an AnnotatedDocument model instance from a langextract AnnotatedDocument."""
        instance = cls(document_id=document.document_id, text=document.text)
        if document.extractions:
            instance.extractions = [ExtractionModel.from_langextract(extraction) for extraction in document.extractions]
        return instance

    def to_langextract(self) -> lx.data.AnnotatedDocument:
        """Convert this model instance to a langextract AnnotatedDocument."""
        extractions = None
        if self.extractions:
            extractions = [ext.to_langextract() for ext in self.extractions]

        return lx.data.AnnotatedDocument(document_id=str(self.document_id), text=str(self.text), extractions=extractions)


class CharIntervalModel(BaseModel):
    __tablename__ = "char_intervals"

    id = Column(Integer, primary_key=True)
    start_pos = Column(Integer)
    end_pos = Column(Integer)
    extraction_id = Column(Integer, ForeignKey("extractions.id"))

    # Relationships
    extraction = relationship("ExtractionModel", back_populates="char_interval")

    @classmethod
    def from_langextract(cls, char_interval: lx.data.CharInterval) -> "CharIntervalModel":
        """Create a CharInterval model instance from a langextract CharInterval."""
        return cls(start_pos=char_interval.start_pos, end_pos=char_interval.end_pos)

    def to_langextract(self) -> lx.data.CharInterval:
        """Convert this model instance to a langextract CharInterval."""
        return lx.data.CharInterval(start_pos=self.start_pos, end_pos=self.end_pos)  # type: ignore


class ExtractionModel(BaseModel):
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
    example_id = Column(Integer, ForeignKey("language_extraction_examples.id"))

    # Relationships
    char_interval = relationship("CharIntervalModel", back_populates="extraction", uselist=False)
    annotated_document = relationship("AnnotatedDocumentModel", back_populates="extractions")
    example = relationship("LanguageExtractionExampleModel", back_populates="extractions")

    @classmethod
    def from_langextract(cls, extraction: lx.data.Extraction) -> "ExtractionModel":
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
            instance.char_interval = CharIntervalModel.from_langextract(extraction.char_interval)

        return instance

    def to_langextract(self) -> lx.data.Extraction:
        """Convert this model instance to a langextract Extraction."""
        char_interval = self.char_interval.to_langextract() if self.char_interval else None

        return lx.data.Extraction(
            extraction_class=str(self.extraction_class),
            extraction_text=str(self.extraction_text),
            char_interval=char_interval,
            alignment_status=self.alignment_status,  # type: ignore
            extraction_index=self.extraction_index,  # type: ignore
            group_index=self.group_index,  # type: ignore
            description=self.description,  # type: ignore
            attributes=self.attributes,  # type: ignore
        )


class LanguageExtractionExampleModel(BaseModel):
    __tablename__ = "language_extraction_examples"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    job_type_id = Column(Integer, ForeignKey("language_extraction_job_types.id"))

    # Relationships
    job_type = relationship("LanguageExtractionJobTypeModel", back_populates="examples")
    extractions = relationship("ExtractionModel", back_populates="example")

    @classmethod
    def from_langextract(cls, example: lx.data.ExampleData) -> "LanguageExtractionExampleModel":
        """Create a LanguageExtractionExample model instance from a langextract ExampleData."""
        instance = cls(text=example.text)
        if example.extractions:
            instance.extractions = [ExtractionModel.from_langextract(ext) for ext in example.extractions]
        return instance

    def to_langextract(self) -> lx.data.ExampleData:
        """Convert this model instance to a langextract ExampleData."""
        extractions = None
        if self.extractions:
            extractions = [ext.to_langextract() for ext in self.extractions]

        return lx.data.ExampleData(text=str(self.text), extractions=extractions or [])


@dataclass(frozen=True)
class LanguageExtractionJobType:
    """A common model which combines a prompt + samples for a language extraction.

    For example, you can create an instance of this class when you want to run sentiment analysis,
    providing a prompt that is relevant to sentiment analysis, and then a high quality example as reference.

    Example
    ```
    prompt = "Extract characters, emotions, and relationships in order of appearance."
    "Use exact text for extractions. Do not paraphrase or overlap entities."
    "Provide meaningful attributes for each entity to add context"

    examples = [
    ExampleData(
        text="ROMEO. But soft! What light through yonder window breaks? It is the east, and Juliet is the sun.",
        extractions=[
            Extraction(extraction_class="character", extraction_text="ROMEO", attributes={"emotional_state": "wonder"}),
            Extraction(extraction_class="emotion", extraction_text="But soft!", attributes={"feeling": "gentle awe"}),
            Extraction(extraction_class="relationship", extraction_text="Juliet is the sun", attributes={"type": "metaphor"}),
        ],
    )]
    ```
    """

    prompt: str
    examples: list[lx.data.ExampleData]
    name: str = "UnnamedJobType"


class LanguageExtractionJobTypeModel(BaseModel):
    __tablename__ = "language_extraction_job_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, default="UnnamedJobType")
    prompt = Column(String, nullable=False)

    # Relationships
    examples = relationship("LanguageExtractionExampleModel", back_populates="job_type")

    @classmethod
    def from_dataclass(cls, job_type: LanguageExtractionJobType) -> "LanguageExtractionJobTypeModel":
        """Create a model instance from the dataclass."""
        instance = cls(name=job_type.name, prompt=job_type.prompt)
        if job_type.examples:
            instance.examples = [LanguageExtractionExampleModel.from_langextract(ex) for ex in job_type.examples]
        return instance

    def to_dataclass(self) -> LanguageExtractionJobType:
        """Convert this model instance to a LanguageExtractionJobType dataclass."""
        examples = []
        if self.examples:
            examples = [example.to_langextract() for example in self.examples]

        return LanguageExtractionJobType(prompt=str(self.prompt), name=str(self.name), examples=examples)


# target for alembic replacement
BaseModel.metadata.create_all(engine)
