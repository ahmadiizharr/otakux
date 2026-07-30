import boto3

from .config import settings

s3 = boto3.client(
    "s3",
    endpoint_url=settings.r2_endpoint,
    aws_access_key_id=settings.r2_access_key_id,
    aws_secret_access_key=settings.r2_secret_access_key,
    region_name="auto",
)


def upload_file(key: str, data: bytes, content_type: str | None = None) -> None:
    extra_args = {"ContentType": content_type} if content_type else {}
    s3.put_object(Bucket=settings.r2_bucket, Key=key, Body=data, **extra_args)


def presigned_download_url(key: str, expires_in: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_file(key: str) -> None:
    s3.delete_object(Bucket=settings.r2_bucket, Key=key)
