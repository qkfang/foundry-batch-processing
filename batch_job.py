import json
import time

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

ENDPOINT = "https://fsi-foundry.openai.azure.com/openai/v1/"

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)
client = OpenAI(base_url=ENDPOINT, api_key=token_provider)

# Upload the input file
with open("test.jsonl", "rb") as f:
    # Expiring input files raise the per-resource file limit from 500 to 10,000
    input_file = client.files.create(
        file=f,
        purpose="batch",
        extra_body={"expires_after": {"seconds": 1209600, "anchor": "created_at"}},
    )
print("Uploaded file:", input_file.id)

# Create the batch job
batch = client.batches.create(
    input_file_id=input_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
)
print("Batch id:", batch.id, "status:", batch.status)

# Poll until the job reaches a terminal state
terminal = {"completed", "failed", "canceled", "cancelled", "expired"}
while batch.status not in terminal:
    time.sleep(30)
    batch = client.batches.retrieve(batch.id)
    print(time.strftime("%H:%M:%S"), "status:", batch.status, batch.request_counts)

if batch.error_file_id:
    print("Errors:\n", client.files.content(batch.error_file_id).text)

if batch.output_file_id:
    text = client.files.content(batch.output_file_id).text
    with open("output.jsonl", "w", encoding="utf-8") as out:
        out.write(text)
    for line in text.splitlines():
        r = json.loads(line)
        print(r["custom_id"], "->", r["response"]["body"]["choices"][0]["message"]["content"])
