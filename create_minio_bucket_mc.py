#!/usr/bin/env python3
import subprocess
import sys

def create_bucket_with_mc():
    bucket = "attachments"
    try:
        # Try using MinIO client (mc) if available
        subprocess.run([
            "mc", "alias", "set", "local", "http://localhost:9000",
            "--api", "s3v4",
            "--access-key", "minioadmin",
            "--secret-key", "minioadmin"
        ], check=True)
        subprocess.run(["mc", "mb", "local/attachments"], check=True)
        print(f"Bucket '{bucket}' created/exists.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: simple HTTP PUT with proper headers
        import httpx
        import datetime as dt

        now = dt.datetime.utcnow(dt.timezone.utc)
        date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        auth = f"AWS4-HMAC-SHA256 Credential=minioadmin/{now.strftime('%Y%m%d')}/us-east-1/s3/aws4_request"

        async def create():
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"http://localhost:9000/{bucket}",
                    headers={
                        "Authorization": auth,
                        "Date": date_str,
                        "Host": "localhost:9000"
                    }
                )
                if resp.status_code in (200, 409):
                    print(f"Bucket '{bucket}' ensured.")
                else:
                    print(f"Failed: {resp.status_code} {resp.text}")

        import asyncio
        asyncio.run(create())

if __name__ == "__main__":
    create_bucket_with_mc()
