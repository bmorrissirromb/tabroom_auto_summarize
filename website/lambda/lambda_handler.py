import json
import boto3
import os


def lambda_handler(event, context):
    print(event)
    cors_headers = {
        "Access-Control-Allow-Origin": "*",  # Required for CORS support to work
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    }

    # Do some data validation -- ensure that the number is 5 digits and the school name is 50 characters or less
    s3_client = boto3.client("s3")
    parsed_body = json.loads(event["body"])
    tournament_id = parsed_body["tournament"]
    school_name = parsed_body["school"]
    file_path_to_find_or_create = f"{tournament_id}/{school_name}/results.txt"
    raw_gpt_submission = f"{tournament_id}/{school_name}/gpt_prompt.txt"
    bucket_name = os.environ["DATA_BUCKET_NAME"]
    file_exists = s3_client.list_objects_v2(
        Bucket=bucket_name, Prefix=file_path_to_find_or_create
    )
    if "Contents" in file_exists:
        file_content = s3_client.get_object(
            Bucket=bucket_name, Key=file_path_to_find_or_create
        )
        gpt_content = s3_client.get_object(Bucket=bucket_name, Key=raw_gpt_submission)
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps(
                {
                    "file_content": file_content["Body"].read().decode("utf-8"),
                    "gpt_content": gpt_content["Body"].read().decode("utf-8"),
                }
            ),
        }
    else:
        # Fail early if tournament's end date is in the future or there are no results
        # TODO

        # Check if there are any files in the path bucket_name/tournament_id
        all_objects = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=tournament_id,
        )
        if all_objects["KeyCount"] > 0:
            return {
                "isBase64Encoded": False,
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps(
                    {
                        "file_content": "Tournament exists, but school does not. Check that your school name matches the official name.",
                        "gpt_content": "N/A",
                    }
                ),
            }
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=os.environ["TABROOM_SUMMARY_LAMBDA_NAME"],
            InvocationType="Event",
            Payload=json.dumps(parsed_body),
        )
        # Write a placeholder file to S3
        s3_client.put_object(
            Body="Placeholder during generation.",
            Bucket=bucket_name,
            Key=f"{tournament_id}/placeholder.txt",
        )
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps(
                {
                    "file_content": "File does not exist, will attempt to generate it. Check back in about 15 minutes.",
                    "gpt_content": "N/A",
                }
            ),
        }
