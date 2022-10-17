import boto3
from botocore.exceptions import ClientError

# Replace sender@example.com with your "From" address.
# This address must be verified with Amazon SES.
from common.io import get_single_line_string_from_file, get_file_content_from_crendential_folder

SENDER = "Fantasy Basketball <fantasybasketball@chenghong.info>"

# Replace recipient@example.com with a "To" address. If your account
# is still in the sandbox, this address must be verified.
RECIPIENT = "money.pro.ch@gmail.com"

# If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
AWS_REGION = "us-west-2"


def send_email(subject, body):
    # The subject line for the email.

    # The email body for recipients with non-HTML email clients.

    # The HTML body of the email.
    body_html = """<html>
    <head></head>
    <body>
      <p>{}</p>
    </body>
    </html>
                """.format(body)

    # The character encoding for the email.
    charset = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',
                          aws_access_key_id=get_file_content_from_crendential_folder("email_access_key_id.txt"),
                          aws_secret_access_key=get_file_content_from_crendential_folder(
                              "email_secret_access_key.secret"),
                          region_name=AWS_REGION)

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
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
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
