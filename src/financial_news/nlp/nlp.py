import textwrap
from dataclasses import dataclass
from pathlib import Path

import langextract as lx
from langextract.data import AnnotatedDocument, ExampleData, Extraction

from src.core.database import SessionMaker
from src.core.utilities import (
    DATA_DIR,
    EXTRACTION_RESULT_DIR,
    EXTRACTION_VISUALIZATION_DIR,
    LANGEXTRACT_MODEL,
    STRUCTURED_TEXT_DATA_DIR,
    datetime_iso8601_str,
    get_current_datetime,
    get_logger,
)

from .models import AnnotatedDocumentModel, LanguageExtractionJobType
from .repositories import AnnotatedDocumentRepository

log = get_logger(__name__)


def extract(input_text: str, job_type: LanguageExtractionJobType):
    repository = AnnotatedDocumentRepository(session=SessionMaker())

    prompt = textwrap.dedent(job_type.prompt)

    result: AnnotatedDocument = lx.extract(
        text_or_documents=input_text,
        prompt_description=prompt,
        examples=job_type.examples,
        model_id=LANGEXTRACT_MODEL,
    )  # type: ignore

    model = AnnotatedDocumentModel.from_langextract(result)
    repository.create_with_relations(model)

    save_visualization(result, job_type)

    print(result)


def save_visualization(extraction_result: AnnotatedDocument, job_type: LanguageExtractionJobType):
    output_filename = f"{job_type.name}-{get_current_datetime().replace(':', '-')}"

    extraction_text_result_filepath = EXTRACTION_RESULT_DIR / f"{output_filename}.jsonl"
    extraction_viz_filepath = EXTRACTION_VISUALIZATION_DIR / f"{output_filename}.html"

    extraction_text_result_filepath.write_text("")

    # Save the results to a JSONL file
    lx.io.save_annotated_documents(
        [extraction_result],  # type: ignore
        output_name=extraction_text_result_filepath.name,
        output_dir=extraction_text_result_filepath.parent,
    )

    # write as a html
    html_content = lx.visualize(extraction_text_result_filepath)
    extraction_viz_filepath.write_text(html_content, encoding="utf-8")

    return extraction_viz_filepath


if __name__ == "__main__":
    from src.financial_news.rss_feed_service import FinancialRSSDataService

    rss_service = FinancialRSSDataService()
    rss_service.load()
    news = list(rss_service.get_news())

    assert len(news) > 1

    # time.sleep(20)

    top_10_news_items = [
        textwrap.dedent(f"""Title:{i.title.strip()}
        Description:{i.description.strip()}""")
        for i in news[:50]
    ]

    extract_company_names_job = LanguageExtractionJobType(
        prompt="""Extract company names in order of appearance."
    "Use exact text for extractions. Do not paraphrase or overlap entities."
    "Provide meaningful attributes for each entity to add context""",
        examples=[
            ExampleData(
                text="Title:DigitalBridge Group, Inc. (DBRG) Q2 2025 Earnings Call Transcript\nDescription:\nTitle:Arbor Realty: I Own The 8% Yielding Preferreds Over The Commons\nDescription:\nTitle:6-K: Report of foreign issuer rules 13a-16 and 15d-16 of the Securities Exchange Act\nDescription:THOMSON REUTERS CORP /CAN/\nTitle:ESPN inks five-year deal for WWE's live premium events including WrestleMania, Royal Rumble\n",
                extractions=[
                    Extraction(
                        extraction_class="company_name",
                        extraction_text="DigitalBridge Group, Inc.",
                    ),
                    Extraction(extraction_class="company_name", extraction_text="Arbor Realty"),
                    Extraction(extraction_class="company_name", extraction_text="ESPN"),
                ],
            )
        ],
    )

    input_text = "\n".join(top_10_news_items)
    log.info(input_text)
    r = extract(input_text=input_text, job_type=extract_company_names_job)
