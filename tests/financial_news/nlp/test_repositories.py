import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import langextract as lx
from langextract.data import AlignmentStatus

from src.core.database import BaseModel
from src.financial_news.nlp.repositories import (
    DocumentRepository,
    AnnotatedDocumentRepository,
    ExtractionRepository,
    CharIntervalRepository,
    LanguageExtractionExampleRepository,
    LanguageExtractionJobTypeRepository,
)
from src.financial_news.nlp.models import DocumentModel, AnnotatedDocumentModel, ExtractionModel, CharIntervalModel

from src.core.utilities import get_logger

log = get_logger(__name__)


@pytest.fixture
def document_repo(db_session):
    return DocumentRepository(db_session)


@pytest.fixture
def annotated_document_repo(db_session):
    return AnnotatedDocumentRepository(db_session)


@pytest.fixture
def extraction_repo(db_session):
    return ExtractionRepository(db_session)


@pytest.fixture
def char_interval_repo(db_session):
    return CharIntervalRepository(db_session)


@pytest.fixture
def job_type_repo(db_session):
    return LanguageExtractionJobTypeRepository(db_session)


@pytest.fixture
def example_repo(db_session):
    return LanguageExtractionExampleRepository(db_session)


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


class TestLanguageExtractionJobTypeRepository:
    def test_create_job_type(self, job_type_repo):
        job_type = job_type_repo.create(name="test_job", prompt="Test prompt")

        assert job_type.name == "test_job"
        assert job_type.prompt == "Test prompt"

    def test_get_by_name(self, job_type_repo):
        created = job_type_repo.create(name="test_job", prompt="Test prompt")

        retrieved = job_type_repo.get_by_name("test_job")
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.prompt == created.prompt

    def test_get_all(self, job_type_repo):
        job_type_repo.create(name="job1", prompt="prompt1")
        job_type_repo.create(name="job2", prompt="prompt2")

        jobs = job_type_repo.get_all()
        assert len(jobs) == 2
        assert {job.name for job in jobs} == {"job1", "job2"}


class TestLanguageExtractionExampleRepository:
    def test_create_example(self, example_repo, job_type_repo):
        # Create parent job type first
        job_type = job_type_repo.create(name="test_job", prompt="Test prompt")

        example = example_repo.create(text="example text", job_type_id=job_type.id)

        assert example.text == "example text"
        assert example.job_type_id == job_type.id

    def test_get_by_job_type_id(self, example_repo, job_type_repo):
        job_type = job_type_repo.create(name="test_job", prompt="Test prompt")

        example_repo.create(text="example1", job_type_id=job_type.id)
        example_repo.create(text="example2", job_type_id=job_type.id)

        examples = example_repo.get_by_job_type_id(job_type.id)
        assert len(examples) == 2
        assert {ex.text for ex in examples} == {"example1", "example2"}

    def test_create_with_extractions(self, example_repo, job_type_repo, extraction_repo):
        job_type = job_type_repo.create(name="test_job", prompt="Test prompt")

        extraction = ExtractionModel(extraction_class="test_class", extraction_text="test extraction")

        example = example_repo.create(text="example text", job_type_id=job_type.id, extractions=[extraction])

        assert len(example.extractions) == 1
        assert example.extractions[0].extraction_class == "test_class"
