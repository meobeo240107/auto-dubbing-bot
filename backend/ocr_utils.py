import cv2
import logging
from deep_translator import GoogleTranslator
import difflib
import os
import re
import tempfile
from pathlib import Path

from ai.model_policy import current_model_policy
from ai.model_runtime import ModelRuntimeError, run_model_stage, runtime_module_available

logger = logging.getLogger(__name__)
reader = None

def get_ocr_reader():
    global reader
    if reader is None:
        import easyocr

        logger.info("Initializing EasyOCR reader (GPU=True)...")
        # Gỡ bỏ 'en' để tránh EasyOCR bị ảo giác (nhận diện nhầm nhiễu thành chữ tiếng Anh)
        reader = easyocr.Reader(['ch_sim'])
    return reader

def release_ocr_reader():
    global reader
    if reader is not None:
        logger.info("🧹 Đang giải phóng bộ nhớ RAM/VRAM của EasyOCR...")
        del reader
        reader = None
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def _readtext_batch(frames):
    """Recognize all sampled frames in one PP-OCRv6 process, then fallback safely."""

    policy = current_model_policy()
    if policy.ocr_backend in {"auto", "paddle"} and runtime_module_available(
        "paddleocr", policy
    ):
        try:
            with tempfile.TemporaryDirectory(prefix="autodub-ocr-") as temporary:
                paths = []
                for index, frame in enumerate(frames):
                    path = Path(temporary) / "frame_{:04d}.png".format(index)
                    if not cv2.imwrite(str(path), frame):
                        raise OSError("Could not write OCR frame {}".format(path))
                    paths.append(str(path))
                result = run_model_stage(
                    "paddle_ocr",
                    {
                        "images": paths,
                        "ocr_version": policy.paddle_ocr_version,
                        "engine": policy.paddle_ocr_engine,
                    },
                    timeout_seconds=float(os.getenv("OCR_MODEL_TIMEOUT_SECONDS", "1800")),
                    policy=policy,
                )
                by_path = {
                    str(item.get("path")): item.get("rows", [])
                    for item in result.get("images", [])
                }
                output = []
                for path in paths:
                    rows = []
                    for item in by_path.get(path, []):
                        bbox = item.get("bbox", [])
                        text = str(item.get("text", "") or "")
                        score = float(item.get("score", 0.0) or 0.0)
                        if len(bbox) >= 4 and text.strip():
                            rows.append((bbox, text, score))
                    output.append(rows)
                if len(output) != len(frames):
                    raise RuntimeError("PP-OCRv6 returned an incomplete frame batch")
                logger.info(
                    "PP-OCRv6 completed %d sampled frames via %s",
                    len(frames),
                    policy.paddle_ocr_engine,
                )
                return output
        except (ModelRuntimeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            logger.warning("PP-OCRv6 failed; falling back to EasyOCR: %s", exc)

    easy_reader = get_ocr_reader()
    return [
        easy_reader.readtext(
            frame,
            detail=1,
            paragraph=False,
            mag_ratio=1.0,
            width_ths=0.7,
        )
        for frame in frames
    ]

def extract_silent_subtitles_from_gaps(gap_segments, target_lang="vi", api_key=None):
    return []

def perform_video_ocr(video_path, target_lang='vi', sample_rate=1.0, api_key=None, srt_segments=None, **kwargs):
    logger.info(f"Bắt đầu OCR toàn diện trên video {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return [], 1080, 1920, 0.85
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1: fps = 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_interval = int(fps * sample_rate)
    
    class OCRBlock:
        def __init__(self, text, start, end, x_pct, max_x_pct, y_pct, max_y_pct):
            self.text = text
            self.start = start
            self.end = end
            self.x_pct = x_pct
            self.max_x_pct = max_x_pct
            self.y_pct = y_pct
            self.max_y_pct = max_y_pct

    all_blocks = []
    
    # === TỐI ƯU HÓA SIÊU TỐC OCR THEO TỪNG ĐOẠN THOẠI ===
    target_timestamps = []
    if srt_segments:
        # Lấy tối đa 16 frame đại diện (1 frame giữa mỗi câu thoại) để nhận diện vị trí sub siêu tốc
        step = max(1, len(srt_segments) // 16)
        sampled_segs = srt_segments[::step]
        for seg in sampled_segs:
            s = seg.start.total_seconds()
            e = seg.end.total_seconds()
            mid = (s + e) / 2.0
            target_timestamps.append((mid, seg))
    else:
        for pct in [0.15, 0.3, 0.45, 0.6, 0.75, 0.9]:
            target_timestamps.append((10.0 * pct, None))

    crop_y_start = int(height * 0.05) # Quét từ 5% (bỏ thanh trạng thái)
    crop_y_end = int(height * 0.95)   # đến 95%
    captured_frames = []

    for current_time, target_seg in target_timestamps:
        import shared_state
        if getattr(shared_state, 'stop_requested', False):
            cap.release()
            return [], width, height, 0.85

        cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000)
        ret, frame = cap.read()
        if not ret: continue
        
        # 1. Cắt vùng chứa phụ đề tiềm năng (từ 5% đến 95% chiều cao màn hình)
        cropped_frame = frame[crop_y_start:crop_y_end, :]
        
        # 2. Resize nhanh về độ phân giải chuẩn 720p để EasyOCR tăng tốc gấp 3 lần nhưng vẫn siêu nét
        orig_crop_h, orig_crop_w = cropped_frame.shape[:2]
        scale_ratio = 1.0
        if orig_crop_w > 720:
            scale_ratio = 720.0 / orig_crop_w
            target_w = 720
            target_h = int(orig_crop_h * scale_ratio)
            proc_frame = cv2.resize(cropped_frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
        else:
            proc_frame = cropped_frame

        captured_frames.append((current_time, scale_ratio, proc_frame))

    cap.release()
    recognized_batches = _readtext_batch(
        [item[2] for item in captured_frames]
    ) if captured_frames else []
    for (current_time, scale_ratio, _proc_frame), results in zip(
        captured_frames, recognized_batches
    ):
        frame_blocks = []
        for (bbox, text, prob) in results:
            clean_t = text.strip()
            # Khong bo qua chu Han ke ca khi prob thap vi font chu nghe thuat co vien thuong co prob = 0.00
            if len(clean_t) == 0:
                continue
            
            xs = [pt[0] / scale_ratio for pt in bbox]
            ys = [(pt[1] / scale_ratio) + crop_y_start for pt in bbox] # Bù lại vị trí cắt dọc
            
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)
            
            x1 = max(0, x1 - int(width * 0.01))
            x2 = min(width, x2 + int(width * 0.01))
            y1 = max(0, y1 - int(height * 0.005))
            y2 = min(height, y2 + int(height * 0.005))
            
            x_pct = x1 / width
            max_x_pct = x2 / width
            y_pct = y1 / height
            max_y_pct = y2 / height
            
            frame_blocks.append({
                'text': clean_t, 'x_pct': x_pct, 'max_x_pct': max_x_pct, 
                'y_pct': y_pct, 'max_y_pct': max_y_pct, 'prob': prob
            })
            
        merged_frame_blocks = []
        for fb in frame_blocks:
            added = False
            for mb in merged_frame_blocks:
                y_dist = abs((mb['y_pct'] + mb['max_y_pct'])/2 - (fb['y_pct'] + fb['max_y_pct'])/2)
                horizontal_overlap = not (mb['max_x_pct'] < fb['x_pct'] or fb['max_x_pct'] < mb['x_pct'])
                
                # Không gộp nếu 1 bên là tiếng Trung và 1 bên là tiếng Anh ở khác dòng
                mb_has_zh = any('\u4e00' <= c <= '\u9fff' for c in mb['text'])
                fb_has_zh = any('\u4e00' <= c <= '\u9fff' for c in fb['text'])
                if mb_has_zh != fb_has_zh and y_dist > 0.015:
                    continue

                # Giảm khoảng cách Y cho phép merge (0.025) để không nuốt nhầm dòng phụ đề tiếng Anh bên dưới
                if y_dist < 0.025 and horizontal_overlap:
                    mb['text'] += " " + fb['text']
                    mb['x_pct'] = min(mb['x_pct'], fb['x_pct'])
                    mb['max_x_pct'] = max(mb['max_x_pct'], fb['max_x_pct'])
                    mb['y_pct'] = min(mb['y_pct'], fb['y_pct'])
                    mb['max_y_pct'] = max(mb['max_y_pct'], fb['max_y_pct'])
                    added = True
                    break
            if not added:
                merged_frame_blocks.append(fb)
        
        for mb in merged_frame_blocks:
            all_blocks.append(OCRBlock(mb['text'], current_time - 1.2, current_time + 1.2, 
                                       mb['x_pct'], mb['max_x_pct'], mb['y_pct'], mb['max_y_pct']))

    
    # Hàm đếm số lượng chữ Hán
    def count_chinese(text):
        return sum(1 for c in str(text) if '\u4e00' <= c <= '\u9fff')

    # Ưu tiên lọc 100% khối chữ Hán (tiếng Trung) để không bị che nhầm hoặc nhảy dòng theo tiếng Anh
    chinese_blocks = [b for b in all_blocks if count_chinese(b.text) >= 1]
    
    if len(chinese_blocks) >= 2:
        valid_subtitle_blocks = chinese_blocks
    else:
        valid_subtitle_blocks = [b for b in all_blocks if len(re.sub(r'[^\w\u4e00-\u9fff]', '', b.text)) >= 2]
    
    matched_spoken_tops = []
    matched_spoken_bottoms = []
    
    # Gán tọa độ Y cho từng segment dựa trên độ tương đồng với câu thoại thực tế
    if srt_segments:
        for seg in srt_segments:
            seg_start = seg.start.total_seconds()
            seg_end = seg.end.total_seconds()
            seg_text = str(seg.content).strip()
            
            best_sim = 0
            best_block = None
            matched_blocks = []
            
            for b in valid_subtitle_blocks:
                if b.start <= seg_end + 0.5 and b.end >= seg_start - 0.5:
                    sim = difflib.SequenceMatcher(None, b.text, seg_text).ratio()
                    for part in b.text.split(" "):
                        if not part.strip(): continue
                        p_sim = difflib.SequenceMatcher(None, part, seg_text).ratio()
                        if p_sim > sim: sim = p_sim
                    
                    # Ưu tiên tối đa khối chữ Hán
                    if count_chinese(b.text) >= 1:
                        sim *= 1.5
                    
                    if sim >= 0.1 and 0.05 <= b.y_pct <= 0.95:
                        matched_blocks.append(b)
                        
                    if sim > best_sim:
                        best_sim = sim
                        best_block = b
            
            if best_block and best_sim >= 0.15 and 0.05 <= best_block.y_pct <= 0.95:
                y_pcts = [b.y_pct for b in matched_blocks]
                max_y_pcts = [b.max_y_pct for b in matched_blocks]
                x_pcts = [b.x_pct for b in matched_blocks]
                max_x_pcts = [b.max_x_pct for b in matched_blocks]
                
                seg.y_pct = min(y_pcts) if y_pcts else best_block.y_pct
                seg.max_y_pct = max(max_y_pcts) if max_y_pcts else best_block.max_y_pct
                
                union_block = OCRBlock(
                    text=best_block.text, start=best_block.start, end=best_block.end,
                    x_pct=min(x_pcts) if x_pcts else best_block.x_pct,
                    max_x_pct=max(max_x_pcts) if max_x_pcts else best_block.max_x_pct,
                    y_pct=seg.y_pct, max_y_pct=seg.max_y_pct
                )
                
                seg.tracking_blocks = matched_blocks
                seg.best_block = union_block
                matched_spoken_tops.append(seg.y_pct)
                matched_spoken_bottoms.append(seg.max_y_pct)
                logger.info(f"Sync (Matched {best_sim:.2f} Union): '{seg.content[:15]}' -> Y: {seg.y_pct:.3f} - {seg.max_y_pct:.3f}")
            else:
                widest_block = None
                max_w = 0
                for b in valid_subtitle_blocks:
                    if b.start <= seg_end + 0.2 and b.end >= seg_start - 0.2 and 0.05 <= b.y_pct <= 0.95:
                        w = b.max_x_pct - b.x_pct
                        if count_chinese(b.text) >= 1:
                            w *= 1.5
                        if w > max_w:
                            max_w = w
                            widest_block = b
                
                if widest_block and max_w >= 0.10:
                    seg.y_pct = widest_block.y_pct
                    seg.max_y_pct = widest_block.max_y_pct
                    seg.best_block = widest_block
                    matched_spoken_tops.append(seg.y_pct)
                    matched_spoken_bottoms.append(seg.max_y_pct)
                    logger.info(f"Sync (Fallback Widest): '{seg.content[:15]}' -> Y: {seg.y_pct:.3f} - {seg.max_y_pct:.3f}")
                else:
                    seg.best_block = None

    # === TÍNH TOÁN BĂNG DẢI PHỤ ĐỀ TOÀN CỤC TỪ CÁC CÂU ĐÃ KHỚP CHỮ TRUNG ===
    if matched_spoken_tops:
        import numpy as np
        global_med_top = float(np.median(matched_spoken_tops))
        global_med_bottom = float(np.median(matched_spoken_bottoms))
    else:
        candidate_y_tops = [b.y_pct for b in valid_subtitle_blocks if 0.05 < b.y_pct < 0.90]
        candidate_y_bottoms = [b.max_y_pct for b in valid_subtitle_blocks if 0.05 < b.max_y_pct < 0.95]
        if candidate_y_tops and candidate_y_bottoms:
            import numpy as np
            global_med_top = float(np.median(candidate_y_tops))
            global_med_bottom = float(np.median(candidate_y_bottoms))
        else:
            global_med_top = 0.75
            global_med_bottom = 0.82
        
    main_y_pct = global_med_top
    logger.info(f"🎯 Global Subtitle Band detected: Top={global_med_top:.3f}, Bottom={global_med_bottom:.3f}")
    
    # Khóa và ổn định dải phụ đề: Ghim chặt vị trí để phụ đề tiếng Việt đứng yên, không nhảy lên xuống
    if srt_segments:
        for seg in srt_segments:
            if not getattr(seg, 'best_block', None):
                seg.y_pct = global_med_top
                seg.max_y_pct = global_med_bottom
                logger.info(f"Sync (Global Band Fallback): '{seg.content[:15]}' -> Y: {global_med_top:.3f} - {global_med_bottom:.3f}")
            elif hasattr(seg, 'y_pct') and abs(seg.y_pct - global_med_top) > 0.035:
                # Nếu câu nào bị lệch quá 3.5% so với dòng chữ Trung (do dính chữ tiếng Anh), ghim về dòng chuẩn
                logger.info(f"Ổn định vị trí: Ghim Y từ {seg.y_pct:.3f} về dải chữ Trung chuẩn {global_med_top:.3f}")
                seg.y_pct = global_med_top
                seg.max_y_pct = global_med_bottom
                if hasattr(seg, 'best_block') and seg.best_block:
                    seg.best_block.y_pct = global_med_top
                    seg.best_block.max_y_pct = global_med_bottom

    return [], width, height, main_y_pct
