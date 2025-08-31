from langextract.data import AlignmentStatus

from src.core.utilities import get_logger
from src.financial_news.nlp.models import ExtractionModel
from src.financial_news.nlp.repositories import (
    AnnotatedDocumentRepository,
    CharIntervalRepository,
    DocumentRepository,
    ExtractionRepository,
    LanguageExtractionExampleRepository,
    LanguageExtractionJobTypeRepository,
)

log = get_logger(__name__)


class TestDocumentRepository:
    def test_create_document(self, db_session):
        doc = DocumentRepository.create(document_id="doc_123", text="test document", additional_context="test context", session=db_session)

        assert doc.document_id == "doc_123"
        assert doc.text == "test document"
        assert doc.additional_context == "test context"

    def test_get_by_id(self, db_session):
        doc = DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)

        retrieved_doc = DocumentRepository.get_by_id("doc_123", session=db_session)
        assert retrieved_doc
        assert retrieved_doc.document_id == doc.document_id
        assert retrieved_doc.text == doc.text

    def test_get_all(self, db_session):
        doc1 = DocumentRepository.create(document_id="doc_1", text="test 1", session=db_session)
        doc2 = DocumentRepository.create(document_id="doc_2", text="test 2", session=db_session)

        docs = DocumentRepository.get_all(session=db_session)
        assert len(docs) == 2
        assert {doc.document_id for doc in docs} == {"doc_1", "doc_2"}


class TestAnnotatedDocumentRepository:
    def test_create_annotated_document(self, db_session):
        # Create parent document first
        DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)
        anno_doc = AnnotatedDocumentRepository.create(document_id="doc_123", text="annotated text", session=db_session)

        assert anno_doc.document_id == "doc_123"
        assert anno_doc.text == "annotated text"

    def test_get_by_document_id(self, db_session):
        DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)
        anno_doc = AnnotatedDocumentRepository.create(document_id="doc_123", session=db_session)

        retrieved = AnnotatedDocumentRepository.get_by_document_id("doc_123", session=db_session)
        assert retrieved
        assert retrieved.document_id == anno_doc.document_id


class TestExtractionRepository:
    def test_create_extraction(self, db_session):
        # Setup parent documents
        DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)
        anno_doc = AnnotatedDocumentRepository.create(document_id="doc_123", session=db_session)

        extraction = ExtractionRepository.create(
            extraction_class="test_class",
            extraction_text="test extraction",
            annotated_document_id=anno_doc.id,
            alignment_status=AlignmentStatus.MATCH_EXACT.name,
            extraction_index=1,
            group_index=1,
            description="test description",
            attributes={"key": "value"},
            session=db_session,
        )

        assert extraction.extraction_class == "test_class"
        assert extraction.extraction_text == "test extraction"
        assert extraction.annotated_document_id == anno_doc.id

    def test_get_by_annotated_document_id(self, db_session):
        DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)
        anno_doc = AnnotatedDocumentRepository.create(document_id="doc_123", session=db_session)

        ExtractionRepository.create(extraction_class="class1", extraction_text="text1", annotated_document_id=anno_doc.id, session=db_session)
        ExtractionRepository.create(extraction_class="class2", extraction_text="text2", annotated_document_id=anno_doc.id, session=db_session)

        extractions = ExtractionRepository.get_by_annotated_document_id(anno_doc.id, session=db_session)
        assert len(extractions) == 2
        assert {e.extraction_class for e in extractions} == {"class1", "class2"}


class TestCharIntervalRepository:
    def test_create_char_interval(self, db_session):
        # Setup parent documents and extraction
        DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)
        anno_doc = AnnotatedDocumentRepository.create(document_id="doc_123", session=db_session)
        extraction = ExtractionRepository.create(
            extraction_class="test_class", extraction_text="test extraction", annotated_document_id=anno_doc.id, session=db_session
        )

        char_interval = CharIntervalRepository.create(extraction_id=extraction.id, start_pos=0, end_pos=10, session=db_session)

        assert char_interval.extraction_id == extraction.id
        assert char_interval.start_pos == 0
        assert char_interval.end_pos == 10

    def test_get_by_extraction_id(self, db_session):
        DocumentRepository.create(document_id="doc_123", text="test document", session=db_session)
        anno_doc = AnnotatedDocumentRepository.create(document_id="doc_123", session=db_session)
        extraction = ExtractionRepository.create(
            extraction_class="test_class", extraction_text="test extraction", annotated_document_id=anno_doc.id, session=db_session
        )

        char_interval = CharIntervalRepository.create(extraction_id=extraction.id, start_pos=0, end_pos=10, session=db_session)

        retrieved = CharIntervalRepository.get_by_extraction_id(extraction.id, session=db_session)

        assert retrieved
        assert retrieved.start_pos == char_interval.start_pos
        assert retrieved.end_pos == char_interval.end_pos


class TestLanguageExtractionJobTypeRepository:
    def test_create_job_type(self, db_session):
        job_type = LanguageExtractionJobTypeRepository.create(name="test_job", prompt="Test prompt", session=db_session)

        assert job_type.name == "test_job"
        assert job_type.prompt == "Test prompt"

    def test_get_by_name(self, db_session):
        created = LanguageExtractionJobTypeRepository.create(name="test_job", prompt="Test prompt", session=db_session)

        retrieved = LanguageExtractionJobTypeRepository.get_by_name("test_job", session=db_session)

        assert retrieved
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.prompt == created.prompt

    def test_get_all(self, db_session):
        LanguageExtractionJobTypeRepository.create(name="job1", prompt="prompt1", session=db_session)
        LanguageExtractionJobTypeRepository.create(name="job2", prompt="prompt2", session=db_session)

        jobs = LanguageExtractionJobTypeRepository.get_all(session=db_session)
        assert len(jobs) == 2
        assert {job.name for job in jobs} == {"job1", "job2"}


class TestLanguageExtractionExampleRepository:
    def test_create_example(self, db_session):
        # Create parent job type first
        job_type = LanguageExtractionJobTypeRepository.create(name="test_job", prompt="Test prompt", session=db_session)

        example = LanguageExtractionExampleRepository.create(text="example text", job_type_id=job_type.id, session=db_session)

        assert example.text == "example text"
        assert example.job_type_id == job_type.id

    def test_get_by_job_type_id(self, db_session):
        job_type = LanguageExtractionJobTypeRepository.create(name="test_job", prompt="Test prompt", session=db_session)

        LanguageExtractionExampleRepository.create(text="example1", job_type_id=job_type.id, session=db_session)
        LanguageExtractionExampleRepository.create(text="example2", job_type_id=job_type.id, session=db_session)

        examples = LanguageExtractionExampleRepository.get_by_job_type_id(job_type.id, session=db_session)
        assert len(examples) == 2
        assert {ex.text for ex in examples} == {"example1", "example2"}

    def test_create_with_extractions(self, db_session):
        job_type = LanguageExtractionJobTypeRepository.create(name="test_job", prompt="Test prompt", session=db_session)

        extraction = ExtractionModel(extraction_class="test_class", extraction_text="test extraction")

        example = LanguageExtractionExampleRepository.create(
            text="example text", job_type_id=job_type.id, extractions=[extraction], session=db_session
        )

        assert len(example.extractions) == 1
        assert example.extractions[0].extraction_class == "test_class"
        assert example.extractions[0].extraction_class == "test_class"
        assert example.extractions[0].extraction_class == "test_class"
