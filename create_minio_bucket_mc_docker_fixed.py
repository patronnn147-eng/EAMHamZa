import subprocess

def create_bucket_via_docker():
    bucket = "attachments"
    try:
        # Set MinIO alias
        subprocess.run([
            "docker", "exec", "asset_management_minio", "mc", "alias", "set", "local", "http://localhost:9000",
            "--api", "s3v4",
            "--access-key", "minioadmin",
            "--secret-key", "minioadmin"
        ], check=True, capture_output=True, text=True)
        # Create bucket
        subprocess.run([
            "docker", "exec", "asset_management_minio", "mc", "mb", "local/attachments"
        ], check=True, capture_output=True, text=True)
        print(f"Bucket '{bucket}' created/exists via MinIO container.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create bucket: {e.stderr}")

if __name__ == "__main__":
    create_bucket_via_docker()
