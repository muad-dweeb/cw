import boto3
import logging
from botocore.exceptions import ClientError
from datetime import datetime
from os import path


def create_new_filename(in_path, overwrite_existing=False):
    """ Save to a new CSV file with an incrementing filename unless overwrite is requested """
    # YYYYMMDD
    now_string = datetime.now().strftime('%Y%m%d')

    full_path = path.expanduser(in_path)

    # Remove any file extension from the path
    full_path = path.splitext(full_path)[0]

    out_path = '{}_{}.csv'.format(full_path, now_string)

    if not overwrite_existing:
        increment = 1
        while path.isfile(out_path):
            out_path = '{}_{}_{}.csv'.format(full_path, now_string, increment)
            increment += 1

    return out_path


def create_logger(caller, debug=False):
    """ General purpose logger with simple configuration """
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    new_logger = logging.getLogger(caller)
    console_handler = logging.StreamHandler()
    log_format = logging.Formatter('%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    new_logger.addHandler(console_handler)
    new_logger.setLevel(log_level)
    # Prevent duplicate log entries if another handler exists downstream: https://stackoverflow.com/a/44426266/3900915
    new_logger.propagate = False
    return new_logger


def upload_file(file_name, bucket, object_name=None):
    """
    Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        raise e
