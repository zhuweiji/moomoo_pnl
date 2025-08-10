import pytest
from langextract.data import Document as LxDocument
from langextract.data import AnnotatedDocument as LxAnnotatedDocument
from langextract.data import Extraction as LxExtraction
from langextract.data import CharInterval as LxCharInterval
from langextract.data import AlignmentStatus

from src.nlp.models import Document, AnnotatedDocument, Extraction, CharInterval


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


class TestDocument:
    def test_from_langextract(self, lx_document):
        document = Document.from_langextract(lx_document)

        assert document.document_id == lx_document.document_id
        assert document.text == lx_document.text
        assert document.additional_context == lx_document.additional_context


class TestAnnotatedDocument:
    def test_from_langextract(self, lx_annotated_document):
        annotated_doc = AnnotatedDocument.from_langextract(lx_annotated_document)

        assert annotated_doc.document_id == lx_annotated_document.document_id
        assert annotated_doc.text == lx_annotated_document.text
        assert len(annotated_doc.extractions) == 1

        extraction = annotated_doc.extractions[0]
        lx_extraction = lx_annotated_document.extractions[0]
        assert extraction.extraction_class == lx_extraction.extraction_class
        assert extraction.extraction_text == lx_extraction.extraction_text


class TestExtraction:
    def test_from_langextract(self, lx_extraction):
        extraction = Extraction.from_langextract(lx_extraction)

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


class TestCharInterval:
    def test_from_langextract(self, lx_char_interval):
        char_interval = CharInterval.from_langextract(lx_char_interval)

        assert char_interval.start_pos == lx_char_interval.start_pos
        assert char_interval.end_pos == lx_char_interval.end_pos
