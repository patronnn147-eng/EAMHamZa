import subprocess

def create_bucket_via_curl():
    bucket = "attachments"
    try:
        # Use curl inside MinIO container to create bucket (no auth needed for local MinIO)
        result = subprocess.run([
            "docker", "exec", "asset_management_minio", "curl", "-X", "PUT",
            f"http://localhost:9000/{bucket}"
        ], capture_output=True, text=True)
        if result.returncode in (0, 409):
            print(f"Bucket '{bucket}' created/exists.")
        else:
            print(f"Failed to create bucket: {result.stderr}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_bucket_via_curl()
