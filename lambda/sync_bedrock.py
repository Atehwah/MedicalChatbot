import os
import boto3
import json

def handler(event, context):
    # Initialize the Bedrock Agent client
    client = boto3.client("bedrock-agent-runtime")
    
    # Prepare the input parameters
    input_params = {
        "knowledgeBaseId": os.getenv["KNOWLEDGE_BASE_ID"],
        "dataSourceId": os.getenv["DATA_SOURCE_ID"],
        "clientToken": context.aws_request_id,  # Unique token for idempotency
    }

    # Start the ingestion job
    response = client.start_ingestion_job(**input_params)
    
    # Return the response
    return {
        "statusCode": 200,
        "body": json.dumps({
            "ingestionJob": response.get("ingestionJob")
        })
    }