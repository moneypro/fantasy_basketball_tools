"""AWS SES email utilities for sending emails."""
import os
from typing import List, Dict, Any

import boto3
from botocore.exceptions import ClientError

from common.io import get_file_content_from_crendential_folder, find_configs_folder

SENDER: str = "Fantasy Basketball <fantasybasketball@chenghong.info>"

# Load recipients from config file
with open(os.path.join(find_configs_folder(), "recipient_emails.txt")) as f:
    RECIPIENTS: List[str] = f.readlines()

# AWS Region for SES
AWS_REGION: str = "us-west-2"


def send_email(subject: str, body: str) -> None:
    """Send an email via AWS SES.
    
    Args:
        subject: The email subject line
        body: The email body text (will be wrapped in HTML)
        
    Raises:
        ClientError: If the email fails to send
    """
    # Build HTML version of the email
    body_html: str = """<html>
    <head></head>
    <body>
      <p>{}</p>
    </body>
    </html>
                """.format(body)

    charset: str = "UTF-8"

    # Create SES client
    client: Any = boto3.client(
        'ses',
        aws_access_key_id=get_file_content_from_crendential_folder("email_access_key_id.txt"),
        aws_secret_access_key=get_file_content_from_crendential_folder("email_secret_access_key.secret"),
        region_name=AWS_REGION
    )

    # Try to send the email
    try:
        response: Dict[str, Any] = client.send_email(
            Destination={
                'ToAddresses': RECIPIENTS,
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html,
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body,
                    },
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject,
                },
            },
            Source=SENDER,
        )
        print("Email sent! Message ID:"),
        print(response['MessageId'])
    except ClientError as e:
        print(e.response['Error']['Message'])
