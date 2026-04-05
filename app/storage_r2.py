import os
try:
    import boto3
    from botocore.client import Config
except Exception:  # boto3 not installed or import error
    boto3 = None
    Config = None

def get_s3_client():
    if boto3 is None or Config is None:
        raise RuntimeError("boto3 is not installed. Install it with 'pip install boto3' to use Cloudflare R2 storage.")
    endpoint_url = os.getenv('R2_ENDPOINT')
    access_key = os.getenv('R2_ACCESS_KEY_ID')
    secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
    if not all([endpoint_url, access_key, secret_key]):
        raise RuntimeError('R2 credentials not configured in environment')
    session = boto3.session.Session()
    client = session.client(
        service_name='s3',
        region_name='auto',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
    )
    return client

def upload_to_r2(file_obj, bucket, object_key, content_type='application/pdf'):
    client = get_s3_client()
    # Read file content
    file_obj.seek(0)
    data = file_obj.read()
    client.put_object(Bucket=bucket, Key=object_key, Body=data, ContentType=content_type)
    # Generate a presigned URL for retrieval (7 days default here)
    url = client.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket, 'Key': object_key},
        ExpiresIn=7 * 24 * 3600
    )
    return url
