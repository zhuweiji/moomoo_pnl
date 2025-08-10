import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import langextract as lx
from langextract.data import AlignmentStatus

from src.core.database import BaseModel
from src.nlp.repositories import (
    DocumentRepository,
    AnnotatedDocumentRepository,
    ExtractionRepository,
    CharIntervalRepository,
)
from src.nlp.models import Document, AnnotatedDocument, Extraction, CharInterval

from src.core.utilities import get_logger

log = get_logger(__name__)


@pytest.fixture(scope="function")
def engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    BaseModel.metadata.create_all(engine)
    yield engine
    BaseModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def document_repo(session):
    return DocumentRepository(session)


@pytest.fixture
def annotated_document_repo(session):
    return AnnotatedDocumentRepository(session)


@pytest.fixture
def extraction_repo(session):
    return ExtractionRepository(session)


@pytest.fixture
def char_interval_repo(session):
    return CharIntervalRepository(session)


class TestDocumentRepository:
    def test_create_document(self, document_repo):
        doc = document_repo.create(document_id="doc_123", text="test document", additional_context="test context")

        assert doc.document_id == "doc_123"
        assert doc.text == "test document"
        assert doc.additional_context == "test context"

    def test_get_by_id(self, document_repo):
        doc = document_repo.create(document_id="doc_123", text="test document")

        retrieved_doc = document_repo.get_by_id("doc_123")
        assert retrieved_doc.document_id == doc.document_id
        assert retrieved_doc.text == doc.text

    def test_get_all(self, document_repo):
        doc1 = document_repo.create(document_id="doc_1", text="test 1")
        doc2 = document_repo.create(document_id="doc_2", text="test 2")

        docs = document_repo.get_all()
        assert len(docs) == 2
        assert {doc.document_id for doc in docs} == {"doc_1", "doc_2"}


class TestAnnotatedDocumentRepository:
    def test_create_annotated_document(self, annotated_document_repo, document_repo):
        # Create parent document first
        document_repo.create(document_id="doc_123", text="test document")

        anno_doc = annotated_document_repo.create(document_id="doc_123", text="annotated text")

        assert anno_doc.document_id == "doc_123"
        assert anno_doc.text == "annotated text"

    def test_get_by_document_id(self, annotated_document_repo, document_repo):
        document_repo.create(document_id="doc_123", text="test document")
        anno_doc = annotated_document_repo.create(document_id="doc_123")

        retrieved = annotated_document_repo.get_by_document_id("doc_123")
        assert retrieved.document_id == anno_doc.document_id


class TestExtractionRepository:
    def test_create_extraction(self, extraction_repo, annotated_document_repo, document_repo):
        # Setup parent documents
        document_repo.create(document_id="doc_123", text="test document")
        anno_doc = annotated_document_repo.create(document_id="doc_123")

        extraction = extraction_repo.create(
            extraction_class="test_class",
            extraction_text="test extraction",
            annotated_document_id=anno_doc.id,
            alignment_status=AlignmentStatus.MATCH_EXACT.name,
            extraction_index=1,
            group_index=1,
            description="test description",
            attributes={"key": "value"},
        )

        assert extraction.extraction_class == "test_class"
        assert extraction.extraction_text == "test extraction"
        assert extraction.annotated_document_id == anno_doc.id

    def test_get_by_annotated_document_id(self, extraction_repo, annotated_document_repo, document_repo):
        document_repo.create(document_id="doc_123", text="test document")
        anno_doc = annotated_document_repo.create(document_id="doc_123")

        extraction1 = extraction_repo.create(extraction_class="class1", extraction_text="text1", annotated_document_id=anno_doc.id)
        extraction2 = extraction_repo.create(extraction_class="class2", extraction_text="text2", annotated_document_id=anno_doc.id)

        extractions = extraction_repo.get_by_annotated_document_id(anno_doc.id)
        assert len(extractions) == 2
        assert {e.extraction_class for e in extractions} == {"class1", "class2"}


class TestCharIntervalRepository:
    def test_create_char_interval(self, char_interval_repo, extraction_repo, annotated_document_repo, document_repo):
        # Setup parent documents and extraction
        document_repo.create(document_id="doc_123", text="test document")
        anno_doc = annotated_document_repo.create(document_id="doc_123")
        extraction = extraction_repo.create(extraction_class="test_class", extraction_text="test extraction", annotated_document_id=anno_doc.id)

        char_interval = char_interval_repo.create(extraction_id=extraction.id, start_pos=0, end_pos=10)

        assert char_interval.extraction_id == extraction.id
        assert char_interval.start_pos == 0
        assert char_interval.end_pos == 10

    def test_get_by_extraction_id(self, char_interval_repo, extraction_repo, annotated_document_repo, document_repo):
        document_repo.create(document_id="doc_123", text="test document")
        anno_doc = annotated_document_repo.create(document_id="doc_123")
        extraction = extraction_repo.create(extraction_class="test_class", extraction_text="test extraction", annotated_document_id=anno_doc.id)

        char_interval = char_interval_repo.create(extraction_id=extraction.id, start_pos=0, end_pos=10)

        retrieved = char_interval_repo.get_by_extraction_id(extraction.id)
        assert retrieved.start_pos == char_interval.start_pos
        assert retrieved.end_pos == char_interval.end_pos
