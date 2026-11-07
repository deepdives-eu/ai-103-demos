# D3 Keyless by default

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video 'Plan and manage: monitor, secure and govern' in the AI-103 playlist.

**Goal:** make the same model call with an API key and with Microsoft Entra ID, switch key authentication off on the Foundry resource, watch the key call fail while the keyless call keeps working, and then show that the Foundry User role assignment is what lets the keyless call through.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Plan and manage an Azure AI solution > Manage, monitor, and secure AI systems: "Configure security, including managed identity, private networking, keyless credentials, and role policies"
- Implement generative AI and agentic solutions > Build generative applications by using Foundry: "Configure an application to connect to a Foundry project"

This demo covers keyless credentials and role policies for your own user. Managed identity comes up in the notes; private networking is not part of this demo.

## What it costs and why

Tokens only, nothing billed by the hour. Every successful call is one short Responses request to `gpt-5.4-mini`: a one-sentence question, a one-sentence answer, reasoning effort low, output capped at 500 tokens. The script prints the token count after every call.

- **Successful calls**: about seven over the whole demo (step 2 once, steps 3, 5 and 8 twice each because `keyless` calls two endpoints), plus the polling in steps 4 and 7.
- **Refused calls**: a 401 or 403 returns no answer and no token count. The polling in steps 4 and 7 repeats a call every 20 seconds, and until the change applies those calls still succeed and use tokens. Keep `--minutes` short if you're careful with cost; each call is small.
- **Role assignments and the `disableLocalAuth` setting**: control plane changes, no charge.

The model is sold directly by Azure and deployed as Global Standard (pay per token) by `../common/setup.sh`. No Marketplace model, no provisioned throughput (PTU).

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini`, Global Standard), and `../common/demo.env` filled in. The resource has a custom subdomain (setup.sh sets `--custom-domain`); Learn says token authentication needs one.
- You (the signed-in user) have Foundry User on the Foundry resource. `../common/setup.sh` does that. Foundry User is role ID `53ca6127-db72-4b80-b1b0-d745d6d5456d` (formerly Azure AI User).
- You can change role assignments on the resource (Owner or User Access Administrator), for steps 7 and 8.
- Azure CLI signed in (`az login`), Python 3.10 or later.

## Setup

```bash
cd D3-keyless-auth
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

## Steps

1. **Read the code: two clients.** Open `auth_demo.py` and look at `key_client()` and `keyless_client()`.
   Both point at the same endpoint, `https://<resource>.openai.azure.com/openai/v1/`. The first passes the resource key. The second passes a token provider built from `DefaultAzureCredential` with the scope `https://ai.azure.com/.default`. On your laptop that credential picks up your `az login`; deployed in Azure, the same code picks up a managed identity. `project_client()` is the third way in: the Foundry project endpoint through `AIProjectClient`, which only accepts Entra ID.

2. **Call with the key.** Check the setting, put the key in your shell (not in a file), and call:

   ```bash
   ./local_auth.sh status
   export FOUNDRY_KEY=$(az cognitiveservices account keys list -n "$FOUNDRY" -g "$RG" --query key1 -o tsv)
   python auth_demo.py key
   ```

   Expected: `disableLocalAuth on <name>:` followed by nothing or `false`, then `[api key, /openai/v1] OK (n tokens): ...`.
   If this step fails: an empty `FOUNDRY_KEY` means `keys list` returned nothing; run it without `--query` and look at the field names. A 401 here means key auth is already off; run `./local_auth.sh on`, wait, and try again, or skip to step 3.

3. **Call without a key.** `python auth_demo.py keyless`
   Expected: two lines, `[Entra ID, /openai/v1] OK ...` and `[Entra ID, project] OK ...`. Same identity, two endpoints, no secret anywhere.
   If this step fails: a 401 usually means the token is for the wrong scope or the endpoint isn't the custom subdomain. A 403 means a missing role; run `./roles.sh show`, and `./roles.sh add` if Foundry User isn't listed.

4. **Switch keys off.** `./local_auth.sh off`, then `python auth_demo.py key --until denied --minutes 30`
   This sets `disableLocalAuth` to `true` on the Foundry resource. The setting changes at once, but Learn says the gateway can keep accepting the old key for a few minutes, and in some cases for several hours. The script repeats the key call every 20 seconds until it's refused.
   Expected: `disableLocalAuth on <name>: true`, a few `OK` lines, then `[api key, /openai/v1] refused: HTTP 401: ...` and `Reached 'denied'.` Learn gives the error as `Access denied due to invalid subscription key or wrong API endpoint`.
   If this step fails: if `az resource update` is rejected, use the PowerShell route Learn documents, `Set-AzCognitiveServicesAccount -ResourceGroupName <rg> -Name <name> -DisableLocalAuth $true`. If the key still works after 30 minutes, run the same command again later; don't move on until it's refused.

5. **Keyless still works.** `python auth_demo.py keyless`
   Expected: both lines `OK`, exactly as in step 3. Switching keys off changes nothing for Entra ID callers.

6. **What lets the keyless call in.** `./roles.sh show`
   Expected: a table with Foundry User (it may still show as Azure AI User during the rename) and role ID `.../53ca6127-db72-4b80-b1b0-d745d6d5456d`.
   Foundry User is a data plane role: it allows using the resource (model calls, agents, evaluations), not managing it. The generic Owner and Contributor roles are the other way round. They manage the resource but have no data actions, so they don't let you call the model. With a key there are no roles at all: the key grants full access.

7. **Take the role away.** `./roles.sh remove`, then `python auth_demo.py keyless --until denied`
   Role changes can take up to 10 minutes to apply.
   Expected: `OK` lines for a while, then both calls `refused: HTTP 403: ...` and `Reached 'denied'.` You are still signed in, the token is still valid, but you're no longer allowed.
   If this step fails: if one call keeps working, you hold another data plane role on the resource. `./roles.sh show` lists it. For example, D13's setup gives you Cognitive Services OpenAI User on the Foundry resource, which also allows the `/openai/v1` call. Remove that assignment too, or accept the mixed result and explain it. Roles inherited from the resource group or subscription don't show in `roles.sh show`; check them in the portal under **Access control (IAM) > Check access**.

8. **Give it back.** `./roles.sh add`, then `python auth_demo.py keyless --until ok`
   Expected: `refused: HTTP 403` for a few minutes, then both lines `OK` and `Reached 'ok'.`
   If this step fails: after 15 minutes, sign out and in again (`az logout`, `az login`); Learn says that forces a refresh of role assignment changes for the Azure CLI. Then run `python auth_demo.py keyless`.

9. **Wrap up, no command.** In code, keyless is one credential object instead of a key. On the resource, `disableLocalAuth` closes the key door. And access is a role assignment per identity, which you can grant, audit and take away without rotating anything.

## Cleanup

```bash
./cleanup.sh
unset FOUNDRY_KEY
```

This assigns Foundry User to you again, in case you stopped after step 7, and shows the key setting. **Key auth stays off.** No other demo in this repo calls the Foundry resource with a key: they all use `DefaultAzureCredential`, and Learn lists Agent Service and evaluations as Entra ID only. D13 switches keys off on its own search service and calls the Foundry resource with a token. If you need keys back for your own work, run `./cleanup.sh --enable-keys`; that can also take minutes to hours to apply.

## Notes

- Learn's keyless how-to also says people who already have a key can keep using it until you regenerate it, and suggests regenerating both keys from the portal. If you leave key auth off, regenerating is optional; if you turn it back on, regenerate so the key you exported in step 2 is useless: `az cognitiveservices account keys regenerate -n "$FOUNDRY" -g "$RG" --key-name Key1` (and `Key2`).
- In production, Learn recommends a deterministic credential instead of `DefaultAzureCredential`, for example `ManagedIdentityCredential`, or a `ChainedTokenCredential` with only the credentials you expect.
- To enforce this for every Foundry resource in a subscription or resource group, Learn points to the Azure Policy "Azure AI Services resources should have key access disabled (disable local authentication)". In Bicep or ARM, set `disableLocalAuth: true` on the account.
- For an app that only calls agents, Foundry Agent Consumer is enough. Foundry User is the starting point for developers and for the project's managed identity.
- Learn's keyless how-to for Foundry Models assigns Cognitive Services User, while the Foundry RBAC page says not to assign roles that start with Cognitive Services for Foundry work. This demo follows the RBAC page and uses Foundry User.

## Sources

Microsoft Learn:

- Configure keyless authentication with Microsoft Entra ID (code, `disableLocalAuth`, key regeneration, credential best practices): https://learn.microsoft.com/azure/foundry/foundry-models/how-to/configure-entra-id
- Disable local authentication in Foundry Tools (policy, propagation delay, the 401 error, re-enable): https://learn.microsoft.com/azure/ai-services/disable-local-auth
- Authentication and authorization in Microsoft Foundry (token scope, feature support matrix, role IDs, 401 and 403): https://learn.microsoft.com/azure/foundry/concepts/authentication-authorization-foundry
- Role-based access control for Microsoft Foundry (Foundry User, Owner without data actions, Foundry Agent Consumer): https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry
- Responses API, key and Entra ID clients in Python: https://learn.microsoft.com/azure/foundry/openai/how-to/responses#generate-a-text-response
- Error handling with the OpenAI Python library: https://learn.microsoft.com/azure/foundry/openai/supported-languages?pivots=programming-language-python#error-handling
- `az resource update --set properties.disableLocalAuth=true` (shown for Cosmos DB): https://learn.microsoft.com/azure/cosmos-db/how-to-connect-role-based-access-control#disable-key-based-authentication
- `az cognitiveservices account keys`: https://learn.microsoft.com/cli/azure/cognitiveservices/account/keys
- Role assignment changes take up to 10 minutes: https://learn.microsoft.com/azure/role-based-access-control/troubleshooting#azure-role-assignments
- Study guide for Exam AI-103: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Checked against Learn on 2026-11-07.
