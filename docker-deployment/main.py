import argparse
import boto3
import logging
import os
from tabroom_summary import tabroom_summary

"""
This is the main routine for the tabroom_summary Lambda. It will query Tabroom.com for the tournament results and then
create a PROMPT that can be passed to an LLM to generate a summary of a school's results at the tournament.

Unlike previous versions, this version will NOT ever directly send LLM prompts to an LLM. That behavior now occurs synchronously at user-request time.
"""

# Set log level
logging.basicConfig(level=logging.INFO)

DATA_BUCKET = "tabroom-summaries-data-bucket"  # TODO - remove after testing


def handler(event, context):
    running_outside_of_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None
    print(event)
    # Send ol' Benjamin an email to let him know that people are using the service
    try:
        boto3.client("sns").publish(
            TopicArn=os.environ["SNS_TOPIC_ARN"],
            Message=f"Running tabroom_summary for {event['tournament']}; requested school is {event['school']}",
        )
    except Exception:
        logging.error("Error publishing to SNS")

    # Generate a Tabroom summary
    tournament_id = event["tournament"]
    response = tabroom_summary.main(
        tournament_id=tournament_id,
        data_bucket=os.getenv("DATA_BUCKET_NAME", DATA_BUCKET),
    )

    # Save the result outputs
    # If we're not in Lambda, assume we're in Windows
    if running_outside_of_lambda:
        # Make the directories as needed
        for school_name in response.keys():
            os.makedirs(f"{tournament_id}/{school_name}", exist_ok=True)
            if "gpt_prompt" in response[school_name]:
                with open(f"{tournament_id}/{school_name}/gpt_prompt.txt", "w") as f:
                    f.write(response[school_name]["gpt_prompt"])
    else:
        # Save the tournament results to S3
        s3_client = boto3.client("s3")
        bucket_name = os.environ["DATA_BUCKET_NAME"]
        for school_name in response.keys():
            if "gpt_prompt" in response[school_name]:
                s3_client.put_object(
                    Body=response[school_name]["gpt_prompt"],
                    Bucket=bucket_name,
                    Key=f"{tournament_id}/{school_name}/gpt_prompt.txt",
                )
            if "numbered_list_response" in response[school_name]:
                s3_client.put_object(
                    Body=response[school_name]["numbered_list_response"],
                    Bucket=bucket_name,
                    Key=f"{tournament_id}/{school_name}/numbered_list_response.txt",
                )
        try:
            # Delete the placeholder to signal to the Lambda that execution is complete
            s3_client.delete_object(
                Bucket=bucket_name, Key=f"{tournament_id}/placeholder.txt"
            )
        except Exception:
            pass


if __name__ == "__main__":
    os.environ["SNS_TOPIC_ARN"] = (
        "arn:aws:sns:us-east-1:238589881750:summary_generation_topic"
    )
    # Create an argparse for tournament ID and readonly
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--tournament-id",
        help="Tournament ID (typically a 5-digit number) of the tournament you want to generate results for.",
        required=False,  # TODO - require again
        default="20134",
    )
    args = parser.parse_args()
    tournament_id = args.tournament_id
    event = {
        "tournament": tournament_id,  # "30799",  # "29810",  # "20134",
    }
    handler(event, {})
