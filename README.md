# foundry-batch-processing

Sample scripts for running Azure OpenAI (Microsoft Foundry) batch jobs with the `openai` Python SDK and Microsoft Entra ID authentication.

| Script | Description |
| --- | --- |
| `batch_job.py` | Uploads `test.jsonl` via the Files API (expiring after 14 days), creates a batch, polls until done, and saves `output.jsonl`. |
| `batch_job2.py` | Reads the input from, and writes results to, Azure Blob Storage in a separate storage account, then downloads `output2.jsonl`. |

`test.jsonl` holds three chat completion requests. Set `body.model` to your Global-Batch deployment name.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install openai azure-identity azure-storage-blob
az login
```

Set `ENDPOINT` in each script to your Azure OpenAI resource (`https://<resource>.openai.azure.com/openai/v1/`). You need the **Cognitive Services OpenAI User** role on the resource.

## Run

```powershell
python batch_job.py
python batch_job2.py --storage-account <name> --upload
```

`batch_job2.py` options: `--input-container` (default `batch-input`), `--output-container` (default `batch-output`), `--input-blob` (default `test.jsonl`), and `--upload` to copy the local `test.jsonl` to the input blob first.

Jobs can take from a few minutes to about an hour.

## Blob Storage access (batch_job2.py)

1. Enable the system-assigned managed identity on the Azure OpenAI resource.
2. Assign **Storage Blob Data Contributor** on the storage account to that identity and to your user.
3. Create the `batch-input` and `batch-output` containers.
4. The storage account must be reachable over the network. In this tenant, public access is forced off unless the account has the tag `SecurityControl=Ignore`.

Don't modify the input blob while a job is running, or it fails with `input_modified`.

## Cleanup

There is no API to delete a batch job record. It is kept for 365 days after it reaches a terminal state. Files uploaded through the Files API can be deleted with `DELETE /openai/v1/files/{file_id}`. Blobs in your storage account can be deleted directly.