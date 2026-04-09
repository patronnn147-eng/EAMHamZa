#!/usr/bin/env python3
import asyncio
import httpx
import os

async def create_bucket():
    url = "http://localhost:9000"
    access_key = os.getenv("OSS_API_KEY", "minioadmin")
    bucket_name = "attachments"

    # MinIO CreateBucket via simple PUT
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{url}/{bucket_name}",
            headers={"Authorization": f"AWS4-HMAC-SHA256 Credential={access_key}/us-east-1/s3/aws4_request"}
        )
        if resp.status_code in (200, 409):
            print(f"Bucket '{bucket_name}' ensured.")
        else:
            print(f"Failed to create bucket: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    asyncio.run(create_bucket())
