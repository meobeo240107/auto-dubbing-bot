# Pipeline v2 rollout guide

Pipeline v2 is integrated into Telegram URL uploads, Telegram file uploads and
the local batch processor. The default remains the unchanged legacy pipeline.

## Modes

```env
PIPELINE_MODE=legacy
```

- `legacy`: current production flow; no v2 processing or manifest writes.
- `shadow`: legacy remains authoritative and a post-run shadow manifest records
  artifact hashes plus observed stage/total timing for comparison. It never
  loads a second GPU model alongside the live legacy render.
- `v2`: use the checkpointed v2 pipeline and publish its final result.

Restart the bot only when its queue is empty. Never change modes while Demucs,
Whisper, EasyOCR, RVC or FFmpeg is active.

## Recommended rollout

Start with shadow mode:

```env
PIPELINE_MODE=shadow
```

Then test one short video with conservative v2 settings:

```env
PIPELINE_MODE=v2
ENABLE_GPU_PROCESS_ISOLATION=true
ENABLE_STAGE_CACHE=true
ENABLE_PARALLEL_OCR_GEMINI=false
ENABLE_ADAPTIVE_DEMUCS=false
ENABLE_ADAPTIVE_OCR=false
ENABLE_TIMING_SOLVER=false
ENABLE_FFMPEG_MIX_V2=false
ENABLE_LEGACY_MIX_AB=false
PRESERVE_SOURCE_RESOLUTION=true
QC_GATE_POLICY=report_only
ATEMPO_MIN=0.92
ATEMPO_MAX=1.08
```

Enable optimizations one at a time after comparing the output:

```env
ENABLE_PARALLEL_OCR_GEMINI=true
ENABLE_ADAPTIVE_DEMUCS=true
ENABLE_ADAPTIVE_OCR=true
ENABLE_TIMING_SOLVER=true
ENABLE_FFMPEG_MIX_V2=true
```

When FFmpeg mix v2 is enabled, Pydub A/B output stays off by default to avoid
loading long PCM audio into RAM twice. Set `ENABLE_LEGACY_MIX_AB=true` only for
a deliberate listening comparison.

Adaptive decisions are conservative. An uncertain audio probe runs Demucs; an
unavailable lightweight video probe runs EasyOCR. Source resolution is kept,
and a requested target must never upscale a smaller source.

Keep QC non-blocking during initial real-video testing:

```env
QC_GATE_POLICY=report_only
```

After multiple successful videos, `warn` still delivers while surfacing QC
errors. `block` prevents delivery when the QC report contains an error, but it
does not delete the render or its artifacts:

```env
QC_GATE_POLICY=block
```

## Checkpoints and output

Each legacy job directory gains a separate `pipeline_v2` directory containing:

- `job_manifest.json` with stage status, attempts and errors;
- `artifacts/` with immutable-by-hash stage outputs;
- `control/` for short-lived GPU worker requests;
- `work/` for stage-local temporary directories.

An interrupted `running` stage becomes `failed` on restart and is retried from
that stage. In `PIPELINE_MODE=v2`, Telegram startup scans incomplete manifests,
puts them back into the same sequential work queue, and republishes both the
workspace output and the automatic `D:\banve` copy. Completed artifacts are
reused only when SHA-256, source,
configuration and model fingerprints remain valid. `ENABLE_STAGE_CACHE=true`
also reuses a fully delivered job; when false, a new run archives the completed
manifest and starts fresh.

The GPU lock is shared by Demucs, Whisper, EasyOCR and RVC. Each heavyweight
stage runs in its own Python process, and operating-system lock release protects
against worker crashes.

## Duration-independent resource limits

Pipeline v2 does not use a separate long-video mode or change the render steps.
The same pipeline scales its timeout from ffprobe duration and bounds the work
per batch, so a 30–60 minute input does not create an unbounded API request,
task list, model process or FFmpeg command line:

```env
TRANSLATION_BATCH_SEGMENTS=80
TRANSLATION_BATCH_CHARACTERS=12000
OCR_BATCH_SEGMENTS=80
TTS_BATCH_SEGMENTS=64
RVC_BATCH_SEGMENTS=64
MIXER_CHUNK_SECONDS=300
MIXER_MAX_INPUTS_PER_PASS=64
```

- Every Gemini translation batch keeps three prior translated lines and samples
  five frames from that batch's own time range.
- TTS and RVC publish atomic per-batch checkpoints. Restarting after a later
  batch fails does not regenerate already validated audio batches.
- RVC uses one short-lived isolated model process per bounded batch.
- The studio mixer builds a lossless FLAC voice bus in bounded FFmpeg passes,
  then applies the same sidechain ducking, `-15 LUFS` loudness and `-1 dBTP`
  limiter once to the full program.
- The global yt-dlp wall-clock timeout is disabled by default; socket timeout
  and retry rules remain active. Set `SOCIAL_DOWNLOAD_TIMEOUT_SECONDS` only if
  an explicit total download deadline is required.

These limits control peak resources, not video duration. They may be tuned for
the machine without changing stage order or output behavior.

## Rollback

Set the following and restart after the queue becomes empty:

```env
PIPELINE_MODE=legacy
```

Legacy mode imports only the lightweight mode configuration; no v2 model,
worker or media-processing module is loaded. The legacy Telegram and batch
processing bodies are still present. Existing v2 artifacts can be kept for
diagnosis and resume; they do not alter legacy outputs.
