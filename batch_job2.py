import argparse
import time

from azure.identity import DefaultAzureCredential
from azure.identity import get_bearer_token_provider
from azure.storage.blob import BlobClient
from openai import OpenAI

ENDPOINT = "https://fsi-foundry.openai.azure.com/openai/v1/"

parser = argparse.ArgumentParser(description="Azure OpenAI batch using Blob Storage in another storage account")
parser.add_argument("--storage-account", required=True, help="Storage account name (not the Foundry resource's)")
parser.add_argument("--input-container", default="batch-input")
parser.add_argument("--output-container", default="batch-output")
parser.add_argument("--input-blob", default="test.jsonl", help="Blob name of the input file")
parser.add_argument("--upload", action="store_true", help="Upload local test.jsonl to the input blob first")
args = parser.parse_args()

account_url = f"https://{args.storage_account}.blob.core.windows.net"
input_blob_url = f"{account_url}/{args.input_container}/{args.input_blob}"
output_container_url = f"{account_url}/{args.output_container}"

credential = DefaultAzureCredential()

if args.upload:
    blob = BlobClient.from_blob_url(input_blob_url, credential=credential)
    with open("test.jsonl", "rb") as f:
        blob.upload_blob(f, overwrite=True)
    print("Uploaded:", input_blob_url)

token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
client = OpenAI(base_url=ENDPOINT, api_key=token_provider)

# No input_file_id: the batch reads the input from Blob Storage and writes to the output container.
# The Foundry resource's system-assigned identity needs Storage Blob Data Contributor on the storage account.
batch = client.batches.create(
    input_file_id=None,
    endpoint="/chat/completions",
    completion_window="24h",
    extra_body={
        "input_blob": input_blob_url,
        "output_folder": {"url": output_container_url},
    },
)
print("Batch id:", batch.id, "status:", batch.status)

terminal = {"completed", "failed", "canceled", "cancelled", "expired"}
while batch.status not in terminal:
    time.sleep(30)
    batch = client.batches.retrieve(batch.id)
    print(time.strftime("%H:%M:%S"), "status:", batch.status, batch.request_counts, flush=True)

if batch.status != "completed":
    for error in (batch.errors.data if batch.errors else []):
        print(f"Error {error.code}: {error.message}")
    raise SystemExit(1)

print("Output blob:", batch.output_blob)
print("Error blob:", batch.error_blob)

# The error blob is only created when there are errors.
for name, url, local in (("output", batch.output_blob, "output2.jsonl"), ("error", batch.error_blob, "errors2.jsonl")):
    try:
        data = BlobClient.from_blob_url(url, credential=credential).download_blob().readall()
    except Exception as e:
        print(f"No {name} blob downloaded: {type(e).__name__}")
        continue
    with open(local, "wb") as out:
        out.write(data)
    print(f"Saved {local}")
