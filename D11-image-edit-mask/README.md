# D11 Edit an image with a mask

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video 'Vision and information extraction: what the exam adds' in the AI-103 playlist.

**Goal:** generate one image with `gpt-image-2`, change only one area of it with a mask, change the whole image with a prompt alone, and compare the three side by side.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Implement computer vision solutions > Design and implement image- and video-generation solutions: "Configure image-editing workflows, including inpainting, mask‑based edits, and prompt‑driven modifications"
- Implement computer vision solutions > Design and implement image- and video-generation solutions: "Select and apply appropriate generation and editing controls provided by the platform"

`gpt-image-2` and the image edit endpoint are generally available. No preview features in this demo.

## What it costs and why

Three image calls in total, nothing billed by the hour:

- **Step 2, generate:** one image, `n=1`.
- **Step 4, edit with a mask:** one image.
- **Step 5, edit with a prompt only:** one image.
- Steps 3 and 6 run locally with Pillow and call nothing.

Learn bills image generation as image tokens and points to the Azure OpenAI pricing page for rates. It gives no price per image, so none is given here. Learn describes `gpt-image-2` as "higher latency and cost" than the other models, so the script keeps the cost down where Learn documents a control for it:

- **Quality `low`.** Learn lists `low`, `medium` and `high` for `gpt-image-2`, with the default `high`. Set `IMAGE_QUALITY=medium` if `low` looks too rough on screen.
- **Size `1024x1024`, `n=1`.** One square image per call, no 4K.
- **Every re-run is a new image.** Run `mask` and `compare` as often as you like; they are free.

The deployment is Global Standard (pay per use) on the shared resource. `gpt-image-2` is a model sold directly by Azure. No Marketplace model, no provisioned throughput. Delete the deployment afterwards (see Cleanup).

## Prerequisites

- The shared demo resource from `../common/setup.sh` (Sweden Central), and `../common/demo.env` filled in. Learn lists `gpt-image-2` version 2026-04-21 for Global Standard in Sweden Central, so no second resource is needed.
- No access request. `gpt-image-2` is generally available. `gpt-image-1` and `gpt-image-1.5` are limited access and need an application first; this demo doesn't use them.
- Quota for image models is counted in images per minute; Learn gives a default of 5 per minute for `gpt-image-2`. Three calls fit.
- `az login` with an account that can create deployments and assign roles on the Foundry resource. `./setup.sh` gives you Cognitive Services OpenAI User, the role Learn names for Entra ID calls to the image API. No keys.
- Python 3.10 or later.

## Setup

```bash
cd D11-image-edit-mask
./setup.sh                       # deploys gpt-image-2, Global Standard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

Role assignments can take a few minutes to apply. If the first call fails with a 401 or 403, wait a few minutes and try again.

All output goes to `out/`, which git ignores.

## Steps

1. **Read the code: the client.** Open `image_demo.py` and look at `client()`.
   It is the plain `OpenAI` client pointed at the v1 endpoint of your resource, `https://<resource>.openai.azure.com/openai/v1/`, with a token from `DefaultAzureCredential` instead of a key. `model` in every call is the deployment name.

2. **Run `python image_demo.py generate`.** One `images.generate` call: a red bicycle against a white brick wall.
   Expected: `Saved out/original.png: 1024x1024 RGB` (the mode may be RGBA). Open the file. Generation takes 10 to 30 seconds; Learn says up to 60 for complex prompts.
   If this step fails: `DeploymentNotFound` means the deployment name doesn't match `IMAGE_DEPLOYMENT`. A 401 is a missing role, or one that hasn't applied yet. A `contentFilter` error means the prompt was blocked; this prompt shouldn't be.

3. **Run `python image_demo.py mask`.** This builds the mask locally, no call.
   The mask is a PNG with an alpha channel, the same size as the image. It is opaque everywhere except one box on the wall above the bicycle, where it is fully transparent (alpha 0). Transparent means: the model may change this. Everything else should stay.
   Expected: `same size as original: True`, about 9% transparent pixels, and a file size of a few KB (the reference says under 4 MB).
   If this step fails: run `generate` first. If the bicycle ended up under the box, change `MASK_BOX` in the script and run `mask` again.

4. **Run `python image_demo.py edit-mask`.** `images.edit` with the image, the mask and a prompt. The prompt describes the whole image you want, including the new wall clock, not only the change.
   Expected: `Saved out/edit_mask.png: 1024x1024`. A clock on the wall, the rest of the scene the same.
   If this step fails: the edit API takes multipart form data, not JSON. The SDK sends multipart for you, so with a 400 check the mask first: a PNG, the same size as the image, under 4 MB. If the edit lands everywhere except the box, the mask is inverted: transparent must be the area to edit. If the v1 endpoint rejects the edit call, use the Learn quickstart route instead: `AzureOpenAI(azure_endpoint=..., api_version="2025-04-01-preview", azure_ad_token_provider=...)`.

5. **Run `python image_demo.py edit-prompt`.** The same original, a prompt and no mask: snowy winter evening.
   Expected: `Saved out/edit_prompt.png`. Same bicycle and wall, but the whole picture changes: light, colours, snow.
   If this step fails: see step 4.

6. **Run `python image_demo.py compare`.** Local, no call. It puts original, mask area, masked edit and prompt-only edit side by side in `out/compare.png`, and measures how much each edit changed the pixels outside the box.
   Expected: four panels, and two numbers. The masked edit has a small difference outside the box, the prompt-only edit a much larger one. Learn doesn't promise that pixels outside the mask stay identical, which is why the script measures it rather than assuming it.

7. **Wrap up, no command.** Generate, then edit. With a mask: a PNG, same size, transparent where the change goes. Without a mask, the prompt steers the whole image. Quality, size and `n` are the controls that drive time and cost.

## Cleanup

```bash
./cleanup.sh
```

This deletes the `gpt-image-2` deployment and the `out/` folder. Leave the shared resource, project and other deployments; the other demos use them. The Cognitive Services OpenAI User role assignment stays; it costs nothing.

## Notes

- `gpt-image-2` returns base64 only, no URL. The script decodes `b64_json` and writes PNG files.
- The edit endpoint takes up to 16 input images. With several, the mask applies to the first one. This demo sends one.
- `input_fidelity` (keep faces and style closer to the input) is an edit option on Learn, not supported by `gpt-image-1-mini`. The preview reference lists it for the `gpt-image-1` series only, so this demo leaves it out.
- `gpt-image-2` sizes: both edges multiples of 16, long edge up to 3840 px, aspect ratio up to 3:1, 655,360 to 8,294,400 pixels in total.
- Retirement: `gpt-image-1` retired on 2026-10-23, `gpt-image-1.5` retires on 2026-12-16, `gpt-image-2` (2026-04-21) on 2027-10-21. Check the schedule before you build on a version.

## Sources

Microsoft Learn:

- Azure OpenAI image generation models (models table, Python and REST quickstarts, image edit API, mask, quality, quotas, troubleshooting): https://learn.microsoft.com/azure/foundry/openai/how-to/dall-e
- REST API preview reference, image edit parameters (mask under 4 MB, mask on the first image): https://learn.microsoft.com/azure/foundry/openai/reference-preview#image-generations---edit
- Region availability, Global Standard (gpt-image-2 in Sweden Central): https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability#global-standard
- Foundry Models sold by Azure, image generation models: https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure
- Model retirement schedule: https://learn.microsoft.com/azure/foundry/openai/concepts/model-retirement-schedule
- Keyless client for the v1 endpoint, Python: https://learn.microsoft.com/azure/foundry/openai/supported-languages?pivots=programming-language-python#authentication
- `az cognitiveservices account deployment`: https://learn.microsoft.com/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest
- Study guide for Exam AI-103: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Checked against Learn on 2026-11-07.
