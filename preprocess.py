"""
# Topex AI Analyst — Audio Preprocessor
#
# Why stoic #4 — Качество распознавания на узбекском
# Чистим шум, нормализуем, конвертируем — чтобы Whisper/Gemini слышали чётче.
"""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger("preprocess")

# Максимальный размер для одного куска при сплите (20 мин)
MAX_SPLIT_SECONDS = 20 * 60


def preprocess(input_path: Path, output_path: Path | None = None) -> Path:
    """
    Предобработка аудио для улучшения ASR:

    1. Конвертация в 16kHz / mono / s16
    2. High-pass фильтр (убираем гул ниже 80 Гц)
    3. Low-pass фильтр (убираем верхние шумы выше 8 кГц)
    4. Нормализация громкости (усиливаем тихие фрагменты)
    5. Noise gate (подавляем паузы)

    Возвращает путь к обработанному файлу.
    """
    if output_path is None:
        output_path = input_path.with_stem(input_path.stem + "_preprocessed").with_suffix(".wav")

    # Качество: 80% звонков — телефонное аудио (8кГц), не надо вытягивать выше
    filter_chain = (
        "highpass=f=80,"
        "lowpass=f=8000,"
        "volume=2.0,"
        "afftdn=nf=-25"  # Neural noise reduction (FFT-based)
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-ar", "16000",         # 16 kHz — золотой стандарт для Whisper
        "-ac", "1",             # Моно
        "-sample_fmt", "s16",   # 16-bit
        "-af", filter_chain,
        str(output_path),
    ]

    try:
        log.info("Предобработка: %s -> %s", input_path.name, output_path.name)
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        size_kb = output_path.stat().st_size // 1024
        log.info("Готово: %s (%d КБ)", output_path.name, size_kb)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            FileNotFoundError, OSError) as e:
        # ffmpeg может отсутствовать на сервере (FileNotFoundError), зависнуть
        # (TimeoutExpired) или упасть — в любом случае не валим весь разбор звонка,
        # а отдаём оригинал аудио дальше в распознавание.
        detail = (
            e.stderr[:200].decode(errors="replace")
            if isinstance(e, subprocess.CalledProcessError) and e.stderr
            else str(e)
        )
        log.warning("Предобработка не удалась (%s), использую оригинал: %s",
                     detail, input_path.name)
        return input_path

    return output_path


def split_audio(input_path: Path, max_seconds: int = MAX_SPLIT_SECONDS) -> list[Path]:
    """
    Режет аудио на куски по max_seconds, если длиннее.
    Возвращает список путей к кускам.
    """
    duration = _get_duration(input_path)
    if duration is None or duration <= max_seconds:
        return [input_path]

    stem = input_path.stem
    parent = input_path.parent
    chunks: list[Path] = []

    log.info("Сплит: %s (%d сек) → куски по %d сек", input_path.name, duration, max_seconds)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-f", "segment",
        "-segment_time", str(max_seconds),
        "-c", "copy",
        str(parent / f"{stem}_chunk_%03d{input_path.suffix}"),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)

    for f in sorted(parent.glob(f"{stem}_chunk_*{input_path.suffix}")):
        chunks.append(f)

    if not chunks:
        chunks.append(input_path)

    return chunks


def cleanup_chunks(chunks: list[Path], exclude: Path | None = None) -> None:
    """Удаляет временные чанки после обработки."""
    for ch in chunks:
        if ch != exclude:
            ch.unlink(missing_ok=True)


def _get_duration(path: Path) -> int | None:
    """Возвращает длительность аудио в секундах через ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
        return int(float(result.stdout.strip()))
    except Exception as e:
        log.warning("Не удалось определить длительность %s: %s", path.name, e)
        return None
