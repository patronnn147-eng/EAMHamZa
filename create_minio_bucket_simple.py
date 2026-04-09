import httpx
import datetime

def create_bucket():
    bucket = "attachments"
    url = f"http://localhost:9000/{bucket}"
    now = datetime.datetime.utcnow()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    auth = f"AWS4-HMAC-SHA256 Credential=minioadmin/{now.strftime('%Y%m%d')}/us-east-1/s3/aws4_request"

    resp = httpx.put(
        url,
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

if __name__ == "__main__":
    create_bucket()
