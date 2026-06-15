"""Always-on ST3GG-inspired defensive scanning adapter."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar"}


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts if count)


def _magic_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith(b"PK\x03\x04"):
        return "zip"
    if data.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7z"
    if data.startswith(b"Rar!\x1a\x07"):
        return "rar"
    if data.startswith(b"%PDF-"):
        return "pdf"
    return "unknown"


def _expected_magic(extension: str) -> str | None:
    return {
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".webp": "webp",
        ".gif": "gif",
        ".bmp": "bmp",
        ".zip": "zip",
        ".7z": "7z",
        ".rar": "rar",
    }.get(extension)


def _png_trailing_data(target: Path, size_bytes: int) -> bool:
    if size_bytes > 5_000_000:
        return False
    data = target.read_bytes()
    marker = b"IEND\xaeB`\x82"
    idx = data.rfind(marker)
    return idx >= 0 and idx + len(marker) < len(data)


def scan_file(path: str | None) -> dict[str, Any]:
    purification_actions = [
        "strip metadata before export",
        "truncate PNG after IEND when needed",
        "run LSB statistical review",
        "recompress JPEG/WebP derivative for public export",
    ]
    if not path:
        return {
            "status": "idle",
            "scanner": "ST3GG defensive adapter",
            "findings": ["No upload selected. Always-on scanner ready."],
            "purification_actions": purification_actions,
            "export_gate": "pending",
            "payload_excerpt": None,
        }

    target = Path(path)
    if not target.exists() or not target.is_file():
        return {
            "status": "error",
            "scanner": "ST3GG defensive adapter",
            "findings": ["File path is unavailable to scanner."],
            "purification_actions": purification_actions,
            "export_gate": "blocked",
            "payload_excerpt": None,
        }

    size_bytes = target.stat().st_size
    with target.open("rb") as handle:
        sample = handle.read(65536)
    entropy = round(_entropy(sample), 3)
    extension = target.suffix.lower()
    magic = _magic_type(sample)
    expected_magic = _expected_magic(extension)
    review_reasons: list[str] = []
    findings = [
        f"extension={extension or 'none'}",
        f"magic={magic}",
        f"size_bytes={size_bytes}",
        f"entropy_sample={entropy}",
    ]
    if entropy > 7.7:
        review_reasons.append("high entropy sample; review metadata/embedded payload risk")
    if extension in IMAGE_EXTENSIONS:
        findings.append("image file queued for metadata and LSB review")
        if expected_magic and magic != expected_magic:
            review_reasons.append("image extension does not match detected file signature")
    if extension == ".png" and magic == "png" and _png_trailing_data(target, size_bytes):
        review_reasons.append("PNG contains trailing data after IEND marker")
    if extension in ARCHIVE_EXTENSIONS or magic in {"zip", "7z", "rar"}:
        review_reasons.append("archive upload requires explicit review before export")
    if expected_magic is None and magic in {"zip", "7z", "rar"}:
        review_reasons.append("archive signature found without matching extension")

    findings.extend(review_reasons)
    status = "review" if review_reasons else "pass"
    return {
        "status": status,
        "scanner": "ST3GG defensive adapter",
        "findings": findings,
        "purification_actions": purification_actions,
        "export_gate": "clear" if status == "pass" else "blocked",
        "size_bytes": size_bytes,
        "extension": extension or "none",
        "magic": magic,
        "entropy_sample": entropy,
        "payload_excerpt": None,
    }
