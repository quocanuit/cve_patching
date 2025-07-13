import os
import json
import logging
import urllib3
from base64 import b64encode

def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    http = urllib3.PoolManager()

    logger.info(f"Received event: {json.dumps(event)}")

    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
    except Exception as e:
        logger.error(f"Error parsing S3 event: {e}")
        raise

    jenkins_server = os.environ['JENKINS_SERVER']
    jenkins_token = os.environ['JENKINS_TOKEN']
    jenkins_job = os.environ['JENKINS_JOB']
    svc_api_token = os.environ['API_TOKEN']

    trigger_url = f"{jenkins_server}/job/{jenkins_job}/build?token={jenkins_token}"

    auth_string = f"svc_account:{svc_api_token}"
    encoded_auth = b64encode(auth_string.encode()).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded_auth}"
    }

    try:
        response = http.request("POST", trigger_url, headers=headers)
        logger.info(f"Jenkins response status: {response.status}")
        if response.status >= 400:
            raise Exception(f"Jenkins error with status code: {response.status}")
    except Exception as e:
        logger.error(f"Failed to trigger Jenkins: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error triggering Jenkins: {str(e)}")
        }

    return {
        'statusCode': 200,
        'body': json.dumps("Jenkins job triggered successfully!")
    }
