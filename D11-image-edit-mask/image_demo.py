"""D11 Edit an image with a mask: gpt-image-2 generate, masked edit (inpainting), prompt-only edit.

One script, one step per subcommand, so each step can be run and explained on screen:

  python image_demo.py generate     generate one image (out/original.png)                       1 image
  python image_demo.py mask         build the mask locally with Pillow (out/mask.png)            no call
  python image_demo.py edit-mask    edit only the transparent area of the mask (out/edit_mask.png) 1 image
  python image_demo.py edit-prompt  the same image, a prompt and no mask (out/edit_prompt.png)  1 image
  python image_demo.py compare      side by side and a pixel check outside the mask (out/compare.png) no call

Three image calls in total. Keyless (DefaultAzureCredential, your `az login`).
Env vars from ../common/demo.env: FOUNDRY. Optional: IMAGE_DEPLOYMENT (default gpt-image-2),
IMAGE_QUALITY (default low).

Client, generate and edit calls follow
https://learn.microsoft.com/azure/foundry/openai/how-to/dall-e (Python and REST quickstarts,
"Call the image edit API"). Mask rules: same page, "Mask", and
https://learn.microsoft.com/azure/foundry/openai/reference-preview#image-generations---edit
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI
from PIL import Image, ImageChops, ImageDraw, ImageStat

OUT = Path(__file__).parent / "out"
ORIGINAL = OUT / "original.png"
MASK = OUT / "mask.png"
EDIT_MASK = OUT / "edit_mask.png"
EDIT_PROMPT = OUT / "edit_prompt.png"
COMPARE = OUT / "compare.png"

DEPLOYMENT = os.environ.get("IMAGE_DEPLOYMENT", "gpt-image-2")
# Learn: low, medium, high; "low is optimized for latency-sensitive use cases". Low keeps the demo cheap.
QUALITY = os.environ.get("IMAGE_QUALITY", "low")
# Square is the smallest standard size and within gpt-image-2's limits (multiples of 16, 655,360+ pixels).
SIZE = "1024x1024"

PROMPT_GENERATE = (
    "A photo of a red bicycle leaning against a plain white brick wall on a quiet street, "
    "soft morning light, no people, no text."
)
# The area the model may change: the empty wall above the bicycle, as a box in pixels (left, top, right, bottom).
MASK_BOX = (352, 96, 672, 384)
# For an edit, describe the whole image you want, not only the change.
PROMPT_EDIT_MASK = (
    "A photo of a red bicycle leaning against a plain white brick wall on a quiet street, "
    "soft morning light, with a round black wall clock hanging on the wall above the bicycle."
)
PROMPT_EDIT_ONLY = "The same scene on a snowy winter evening, street lamps on."


def client() -> OpenAI:
    """OpenAI client on the v1 endpoint of the shared Foundry resource, keyless, as in the Learn sample."""
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://ai.azure.com/.default")
    return OpenAI(
        base_url=f"https://{os.environ['FOUNDRY']}.openai.azure.com/openai/v1/",
        api_key=token_provider,
    )


def save_first(result, path: Path) -> None:
    """GPT-image models return base64 only (no URL option)."""
    path.write_bytes(base64.b64decode(result.data[0].b64_json))
    with Image.open(path) as img:
        print(f"Saved {path.relative_to(path.parent.parent)}: {img.size[0]}x{img.size[1]} {img.mode}")
    usage = getattr(result, "usage", None)
    if usage:
        print(f"Usage: {usage}")


def need(*paths: Path) -> None:
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        sys.exit(f"Missing {', '.join(missing)}. Run the earlier steps first.")


def generate() -> None:
    OUT.mkdir(exist_ok=True)
    print(f"images.generate on deployment {DEPLOYMENT}, size {SIZE}, quality {QUALITY}, n=1")
    result = client().images.generate(
        model=DEPLOYMENT,  # the deployment name
        prompt=PROMPT_GENERATE,
        n=1,
        size=SIZE,
        quality=QUALITY,
        output_format="png",
    )
    save_first(result, ORIGINAL)


def mask() -> None:
    """Opaque everywhere, fully transparent (alpha 0) where the model may edit. PNG, same size as the image."""
    need(ORIGINAL)
    with Image.open(ORIGINAL) as img:
        size = img.size
    m = Image.new("RGBA", size, (0, 0, 0, 255))
    ImageDraw.Draw(m).rectangle(MASK_BOX, fill=(0, 0, 0, 0))
    m.save(MASK, format="PNG")
    alpha = m.getchannel("A")
    transparent = alpha.histogram()[0]
    print(f"Saved out/mask.png: {m.size[0]}x{m.size[1]} {m.mode}, same size as original: {m.size == size}")
    print(f"Transparent pixels (alpha 0): {transparent} of {size[0] * size[1]} "
          f"({100 * transparent / (size[0] * size[1]):.1f}%), box {MASK_BOX}")
    print(f"File size: {MASK.stat().st_size / 1024:.0f} KB (the reference says under 4 MB)")


def edit_mask() -> None:
    need(ORIGINAL, MASK)
    print(f"images.edit with mask on {DEPLOYMENT}, size {SIZE}, quality {QUALITY}, n=1")
    with open(ORIGINAL, "rb") as image_file, open(MASK, "rb") as mask_file:
        result = client().images.edit(
            model=DEPLOYMENT,
            image=image_file,
            mask=mask_file,
            prompt=PROMPT_EDIT_MASK,
            n=1,
            size=SIZE,
            quality=QUALITY,
        )
    save_first(result, EDIT_MASK)


def edit_prompt() -> None:
    need(ORIGINAL)
    print(f"images.edit without mask on {DEPLOYMENT}, size {SIZE}, quality {QUALITY}, n=1")
    with open(ORIGINAL, "rb") as image_file:
        result = client().images.edit(
            model=DEPLOYMENT,
            image=image_file,
            prompt=PROMPT_EDIT_ONLY,
            n=1,
            size=SIZE,
            quality=QUALITY,
        )
    save_first(result, EDIT_PROMPT)


def outside_mask_difference(original: Image.Image, edited: Image.Image) -> float:
    """Mean absolute difference (0-255) between two images, only outside the mask box. Runs locally."""
    edited = edited.resize(original.size)
    diff = ImageChops.difference(original.convert("RGB"), edited.convert("RGB")).convert("L")
    keep = Image.new("L", original.size, 255)
    ImageDraw.Draw(keep).rectangle(MASK_BOX, fill=0)
    return ImageStat.Stat(diff, mask=keep).mean[0]


def compare() -> None:
    need(ORIGINAL, EDIT_MASK, EDIT_PROMPT)
    original = Image.open(ORIGINAL).convert("RGB")
    with_mask = Image.open(EDIT_MASK).convert("RGB")
    prompt_only = Image.open(EDIT_PROMPT).convert("RGB")

    shown_mask = original.copy()
    ImageDraw.Draw(shown_mask).rectangle(MASK_BOX, outline=(255, 0, 0), width=8)

    panels = [("original", original), ("mask area", shown_mask),
              ("edit with mask", with_mask), ("edit, prompt only", prompt_only)]
    w, h, label = 512, 512, 40
    sheet = Image.new("RGB", (w * len(panels), h + label), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (name, img) in enumerate(panels):
        sheet.paste(img.resize((w, h)), (i * w, label))
        draw.text((i * w + 12, 12), name, fill="black")
    sheet.save(COMPARE)
    print("Saved out/compare.png: original | mask area | edit with mask | edit, prompt only")

    print("Mean pixel difference to the original, outside the mask box (0 = identical, 255 = opposite):")
    print(f"  edit with mask:    {outside_mask_difference(original, with_mask):5.1f}")
    print(f"  edit, prompt only: {outside_mask_difference(original, prompt_only):5.1f}")


STEPS = {
    "generate": generate,
    "mask": mask,
    "edit-mask": edit_mask,
    "edit-prompt": edit_prompt,
    "compare": compare,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=STEPS)
    STEPS[parser.parse_args().step]()
