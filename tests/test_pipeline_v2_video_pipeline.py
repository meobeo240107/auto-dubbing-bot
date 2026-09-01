import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from backend.pipeline_v2.config import PipelineMode, PipelineSettings, QCGatePolicy
from backend.pipeline_v2.qc import evaluate_qc_gate
from backend.pipeline_v2.segments import RuntimeSegment, segments_to_dicts
from backend.pipeline_v2.video_pipeline import (
    VideoPipelineRequest,
    VideoPipelineRunner,
    compose_srt,
)


class FakeVideoPipelineRunner(VideoPipelineRunner):
    def __init__(self, request):
        super().__init__(request)
        self.calls = []

    async def _extract_audio_stage(self):
        self.calls.append("extract_audio")
        return [self.artifact_store.put_bytes("audio/original.wav", b"audio")]

    async def _demucs_stage(self):
        self.calls.append("demucs")
        return [
            self.artifact_store.put_bytes("audio/vocals.wav", b"voice"),
            self.artifact_store.put_bytes("audio/background.wav", b"background"),
        ]

    async def _transcribe_stage(self):
        self.calls.append("transcribe")
        segments = [
            RuntimeSegment(
                index=1,
                start=timedelta(seconds=0),
                end=timedelta(seconds=1),
                content="你好",
            )
        ]
        return [
            self.artifact_store.put_text("transcript/original.srt", compose_srt(segments)),
            self.artifact_store.put_json(
                "transcript/segments.json", {"segments": segments_to_dicts(segments)}
            ),
        ]

    async def _ocr_stage(self, transcript):
        self.calls.append("ocr")
        payload = segments_to_dicts(transcript)
        payload[0]["y_pct"] = 0.8
        payload[0]["max_y_pct"] = 0.85
        return [
            self.artifact_store.put_json(
                "ocr/result.json",
                {
                    "segments": payload,
                    "width": 720,
                    "height": 1280,
                    "main_y_pct": 0.8,
                },
            )
        ]

    async def _translate_stage(self, transcript):
        self.calls.append("translate")
        translated = [
            RuntimeSegment(
                index=1,
                start=timedelta(seconds=0),
                end=timedelta(seconds=1),
                content="Xin chào",
                orig_content="你好",
            )
        ]
        return [
            self.artifact_store.put_json(
                "translation/segments.json",
                {"segments": segments_to_dicts(translated)},
            ),
            self.artifact_store.put_text(
                "translation/translated.srt", compose_srt(translated)
            ),
        ]

    async def _tts_stage(self, segments):
        self.calls.append("tts")
        audio = self.artifact_store.put_bytes("tts/1.mp3", b"tts")
        index = self.artifact_store.put_json(
            "tts/segments.json",
            {
                "segments": [
                    {
                        "index": 1,
                        "source_segment_id": 1,
                        "artifact_key": "tts/1.mp3",
                        "path": None,
                        "start": 0.0,
                        "end": 1.0,
                        "actual_audio_duration": 0.9,
                        "timing_fits": True,
                        "content": "Xin chào",
                    }
                ]
            },
        )
        return [audio, index]

    async def _subtitles_stage(self, segments):
        self.calls.append("subtitles")
        return [self.artifact_store.put_text("subtitles/final.ass", "ASS")]

    async def _mix_legacy_stage(self):
        self.calls.append("mix_legacy")
        return [self.artifact_store.put_bytes("audio/mixed_legacy.wav", b"mix")]

    async def _render_stage(self):
        self.calls.append("render")
        return [self.artifact_store.put_bytes("output/final.mp4", b"final-video")]

    async def _qc_stage(self, segments):
        self.calls.append("qc")
        return [
            self.artifact_store.put_json(
                "qc/qc_report.json",
                {
                    "mode": "report_only",
                    "blocking": False,
                    "delivery_allowed": True,
                    "checks": [],
                },
            )
        ]


class VideoPipelineEndToEndTests(unittest.IsolatedAsyncioTestCase):
    async def test_fake_pipeline_delivers_and_resumes_without_rerunning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"source-video")
            output = root / "delivered.mp4"
            settings = PipelineSettings(
                mode=PipelineMode.V2,
                enable_gpu_process_isolation=False,
                enable_stage_cache=True,
            )
            request = VideoPipelineRequest(
                video_path=source,
                job_directory=root / "job",
                output_path=output,
                settings=settings,
            )
            first = FakeVideoPipelineRunner(request)
            self.assertEqual(first.gpu_executor.lock_path, root / "pipeline_v2_gpu.lock")
            result = await first.run()
            self.assertEqual(output.read_bytes(), b"final-video")
            self.assertTrue(result.qc_allowed)
            self.assertEqual(
                first.calls,
                [
                    "extract_audio",
                    "demucs",
                    "transcribe",
                    "ocr",
                    "translate",
                    "tts",
                    "subtitles",
                    "mix_legacy",
                    "render",
                    "qc",
                ],
            )

            resumed = FakeVideoPipelineRunner(request)
            await resumed.run()
            self.assertEqual(resumed.calls, [])

            # Corrupting a completed artifact invalidates that stage and only
            # its downstream consumers; earlier expensive stages stay cached.
            resumed.artifact_store.path_for("translation/segments.json").write_bytes(
                b"corrupt"
            )
            repaired = FakeVideoPipelineRunner(request)
            await repaired.run()
            self.assertNotIn("extract_audio", repaired.calls)
            self.assertNotIn("demucs", repaired.calls)
            self.assertNotIn("transcribe", repaired.calls)
            self.assertNotIn("ocr", repaired.calls)
            self.assertIn("translate", repaired.calls)
            self.assertIn("render", repaired.calls)


class QCGateTests(unittest.TestCase):
    def test_block_policy_blocks_errors_but_report_only_does_not(self):
        report = {"checks": [{"name": "video_stream", "status": "error"}]}
        blocked = evaluate_qc_gate(report, QCGatePolicy.BLOCK)
        allowed = evaluate_qc_gate(report, QCGatePolicy.REPORT_ONLY)
        self.assertFalse(blocked.allowed)
        self.assertTrue(allowed.allowed)


if __name__ == "__main__":
    unittest.main()
