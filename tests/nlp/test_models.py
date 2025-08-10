import pytest
from langextract.data import Document as LxDocument
from langextract.data import AnnotatedDocument as LxAnnotatedDocument
from langextract.data import Extraction as LxExtraction
from langextract.data import CharInterval as LxCharInterval
from langextract.data import AlignmentStatus
from langextract.data import ExampleData as LxExampleData

from src.nlp.models import (
    DocumentModel,
    AnnotatedDocumentModel,
    ExtractionModel,
    CharIntervalModel,
    LanguageExtractionExampleModel,
    LanguageExtractionJobType,
    LanguageExtractionJobTypeModel,
)


@pytest.fixture
def lx_char_interval():
    return LxCharInterval(start_pos=0, end_pos=10)


@pytest.fixture
def lx_extraction(lx_char_interval):
    return LxExtraction(
        extraction_class="test_class",
        extraction_text="test text",
        char_interval=lx_char_interval,
        alignment_status=AlignmentStatus.MATCH_EXACT,
        extraction_index=1,
        group_index=2,
        description="test description",
        attributes={"key": "value"},
    )


@pytest.fixture
def lx_document():
    return LxDocument(text="test document", document_id="doc_123", additional_context="test context")


@pytest.fixture
def lx_annotated_document(lx_extraction):
    return LxAnnotatedDocument(document_id="doc_123", text="test document", extractions=[lx_extraction])


@pytest.fixture
def lx_example_data(lx_extraction):
    from langextract.data import ExampleData

    return ExampleData(text="example text", extractions=[lx_extraction])


@pytest.fixture
def job_type_dataclass(lx_example_data):
    from src.nlp.models import LanguageExtractionJobType

    return LanguageExtractionJobType(name="test_job", prompt="test prompt", examples=[lx_example_data])


class TestDocument:
    def test_from_langextract(self, lx_document):
        document = DocumentModel.from_langextract(lx_document)

        assert document.document_id == lx_document.document_id
        assert document.text == lx_document.text
        assert document.additional_context == lx_document.additional_context

    def test_to_langextract(self, lx_document):
        document = DocumentModel.from_langextract(lx_document)
        converted = document.to_langextract()

        assert isinstance(converted, LxDocument)
        assert converted.document_id == lx_document.document_id
        assert converted.text == lx_document.text
        assert converted.additional_context == lx_document.additional_context


class TestAnnotatedDocument:
    def test_from_langextract(self, lx_annotated_document):
        annotated_doc = AnnotatedDocumentModel.from_langextract(lx_annotated_document)

        assert annotated_doc.document_id == lx_annotated_document.document_id
        assert annotated_doc.text == lx_annotated_document.text
        assert len(annotated_doc.extractions) == 1

        extraction = annotated_doc.extractions[0]
        lx_extraction = lx_annotated_document.extractions[0]
        assert extraction.extraction_class == lx_extraction.extraction_class
        assert extraction.extraction_text == lx_extraction.extraction_text

    def test_to_langextract(self, lx_annotated_document):
        annotated_doc = AnnotatedDocumentModel.from_langextract(lx_annotated_document)
        converted = annotated_doc.to_langextract()

        assert isinstance(converted, LxAnnotatedDocument)
        assert converted.document_id == lx_annotated_document.document_id
        assert converted.text == lx_annotated_document.text
        assert len(converted.extractions) == 1

        extraction = converted.extractions[0]
        original_extraction = lx_annotated_document.extractions[0]
        assert extraction.extraction_class == original_extraction.extraction_class
        assert extraction.extraction_text == original_extraction.extraction_text


class TestExtraction:
    def test_from_langextract(self, lx_extraction):
        extraction = ExtractionModel.from_langextract(lx_extraction)

        assert extraction.extraction_class == lx_extraction.extraction_class
        assert extraction.extraction_text == lx_extraction.extraction_text
        assert extraction.alignment_status == lx_extraction.alignment_status
        assert extraction.extraction_index == lx_extraction.extraction_index
        assert extraction.group_index == lx_extraction.group_index
        assert extraction.description == lx_extraction.description
        assert extraction.attributes == lx_extraction.attributes

        # Test char_interval relationship
        assert extraction.char_interval is not None
        assert extraction.char_interval.start_pos == lx_extraction.char_interval.start_pos
        assert extraction.char_interval.end_pos == lx_extraction.char_interval.end_pos

    def test_to_langextract(self, lx_extraction):
        extraction = ExtractionModel.from_langextract(lx_extraction)
        converted = extraction.to_langextract()

        assert isinstance(converted, LxExtraction)
        assert converted.extraction_class == lx_extraction.extraction_class
        assert converted.extraction_text == lx_extraction.extraction_text
        assert converted.alignment_status == lx_extraction.alignment_status
        assert converted.extraction_index == lx_extraction.extraction_index
        assert converted.group_index == lx_extraction.group_index
        assert converted.description == lx_extraction.description
        assert converted.attributes == lx_extraction.attributes

        # Test char_interval conversion
        assert converted.char_interval is not None
        assert converted.char_interval.start_pos == lx_extraction.char_interval.start_pos
        assert converted.char_interval.end_pos == lx_extraction.char_interval.end_pos


class TestCharInterval:
    def test_from_langextract(self, lx_char_interval):
        char_interval = CharIntervalModel.from_langextract(lx_char_interval)

        assert char_interval.start_pos == lx_char_interval.start_pos
        assert char_interval.end_pos == lx_char_interval.end_pos

    def test_to_langextract(self, lx_char_interval):
        char_interval = CharIntervalModel.from_langextract(lx_char_interval)
        converted = char_interval.to_langextract()

        assert isinstance(converted, LxCharInterval)
        assert converted.start_pos == lx_char_interval.start_pos
        assert converted.end_pos == lx_char_interval.end_pos


class TestLanguageExtractionExample:
    def test_from_langextract(self, lx_example_data):
        example = LanguageExtractionExampleModel.from_langextract(lx_example_data)

        assert example.text == lx_example_data.text
        assert len(example.extractions) == 1

    def test_to_langextract(self, lx_example_data):
        example = LanguageExtractionExampleModel.from_langextract(lx_example_data)
        converted = example.to_langextract()

        assert isinstance(converted, LxExampleData)
        assert converted.text == lx_example_data.text
        assert len(converted.extractions) == 1

        extraction = converted.extractions[0]
        original_extraction = lx_example_data.extractions[0]
        assert extraction.extraction_class == original_extraction.extraction_class
        assert extraction.extraction_text == original_extraction.extraction_text


class TestLanguageExtractionJobType:
    def test_from_dataclass(self, job_type_dataclass):
        model = LanguageExtractionJobTypeModel.from_dataclass(job_type_dataclass)

        assert model.name == job_type_dataclass.name
        assert model.prompt == job_type_dataclass.prompt
        assert len(model.examples) == 1

    def test_to_dataclass(self, job_type_dataclass):
        model = LanguageExtractionJobTypeModel.from_dataclass(job_type_dataclass)
        converted = model.to_dataclass()

        assert isinstance(converted, LanguageExtractionJobType)
        assert converted.name == job_type_dataclass.name
        assert converted.prompt == job_type_dataclass.prompt
        assert len(converted.examples) == 1

        example = converted.examples[0]
        original_example = job_type_dataclass.examples[0]
        assert example.text == original_example.text
        assert len(example.extractions) == len(original_example.extractions)
