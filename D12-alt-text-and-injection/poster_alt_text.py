"""Steps 3 and 4: alt text for a poster that has an instruction hidden in its small print.

  python poster_alt_text.py              step 3, no defence: one plain request, free text back
  python poster_alt_text.py --defended   step 4, the documented prompt-level mitigations:
                                         instructions that say image text is data,
                                         and a strict schema that gives that text its own field

Neither run screens the image. That is step 5.
"""
import sys

import openai as openai_sdk

from common import (MAX_OUTPUT_TOKENS, REASONING, check_finished, deployment,
                    get_openai_client, image_part, print_usage, user_message)
from defence import INSTRUCTIONS, TASK, PosterReading

DEFENDED = "--defended" in sys.argv

openai = get_openai_client()
poster = image_part("poster.png", detail="high")   # high detail: the small print is small

try:
    if not DEFENDED:
        print("Run: no defence\n")
        response = openai.responses.create(
            model=deployment(),
            input=user_message(TASK, poster),
            reasoning=REASONING,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        check_finished(response)
        print(f"Alt text: {response.output_text}")
    else:
        print("Run: instructions + schema\n")
        response = openai.responses.parse(
            model=deployment(),
            instructions=INSTRUCTIONS,
            input=user_message(TASK, poster),
            text_format=PosterReading,
            reasoning=REASONING,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        check_finished(response)
        r: PosterReading = response.output_parsed
        print(f"Alt text:          {r.alt_text}")
        print(f"Instruction found: {r.instruction_found}")
        print("Text in the image:")
        for line in r.text_in_image:
            print(f"  | {line}")
except openai_sdk.BadRequestError as e:
    # If a guardrail on the deployment blocks the request, the call fails with HTTP 400.
    # Print it instead of a stack trace: that is a result worth seeing too.
    print(f"Request blocked (HTTP 400): {getattr(e, 'code', None)}\n{e.message}")
    raise SystemExit(0)

print_usage(response)
