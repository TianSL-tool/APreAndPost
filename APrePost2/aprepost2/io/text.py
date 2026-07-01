from __future__ import annotations

from pathlib import Path


def detect_text_encoding(path: str | Path, sample_size: int = 65536) -> str:
    with Path(path).open("rb") as stream:
        sample = stream.read(sample_size)
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin1"


def clean_control_lines(path: str | Path) -> list[str]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"控制文件不存在：{source}")
    encoding = detect_text_encoding(source)
    result: list[str] = []
    with source.open("r", encoding=encoding) as stream:
        for raw_line in stream:
            line = raw_line.split("//", 1)[0].strip()
            if line:
                result.append(line)
    return result
