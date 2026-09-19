#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sync all RetroHub release assets directly to Cloudflare R2.

Usage:
    export R2_ACCESS_KEY_ID="your_access_key"
    export R2_SECRET_ACCESS_KEY="your_secret_key"
    python3 _src/sync_to_r2.py

Or pass credentials via flags:
    python3 _src/sync_to_r2.py --access-key ... --secret-key ...

Options:
    --dry-run       List files to sync without uploading
    --limit N       Only sync first N files (for testing)
    --local-only    Only sync files present locally on disk
"""

import argparse
import datetime
import getpass
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "nguyenxuanhoa493/repohubtool"
RELEASE_TAG = "assets"

DEFAULT_ACCOUNT_ID = "d37907be82acc99cee6820afdf4203fa"
DEFAULT_BUCKET = "retrohub"
DEFAULT_PUBLIC_BASE = "https://cdn.xuanhoa493.com"
DEFAULT_REGION = "auto"


def load_dotenv():
    """Loads key-value pairs from .env into os.environ if not already set."""
    env_path = os.path.join(ROOT, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


load_dotenv()


# ---------------------------------------------------------------------------
# S3 / SigV4 Pure-Python Client (Zero dependencies fallback)
# ---------------------------------------------------------------------------

class R2PureClient:
    """Minimal S3-compatible client using SigV4 and urllib."""

    def __init__(self, account_id, bucket, access_key, secret_key, region="auto"):
        self.account_id = account_id
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.host = f"{account_id}.r2.cloudflarestorage.com"
        self.endpoint = f"https://{self.host}"

    def _sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, date_stamp):
        k_date = self._sign(("AWS4" + self.secret_key).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, self.region)
        k_service = self._sign(k_region, "s3")
        return self._sign(k_service, "aws4_request")

    def _build_request(self, method, key, body=b"", content_type=None):
        canonical_uri = f"/{self.bucket}/{urllib.parse.quote(key, safe='-_.~/')}"
        now = datetime.datetime.now(datetime.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        payload_hash = hashlib.sha256(body).hexdigest()

        headers = {
            "host": self.host,
            "x-amz-date": amz_date,
            "x-amz-content-sha256": payload_hash,
        }
        if content_type:
            headers["content-type"] = content_type
        if body:
            headers["content-length"] = str(len(body))

        # Build Canonical Headers
        sorted_keys = sorted(headers.keys())
        canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted_keys)
        signed_headers = ";".join(sorted_keys)

        canonical_request = "\n".join([
            method,
            canonical_uri,
            "",  # query string
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        # String to sign
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])

        signing_key = self._get_signature_key(date_stamp)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        auth_header = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        headers["Authorization"] = auth_header

        req_url = f"{self.endpoint}{canonical_uri}"
        req = urllib.request.Request(req_url, data=body if method in ("PUT", "POST") else None, headers=headers, method=method)
        return req

    def head_object(self, key):
        """Returns object size in bytes if exists, else None."""
        req = self._build_request("HEAD", key)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                cl = resp.headers.get("Content-Length")
                return int(cl) if cl else 0
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except Exception:
            return None

    def put_object(self, key, data, content_type="application/octet-stream"):
        """Uploads binary data to R2."""
        req = self._build_request("PUT", key, body=data, content_type=content_type)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status in (200, 201, 204)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", "replace")
            print(f"\n[Lỗi HTTP {e.code}] {err_body}")
            return False


# ---------------------------------------------------------------------------
# Boto3 Client Adapter (Optional)
# ---------------------------------------------------------------------------

class R2BotoClient:
    def __init__(self, account_id, bucket, access_key, secret_key, region="auto"):
        import boto3
        from botocore.config import Config
        self.bucket = bucket
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def head_object(self, key):
        from botocore.exceptions import ClientError
        try:
            resp = self.s3.head_object(Bucket=self.bucket, Key=key)
            return resp.get("ContentLength", 0)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return None
            raise

    def put_object(self, key, data, content_type="application/octet-stream"):
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True


def get_r2_client(account_id, bucket, access_key, secret_key):
    try:
        import boto3
        return R2BotoClient(account_id, bucket, access_key, secret_key)
    except ImportError:
        return R2PureClient(account_id, bucket, access_key, secret_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def guess_mime(name):
    if name.endswith(".tar.gz") or name.endswith(".sqlite3.gz"):
        return "application/gzip"
    if name.endswith(".zip"):
        return "application/zip"
    if name.endswith(".json"):
        return "application/json"
    mime, _ = mimetypes.guess_type(name)
    return mime or "application/octet-stream"


def fetch_github_assets():
    """Fetches list of all assets in GitHub Release tag 'assets'."""
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{RELEASE_TAG}"
    req = urllib.request.Request(url, headers={"User-Agent": "RetroHub-R2-Sync"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            return data.get("assets", [])
    except Exception as e:
        print(f"Không thể đọc danh sách assets từ GitHub: {e}")
        return []


def find_local_file(filename):
    """Checks if the asset file exists in local workspace."""
    search_paths = [
        os.path.join(ROOT, "Themes", "zips", filename),
        os.path.join(ROOT, "EmuIcons", "zips", filename),
        os.path.join(ROOT, "emus", filename),
        os.path.join(ROOT, "catalog", filename),
        os.path.join(ROOT, filename),
    ]
    for p in search_paths:
        if os.path.isfile(p):
            return p
    return None


def check_cdn_public(url):
    """Performs a quick HTTP HEAD check on the public CDN domain."""
    req = urllib.request.Request(url, headers={"User-Agent": "RetroHub-R2-Sync"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                cl = resp.headers.get("Content-Length")
                return int(cl) if cl else 0
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main Sync Flow
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Sync RetroHub assets to Cloudflare R2")
    parser.add_argument("--account-id", default=os.environ.get("R2_ACCOUNT_ID") or DEFAULT_ACCOUNT_ID)
    parser.add_argument("--bucket", default=os.environ.get("R2_BUCKET") or DEFAULT_BUCKET)
    parser.add_argument("--public-base", default=os.environ.get("R2_PUBLIC_BASE") or DEFAULT_PUBLIC_BASE)
    parser.add_argument("--access-key", default=os.environ.get("R2_ACCESS_KEY_ID"))
    parser.add_argument("--secret-key", default=os.environ.get("R2_SECRET_ACCESS_KEY"))
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê file cần sync")
    parser.add_argument("--limit", type=int, default=0, help="Giới hạn số file tải lên (dùng để test)")
    parser.add_argument("--local-only", action="store_true", help="Chỉ sync các file có sẵn ở local")
    args = parser.parse_args()

    print("==================================================")
    print("      RetroHub Cloudflare R2 Asset Sync           ")
    print("==================================================")
    print(f"Bucket      : {args.bucket}")
    print(f"Account ID  : {args.account_id}")
    print(f"CDN Base    : {args.public_base}")

    access_key = args.access_key
    secret_key = args.secret_key

    if not args.dry_run:
        if not access_key:
            access_key = input("Nhập R2 Access Key ID: ").strip()
        if not secret_key:
            secret_key = getpass.getpass("Nhập R2 Secret Access Key: ").strip()

        if not access_key or not secret_key:
            print("LỖI: Cần cung cấp Access Key ID và Secret Access Key để upload.")
            sys.exit(1)

    r2 = None
    if not args.dry_run:
        r2 = get_r2_client(args.account_id, args.bucket, access_key, secret_key)
        client_type = "Boto3" if isinstance(r2, R2BotoClient) else "Pure-Python SigV4"
        print(f"Client mode : {client_type}")

    print("\n[1/3] Đang tải danh sách tài nguyên từ GitHub Release 'assets'...")
    gh_assets = fetch_github_assets()
    print(f"Tìm thấy {len(gh_assets)} file trên GitHub.")

    # Đảm bảo catalog/roms_store.sqlite3.gz có trong danh sách
    asset_dict = {a["name"]: a for a in gh_assets}
    local_sqlite_gz = os.path.join(ROOT, "catalog", "roms_store.sqlite3.gz")
    if os.path.isfile(local_sqlite_gz) and "roms_store.sqlite3.gz" not in asset_dict:
        asset_dict["roms_store.sqlite3.gz"] = {
            "name": "roms_store.sqlite3.gz",
            "size": os.path.getsize(local_sqlite_gz),
            "browser_download_url": None,
        }

    all_items = list(asset_dict.values())
    if args.limit > 0:
        all_items = all_items[:args.limit]
        print(f"Đã giới hạn còn {len(all_items)} file theo cờ --limit {args.limit}.")

    total_files = len(all_items)
    print(f"\n[2/3] Bắt đầu đồng bộ {total_files} file lên Cloudflare R2...")

    uploaded = 0
    skipped = 0
    failed = 0
    total_bytes = 0

    for idx, item in enumerate(all_items, 1):
        name = item["name"]
        expected_size = item.get("size", 0)
        mime = guess_mime(name)
        size_mb = expected_size / (1024 * 1024)

        if args.dry_run:
            print(f"[{idx}/{total_files}] DRY-RUN: {name} ({size_mb:.2f} MB)")
            continue

        # 1. Kiểm tra xem file đã có trên R2 / CDN chưa
        cdn_url = f"{args.public_base.rstrip('/')}/{name}"
        cdn_size = check_cdn_public(cdn_url)
        if cdn_size is not None and cdn_size == expected_size:
            print(f"[{idx}/{total_files}] SKIP (Đã có trên CDN): {name} ({size_mb:.2f} MB)")
            skipped += 1
            continue

        # Nếu check qua CDN chưa thấy, check trực tiếp qua S3 API
        try:
            r2_size = r2.head_object(name)
            if r2_size is not None and (expected_size == 0 or r2_size == expected_size):
                print(f"[{idx}/{total_files}] SKIP (Đã có trên R2): {name} ({size_mb:.2f} MB)")
                skipped += 1
                continue
        except Exception as e:
            print(f"[{idx}/{total_files}] Cảnh báo khi check {name}: {e}")

        # 2. Lấy dữ liệu file (ưu tiên đọc từ local, nếu không có thì tải từ GitHub)
        local_path = find_local_file(name)
        data = None
        source_label = ""

        if local_path and os.path.isfile(local_path):
            source_label = "Local"
            with open(local_path, "rb") as f:
                data = f.read()
        elif not args.local_only and item.get("browser_download_url"):
            source_label = "GitHub"
            t0 = time.time()
            gh_url = item["browser_download_url"]
            print(f"[{idx}/{total_files}] Tải từ GitHub: {name} ({size_mb:.2f} MB)...", end="", flush=True)
            req = urllib.request.Request(gh_url, headers={"User-Agent": "RetroHub-R2-Sync"})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = resp.read()
                print(f" xong ({time.time() - t0:.1f}s)")
            except Exception as e:
                print(f" THẤT BẠI: {e}")
                failed += 1
                continue
        else:
            print(f"[{idx}/{total_files}] BỎ QUA: Không tìm thấy file ở local và không có link tải.")
            skipped += 1
            continue

        # 3. Đẩy lên Cloudflare R2
        t0 = time.time()
        print(f"[{idx}/{total_files}] Upload R2 [{source_label}]: {name} ({len(data) / 1024 / 1024:.2f} MB)...", end="", flush=True)
        try:
            ok = r2.put_object(name, data, content_type=mime)
            dur = time.time() - t0
            if ok:
                uploaded += 1
                total_bytes += len(data)
                speed = (len(data) / 1024 / 1024) / max(dur, 0.001)
                print(f" THÀNH CÔNG ({dur:.1f}s, {speed:.2f} MB/s)")
            else:
                failed += 1
                print(" THẤT BẠI")
        except Exception as e:
            failed += 1
            print(f" LỖI: {e}")

    print("\n[3/3] Kết quả đồng bộ:")
    print("--------------------------------------------------")
    print(f"Đã upload mới: {uploaded} file ({total_bytes / 1024 / 1024:.2f} MB)")
    print(f"Đã có sẵn    : {skipped} file")
    print(f"Thất bại     : {failed} file")
    print(f"CDN Base     : {args.public_base.rstrip('/')}/")
    print("==================================================")

    if uploaded > 0 or skipped > 0:
        test_file = all_items[0]["name"]
        print(f"\nKiểm tra thử link CDN: {args.public_base.rstrip('/')}/{test_file}")


if __name__ == "__main__":
    main()
