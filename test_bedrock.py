import boto3
import json

client = boto3.client("bedrock-runtime", region_name="eu-west-1")

resp = client.invoke_model(
    modelId="eu.anthropic.claude-haiku-4-5-20251001-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": "Dis bonjour en français"}],
        "max_tokens": 50,
    }),
)

print(json.loads(resp["body"].read())["content"][0]["text"])
