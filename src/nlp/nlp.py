from dataclasses import dataclass
from pathlib import Path
import textwrap
import langextract as lx

from src.core.utilities import LANGEXTRACT_MODEL, get_logger, DATA_DIR, get_current_datetime, datetime_iso8601_str, STRUCTURED_TEXT_DATA_DIR

log = get_logger(__name__)

# prompt + examples together for a task


@dataclass(frozen=True)
class LanguageExtractionTask:
    """Example
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
        )
    ]
    ```
    """

    prompt: str
    examples: list[lx.data.ExampleData]
    name: str = "UnnamedTask"


# tbd name on what exactly we will be extracting
def extract_sometext_for_task(self, input_text: str, task: LanguageExtractionTask):
    prompt = textwrap.dedent(task.prompt)

    result: lx.data.AnnotatedDocument = lx.extract(
        text_or_documents=input_text,
        prompt_description=prompt,
        examples=task.examples,
        model_id=LANGEXTRACT_MODEL,
    )  # type: ignore

    output_filename = f"{task.name}-{get_current_datetime()}.jsonl"

    # tbd name of what an extraction should be called
    EXTRACTION_RESULT_DIR = STRUCTURED_TEXT_DATA_DIR / "extraction_data"
    EXTRACTION_VISUALIZATION_DIR = STRUCTURED_TEXT_DATA_DIR / "extraction_viz"

    extraction_text_result_filepath = EXTRACTION_RESULT_DIR / output_filename
    extraction_viz_filepath = EXTRACTION_VISUALIZATION_DIR / output_filename

    # Save the results to a JSONL file
    lx.io.save_annotated_documents([result], output_name=extraction_text_result_filepath.name, output_dir=extraction_text_result_filepath.parent)  # type: ignore

    # write as a html
    html_content = lx.visualize(extraction_text_result_filepath)
    extraction_viz_filepath.write_text(html_content, encoding="utf-8")

    return result


input_text = "Lady Juliet gazed longingly at the stars, her heart aching for Romeo"
