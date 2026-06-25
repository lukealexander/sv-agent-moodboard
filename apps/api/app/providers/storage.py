"""Asset storage backends.

``LocalStorage`` (dev) writes to a directory and has no public URL — the API serves
those assets itself behind auth. ``S3Storage`` (prod) writes to a bucket and returns a
presigned URL. Generated HTML inlines its images as data URIs regardless, so the
shareable file never depends on these URLs being reachable.
"""

import abc
import mimetypes
import pathlib


class Storage(abc.ABC):
    @abc.abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abc.abstractmethod
    def get(self, key: str) -> tuple[bytes, str]:
        """Return ``(data, content_type)``. Raises ``FileNotFoundError`` if absent."""

    def url(self, key: str) -> str | None:
        """A directly-fetchable URL, or None when the API must serve the asset itself."""
        return None


def _guess_type(key: str) -> str:
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


class LocalStorage(Storage):
    def __init__(self, root: str) -> None:
        self.root = pathlib.Path(root)

    def _path(self, key: str) -> pathlib.Path:
        # Keys are app-generated (uuid/index) — never user input — but guard anyway.
        safe = key.replace("..", "_")
        return self.root / safe

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> tuple[bytes, str]:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes(), _guess_type(key)


class S3Storage(Storage):
    def __init__(self, bucket: str, prefix: str = "moodboards") -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def _client(self):  # lazy: boto3 only needed when S3 is configured
        import boto3

        return boto3.client("s3")

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client().put_object(
            Bucket=self.bucket,
            Key=self._full_key(key),
            Body=data,
            ContentType=content_type,
        )

    def get(self, key: str) -> tuple[bytes, str]:
        obj = self._client().get_object(Bucket=self.bucket, Key=self._full_key(key))
        return obj["Body"].read(), obj.get("ContentType", _guess_type(key))

    def url(self, key: str) -> str | None:
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self._full_key(key)},
            ExpiresIn=3600 * 24,
        )
