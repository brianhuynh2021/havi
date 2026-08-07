"""Kiểm magic bytes để xác minh nội dung file khớp loại đã khai.

Vì sao cần: presigned POST **không** kiểm nội dung. S3/MinIO lưu object với
`Content-Type` lấy từ field đã ký trong ticket, không phải từ bytes thật — nên
client hoàn toàn có thể xin ticket cho `image/jpeg` rồi POST một file thực thi,
và object đó sẽ nằm trong bucket với metadata `image/jpeg`. Bucket media là
public-read, nên không kiểm nội dung nghĩa là biến nó thành nơi host file bất kỳ.

Đây là kiểm ở mức chữ ký định dạng, không phải quét malware. Nó chặn được việc
đổi tên file để lách, không chặn được ảnh hợp lệ nhưng nhúng payload.
"""

from core.enums import MediaType

# (offset, chữ ký) — một định dạng có thể có nhiều biến thể.
_SIGNATURES: dict[MediaType, tuple[tuple[int, bytes], ...]] = {
    MediaType.IMAGE: (
        (0, b"\xff\xd8\xff"),  # JPEG
        (0, b"\x89PNG\r\n\x1a\n"),  # PNG
        (0, b"RIFF"),  # WebP (kèm 'WEBP' ở offset 8, kiểm bên dưới)
        (4, b"ftyp"),  # HEIC/HEIF — box 'ftyp' ở offset 4
    ),
    MediaType.AUDIO: (
        (0, b"ID3"),  # MP3 có ID3 tag
        (0, b"\xff\xfb"),  # MP3 frame sync
        (0, b"\xff\xf3"),
        (0, b"\xff\xf2"),
        (0, b"RIFF"),  # WAV
        (0, b"OggS"),  # Ogg
        (4, b"ftyp"),  # M4A/AAC trong container MP4
    ),
    MediaType.VIDEO: (
        (4, b"ftyp"),  # MP4/MOV
        (0, b"RIFF"),  # AVI
        (0, b"\x1a\x45\xdf\xa3"),  # Matroska/WebM
    ),
}

# Đủ để chứa chữ ký dài nhất (HEIC/MP4 cần tới offset 12).
PREFIX_BYTES_NEEDED = 16


def matches_media_type(prefix: bytes, media_type: MediaType) -> bool:
    for offset, signature in _SIGNATURES.get(media_type, ()):
        if prefix[offset : offset + len(signature)] == signature:
            # RIFF dùng chung cho WebP/WAV/AVI — phân biệt bằng subtype ở offset 8.
            if signature == b"RIFF":
                subtype = prefix[8:12]
                if media_type == MediaType.IMAGE and subtype != b"WEBP":
                    continue
                if media_type == MediaType.AUDIO and subtype != b"WAVE":
                    continue
                if media_type == MediaType.VIDEO and subtype != b"AVI ":
                    continue
            return True
    return False
