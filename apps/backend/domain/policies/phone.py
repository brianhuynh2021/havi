"""Chuẩn hoá số điện thoại Việt Nam — nhập 0xxxxxxxxx, lưu dạng +84xxxxxxxxx.

Xem ROADMAP.md "Việt Nam-first": hiển thị lại theo format quen thuộc ở frontend,
backend chỉ lưu và so khớp bằng dạng chuẩn hoá.
"""

import re

_LOCAL_PATTERN = re.compile(r"^0\d{9}$")
_INTL_PATTERN = re.compile(r"^\+84\d{9}$")


class InvalidPhoneNumber(ValueError):
    pass


def normalize_vietnamese_phone(raw: str) -> str:
    value = raw.strip().replace(" ", "")
    if _INTL_PATTERN.match(value):
        return value
    if _LOCAL_PATTERN.match(value):
        return "+84" + value[1:]
    raise InvalidPhoneNumber(f"Số điện thoại không hợp lệ: {raw!r}")
