"""Reproduce the pinned local browser assets from verified npm package archives."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

PACKAGES = [
    ("marked", "18.0.14", "lib/marked.umd.js", "marked.min.js",
     "mBHK6FBHuBAlhgRe88w9F0O1AbwwXJUcQibUbC/QcdTbVGAD7aWza+xt3N6oT/jCZx3/OMeS+8rnuiHZcQ9s7A=="),
    ("dompurify", "3.4.16", "dist/purify.min.js", "purify.min.js",
     "sqo+pNp3qRhCIpbgRi1y8Tgk27Bo2Ry7w0dC1NBeNTdZChWjz9Xb/KOoZbRP/R6pQZ80Qw8YhXw13hWWBbMRnQ=="),
]


def main():
    destination = Path(__file__).resolve().parents[1] / "web" / "vendor"
    destination.mkdir(exist_ok=True)
    manifest = []
    for name, version, member, filename, expected in PACKAGES:
        url = f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz"
        with urllib.request.urlopen(url, timeout=30) as response:
            archive = response.read()
        actual = base64.b64encode(hashlib.sha512(archive).digest()).decode()
        if actual != expected:
            raise ValueError(f"Package integrity check failed: {name}")
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
            data = package.extractfile("package/" + member).read()
            license_data = package.extractfile("package/LICENSE").read()
        (destination / filename).write_bytes(data)
        (destination / (name + ".LICENSE")).write_bytes(license_data)
        manifest.append({"package": name, "version": version, "source": url,
                         "package_integrity": "sha512-" + expected, "file": filename,
                         "sha256": hashlib.sha256(data).hexdigest(),
                         "sri": "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()})
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
