"""Step 2: one image in, a caption, a detailed description and alt text out.

Structured outputs with a Pydantic model and responses.parse, as in D9. The image goes in as an
input_image content part with a base64 data URL.
"""
import sys

from pydantic import BaseModel, ConfigDict, Field

from common import (MAX_OUTPUT_TOKENS, REASONING, check_finished, deployment,
                    get_openai_client, image_part, print_usage, user_message)


class ImageDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str = Field(description="One short line for a gallery, under 10 words.")
    detailed_description: str = Field(description="Three to five sentences for search and for people who want detail.")
    alt_text: str = Field(description="Alt text for a screen reader: one sentence that says what matters.")


TASK = (
    "Describe this image for a website. "
    "Only describe what you can see. If you can't tell something, leave it out. "
    "The alt text is read out by a screen reader: one sentence, say what matters, keep it short."
)

image_name = sys.argv[1] if len(sys.argv) > 1 else "scene.png"

openai = get_openai_client()
response = openai.responses.parse(
    model=deployment(),
    input=user_message(TASK, image_part(image_name)),
    text_format=ImageDescription,
    reasoning=REASONING,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)
check_finished(response)

d: ImageDescription = response.output_parsed
print(f"Image:    {image_name}")
print(f"Caption:  {d.caption}")
print(f"Detail:   {d.detailed_description}")
print(f"Alt text: {d.alt_text}  ({len(d.alt_text)} characters)")
print(f'\nAs HTML:  <img src="{image_name}" alt="{d.alt_text}">')

print_usage(response)
