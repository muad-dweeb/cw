import datetime
import os
from argparse import ArgumentParser
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from socket import gethostname

import boto3
from botocore.exceptions import ClientError


class EmailReporterException(BaseException):
    pass


class EmailReporter(object):

    FOOTER = 'This is an automated message. Replies probably won\'t be read in a timely manner.'

    def __init__(self, sender, recipient):
        self.sender = sender
        self.recipient = recipient
        self._client = boto3.client('ses')

    @staticmethod
    def __assemble_report_body_text(metrics_dict, sample_output_list=None):

        # Main body
        text = 'Run Metrics\n'
        for key, value in metrics_dict.items():
            text += '\n{}: {}'.format(key, value)

        # Output sample
        if sample_output_list is not None:
            text += '\n\n----------\n\n'
            text += '\n'.join(sample_output_list)

        # Footer
        text += '\n\n----------\n\n{}'.format(EmailReporter.FOOTER)

        return text

    @staticmethod
    def __assemble_report_body_html(metrics_dict, sample_output_list=None):

        # Main body
        p = ''
        for key, value in metrics_dict.items():
            p += '<b>{}</b>: {}<br>'.format(key, value)

        # Output sample
        if sample_output_list is not None:
            p += '<br><hr><samp>{}</samp><br>'.format('<br>'.join(sample_output_list))

        html = '''
        <html>
        <head></head>
        <body>
        <h1>Run Metrics</h1>
        <p>{}</p>
        <hr>
        <footer><small><i>{}</i></small></footer>
        </body>
        </html>
        '''.format(p, EmailReporter.FOOTER)
        return html

    @staticmethod
    def __assemble_report_subject():
        hostname = gethostname()
        date = datetime.date.today().strftime("%B %d, %Y")
        subject = 'Scrape Report | {} | {}'.format(hostname, date)
        return subject

    def send_report(self, metrics_dict, screenshot=None, sample_output_list=None):
        # The character encoding for the email.
        char_set = "utf-8"

        # Create a multipart/mixed parent container.
        msg = MIMEMultipart('mixed')
        # Add subject, from and to lines.
        msg['Subject'] = self.__assemble_report_subject()
        msg['From'] = self.sender
        msg['To'] = self.recipient

        # Create a multipart/alternative child container.
        msg_body = MIMEMultipart('alternative')

        # Assemble text and html bodies
        body_text = self.__assemble_report_body_text(metrics_dict, sample_output_list)
        body_html = self.__assemble_report_body_html(metrics_dict, sample_output_list)

        # Encode the text and HTML content and set the character encoding. This step is
        # necessary if you're sending a message with characters outside the ASCII range.
        text_part = MIMEText(body_text, 'plain', char_set)
        html_part = MIMEText(body_html, 'html', char_set)

        # Add the text and HTML parts to the child container.
        msg_body.attach(text_part)
        msg_body.attach(html_part)

        if screenshot is not None:

            screenshot_path = os.path.expanduser(screenshot)

            # Define the attachment part and encode it using MIMEApplication.
            att = MIMEApplication(open(screenshot_path, 'rb').read())

            # Add a header to tell the email client to treat this part as an attachment,
            # and to give the attachment a name.
            att.add_header('Content-Disposition', 'attachment', filename=os.path.basename(screenshot_path))

            # Add the attachment to the parent container.
            msg.attach(att)

        # Attach the multipart/alternative child container to the multipart/mixed
        # parent container.
        msg.attach(msg_body)

        try:
            # Provide the contents of the email.
            self._client.send_raw_email(
                Source=self.sender,
                Destinations=[
                    self.recipient
                ],
                RawMessage={
                    'Data': msg.as_string()
                }
            )
        # Raise error if something goes wrong.
        except ClientError as e:
            raise EmailReporterException(e.response['Error']['Message'])


def test(sender_email, recipient_email, screenshot):

    dummy_metrics = {'send_time': datetime.datetime.now(),
                     'test': True,
                     'bogus_metric': 42}

    dummy_output = 'Process finished with exit code 0'

    screenshot_path = os.path.expanduser(screenshot)

    try:
        reporter = EmailReporter(sender=sender_email, recipient=recipient_email)
        reporter.send_report(metrics_dict=dummy_metrics, screenshot=screenshot_path, sample_output_list=dummy_output)
        print('Test succeeded!')
    except EmailReporterException as e:
        print('Test failed: {}'.format(e))


if __name__ == '__main__':
    arg_parser = ArgumentParser(description='Test EmailReporter class')
    arg_parser.add_argument('--sender', required=True)
    arg_parser.add_argument('--recipient', required=True)
    arg_parser.add_argument('--screenshot', required=False)
    args = arg_parser.parse_args()

    test(sender_email=args.sender, recipient_email=args.recipient, screenshot=args.screenshot)
