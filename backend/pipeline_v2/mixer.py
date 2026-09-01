"""FFmpeg-native dubbing mix with ducking, loudness and peak control."""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple, Union


PathLike = Union[str, os.PathLike]


@dataclass(frozen=True)
class FFmpegMixSettings:
    background_gain_db: float = -2.0
    voice_gain_db: float = 1.0
    duck_threshold: float = 0.025
    duck_ratio: float = 8.0
    duck_attack_ms: float = 20.0
    duck_release_ms: float = 300.0
    target_lufs: float = -15.0
    true_peak_dbtp: float = -1.0
    loudness_range: float = 11.0
    voice_chunk_seconds: float = 300.0
    max_inputs_per_pass: int = 64

    def __post_init__(self) -> None:
        if not 0.000001 <= self.duck_threshold <= 1.0:
            raise ValueError("duck_threshold must be between 0 and 1")
        if self.duck_ratio < 1.0:
            raise ValueError("duck_ratio must be at least 1")
        if self.true_peak_dbtp > 0:
            raise ValueError("true_peak_dbtp must not exceed 0")
        if self.voice_chunk_seconds <= 0 or self.max_inputs_per_pass <= 0:
            raise ValueError("Mixer resource limits must be positive")


@dataclass(frozen=True)
class FFmpegMixResult:
    output_path: str
    dub_count: int
    command: Sequence[str]


@dataclass(frozen=True)
class VoiceChunk:
    start_seconds: float
    end_seconds: float
    dubs: Sequence[Mapping[str, Any]]


def _validated_dubs(dubbing_audio_files: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    valid = []
    for item in dubbing_audio_files:
        path = Path(str(item.get("path", "")))
        if not path.is_file():
            continue
        start = float(item.get("start", 0.0))
        if start < 0:
            raise ValueError("Dubbing start time must not be negative")
        valid.append({**dict(item), "path": str(path), "start": start})
    return sorted(valid, key=lambda item: (item["start"], int(item.get("index", 0))))


def plan_voice_chunks(
    dubs: Sequence[Mapping[str, Any]],
    total_duration_seconds: float,
    target_chunk_seconds: float,
) -> List[VoiceChunk]:
    """Cover the timeline without cutting a dub that crosses a target boundary."""

    if total_duration_seconds <= 0 or target_chunk_seconds <= 0:
        raise ValueError("Timeline durations must be positive")
    ordered = sorted(dubs, key=lambda item: float(item.get("start", 0.0)))
    chunks = []
    cursor = 0.0
    position = 0
    while cursor < total_duration_seconds - 0.0001:
        boundary = min(total_duration_seconds, cursor + target_chunk_seconds)
        selected = []
        while position < len(ordered) and float(ordered[position].get("start", 0.0)) < boundary:
            dub = ordered[position]
            selected.append(dub)
            position += 1
            start = float(dub.get("start", 0.0))
            end = float(
                dub.get(
                    "end",
                    start + float(dub.get("actual_audio_duration", 0.0)),
                )
            )
            boundary = min(total_duration_seconds, max(boundary, end))
        # Include overlapping items pulled across the nominal boundary.
        while position < len(ordered) and float(ordered[position].get("start", 0.0)) < boundary:
            dub = ordered[position]
            selected.append(dub)
            position += 1
            start = float(dub.get("start", 0.0))
            end = float(
                dub.get(
                    "end",
                    start + float(dub.get("actual_audio_duration", 0.0)),
                )
            )
            boundary = min(total_duration_seconds, max(boundary, end))
        if boundary <= cursor:
            boundary = min(total_duration_seconds, cursor + target_chunk_seconds)
        chunks.append(VoiceChunk(cursor, boundary, tuple(selected)))
        cursor = boundary
    return chunks


def _probe_duration(path: PathLike, ffprobe_binary: str = "ffprobe") -> float:
    creation_flags = (
        subprocess.CREATE_NO_WINDOW
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
        else 0
    )
    result = subprocess.run(
        [
            ffprobe_binary,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        creationflags=creation_flags,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe duration failed")
    return float(result.stdout.strip())


def _run_ffmpeg(command: Sequence[str], timeout_seconds: float) -> None:
    creation_flags = (
        subprocess.CREATE_NO_WINDOW
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
        else 0
    )
    result = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        creationflags=creation_flags,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-3000:] or "FFmpeg command failed")


def _render_voice_group(
    dubs: Sequence[Mapping[str, Any]],
    chunk_start: float,
    chunk_duration: float,
    output_path: Path,
    settings: FFmpegMixSettings,
    ffmpeg_binary: str,
    timeout_seconds: float,
) -> None:
    command = [ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    labels = []
    for input_index, dub in enumerate(dubs):
        command.extend(["-i", str(dub["path"])])
        delay = max(0, int(round((float(dub["start"]) - chunk_start) * 1000)))
        label = "v{}".format(input_index)
        filters.append(
            "[{}:a]adelay={}:all=1[{}]".format(
                input_index, delay, label
            )
        )
        labels.append("[{}]".format(label))
    if labels:
        filters.append(
            "{}amix=inputs={}:duration=longest:normalize=0,"
            "apad,atrim=duration={:.6f},aformat=sample_rates=44100:channel_layouts=stereo[out]".format(
                "".join(labels), len(labels), chunk_duration
            )
        )
        command.extend(["-filter_complex", ";".join(filters), "-map", "[out]"])
    else:
        command.extend(
            [
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=44100:cl=stereo:d={:.6f}".format(chunk_duration),
                "-map",
                "0:a",
            ]
        )
    command.extend(["-c:a", "flac", str(output_path)])
    _run_ffmpeg(command, timeout_seconds)


def _mix_voice_tracks(
    inputs: Sequence[Path],
    output_path: Path,
    max_inputs: int,
    ffmpeg_binary: str,
    timeout_seconds: float,
) -> None:
    current = list(inputs)
    generation = 0
    while len(current) > 1:
        next_generation = []
        for offset in range(0, len(current), max_inputs):
            group = current[offset : offset + max_inputs]
            target = output_path.parent / "voice-tree-{}-{}.flac".format(
                generation, len(next_generation)
            )
            command = [ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y"]
            for item in group:
                command.extend(["-i", str(item)])
            labels = "".join("[{}:a]".format(i) for i in range(len(group)))
            graph = "{}amix=inputs={}:duration=longest:normalize=0[out]".format(
                labels, len(group)
            )
            command.extend(
                ["-filter_complex", graph, "-map", "[out]", "-c:a", "flac", str(target)]
            )
            _run_ffmpeg(command, timeout_seconds)
            next_generation.append(target)
        current = next_generation
        generation += 1
    if current:
        os.replace(str(current[0]), str(output_path))


def _render_scalable_voice_bus(
    dubs: Sequence[Mapping[str, Any]],
    total_duration: float,
    directory: Path,
    settings: FFmpegMixSettings,
    ffmpeg_binary: str,
    timeout_seconds: float,
) -> Path:
    chunk_paths = []
    for chunk_index, chunk in enumerate(
        plan_voice_chunks(dubs, total_duration, settings.voice_chunk_seconds)
    ):
        duration = chunk.end_seconds - chunk.start_seconds
        groups = [
            list(chunk.dubs[offset : offset + settings.max_inputs_per_pass])
            for offset in range(0, len(chunk.dubs), settings.max_inputs_per_pass)
        ] or [[]]
        group_paths = []
        for group_index, group in enumerate(groups):
            group_path = directory / "chunk-{}-group-{}.flac".format(
                chunk_index, group_index
            )
            _render_voice_group(
                group,
                chunk.start_seconds,
                duration,
                group_path,
                settings,
                ffmpeg_binary,
                timeout_seconds,
            )
            group_paths.append(group_path)
        chunk_path = directory / "chunk-{}.flac".format(chunk_index)
        if len(group_paths) == 1:
            os.replace(str(group_paths[0]), str(chunk_path))
        else:
            _mix_voice_tracks(
                group_paths,
                chunk_path,
                settings.max_inputs_per_pass,
                ffmpeg_binary,
                timeout_seconds,
            )
        chunk_paths.append(chunk_path)

    concat_file = directory / "voice-chunks.ffconcat"
    with concat_file.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("ffconcat version 1.0\n")
        for item in chunk_paths:
            escaped = str(item.resolve()).replace("'", "'\\''")
            handle.write("file '{}'\n".format(escaped))
        handle.flush()
        os.fsync(handle.fileno())
    voice_bus = directory / "voice-bus.flac"
    command = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:a",
        "flac",
        str(voice_bus),
    ]
    _run_ffmpeg(command, timeout_seconds)
    return voice_bus


def build_ffmpeg_mix_command(
    background_audio: PathLike,
    dubbing_audio_files: Iterable[Mapping[str, Any]],
    output_path: PathLike,
    settings: FFmpegMixSettings = None,
    ffmpeg_binary: str = "ffmpeg",
) -> Tuple[List[str], int]:
    config = settings or FFmpegMixSettings()
    background = Path(background_audio)
    if not background.is_file():
        raise FileNotFoundError("Background audio is missing: {}".format(background))
    dubs = _validated_dubs(dubbing_audio_files)
    command = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(background),
    ]
    for dub in dubs:
        command.extend(["-i", dub["path"]])

    limiter_linear = 10 ** (config.true_peak_dbtp / 20.0)
    filters = []
    if dubs:
        voice_labels = []
        for input_index, dub in enumerate(dubs, 1):
            delay_ms = max(0, int(round(dub["start"] * 1000)))
            label = "voice_{}".format(input_index)
            filters.append(
                "[{}:a]adelay={}:all=1,volume={}dB[{}]".format(
                    input_index, delay_ms, config.voice_gain_db, label
                )
            )
            voice_labels.append("[{}]".format(label))
        if len(voice_labels) == 1:
            filters.append("{}anull[voice_bus]".format(voice_labels[0]))
        else:
            filters.append(
                "{}amix=inputs={}:duration=longest:normalize=0[voice_bus]".format(
                    "".join(voice_labels), len(voice_labels)
                )
            )
        filters.extend(
            [
                "[voice_bus]apad,asplit=2[voice_sc][voice_mix]",
                "[0:a]volume={}dB[background]".format(config.background_gain_db),
                (
                    "[background][voice_sc]sidechaincompress="
                    "threshold={}:ratio={}:attack={}:release={}[ducked]"
                ).format(
                    config.duck_threshold,
                    config.duck_ratio,
                    config.duck_attack_ms,
                    config.duck_release_ms,
                ),
                "[ducked][voice_mix]amix=inputs=2:duration=first:normalize=0[mix_pre]",
            ]
        )
        source_label = "[mix_pre]"
    else:
        filters.append("[0:a]volume={}dB[mix_pre]".format(config.background_gain_db))
        source_label = "[mix_pre]"

    filters.append(
        (
            "{}loudnorm=I={}:TP={}:LRA={},"
            "alimiter=limit={:.8f}:attack=5:release=50:level=false[mix_out]"
        ).format(
            source_label,
            config.target_lufs,
            config.true_peak_dbtp,
            config.loudness_range,
            limiter_linear,
        )
    )
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[mix_out]",
            "-c:a",
            "pcm_s24le",
            "-f",
            "wav",
            str(output_path),
        ]
    )
    return command, len(dubs)


def mix_audio_ffmpeg(
    background_audio: PathLike,
    dubbing_audio_files: Iterable[Mapping[str, Any]],
    output_path: PathLike,
    settings: FFmpegMixSettings = None,
    ffmpeg_binary: str = "ffmpeg",
    timeout_seconds: float = 600.0,
) -> FFmpegMixResult:
    config = settings or FFmpegMixSettings()
    dubs = _validated_dubs(dubbing_audio_files)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    background_duration = _probe_duration(background_audio)
    effective_timeout = max(timeout_seconds, background_duration * 4.0 + 300.0)
    if len(dubs) <= config.max_inputs_per_pass:
        command, dub_count = build_ffmpeg_mix_command(
            background_audio,
            dubs,
            output,
            settings=config,
            ffmpeg_binary=ffmpeg_binary,
        )
        _run_ffmpeg(command, effective_timeout)
    else:
        with tempfile.TemporaryDirectory(
            prefix="voice-bus-", dir=str(output.parent)
        ) as temporary_directory:
            voice_bus = _render_scalable_voice_bus(
                dubs,
                background_duration,
                Path(temporary_directory),
                config,
                ffmpeg_binary,
                effective_timeout,
            )
            command, _ = build_ffmpeg_mix_command(
                background_audio,
                [{"index": 0, "path": str(voice_bus), "start": 0.0}],
                output,
                settings=config,
                ffmpeg_binary=ffmpeg_binary,
            )
            _run_ffmpeg(command, effective_timeout)
            dub_count = len(dubs)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("FFmpeg mix failed")
    return FFmpegMixResult(str(output), dub_count, command)
