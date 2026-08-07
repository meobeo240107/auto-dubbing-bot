import cv2
import easyocr
import logging
from deep_translator import GoogleTranslator
import difflib
import re

logger = logging.getLogger(__name__)
reader = None

def get_ocr_reader():
    global reader
    if reader is None:
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

def extract_silent_subtitles_from_gaps(gap_segments, target_lang="vi", api_key=None):
    return []

def perform_video_ocr(video_path, target_lang='vi', sample_rate=1.0, api_key=None, srt_segments=None):
    logger.info(f"Bắt đầu OCR toàn diện trên video {video_path}")
    reader = get_ocr_reader()
    
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
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
            
        if frame_count % frame_interval == 0:
            current_time = frame_count / fps
            
            # === TIỀN XỬ LÝ ẢNH (NÂNG CẤP OCR) ===
            # 1. Chuyển sang ảnh xám
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # 2. Tăng cường độ tương phản cục bộ (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            
            # 3. OCR với ảnh đã xử lý, phóng to 1.5x để bắt chữ nhỏ tốt hơn
            results = reader.readtext(gray, detail=1, paragraph=False, mag_ratio=1.5, width_ths=0.7)
            
            frame_blocks = []
            for (bbox, text, prob) in results:
                if len(text.strip()) == 0: continue
                
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                x1, x2 = min(xs), max(xs)
                y1, y2 = min(ys), max(ys)
                
                # Bỏ padding dư thừa để bbox ôm sát text thật (Chỉ giữ 1% ngang, 0.5% dọc)
                x1 = max(0, x1 - int(width * 0.01))
                x2 = min(width, x2 + int(width * 0.01))
                y1 = max(0, y1 - int(height * 0.005))
                y2 = min(height, y2 + int(height * 0.005))
                
                x_pct = x1 / width
                max_x_pct = x2 / width
                y_pct = y1 / height
                max_y_pct = y2 / height
                
                frame_blocks.append({
                    'text': text, 'x_pct': x_pct, 'max_x_pct': max_x_pct, 
                    'y_pct': y_pct, 'max_y_pct': max_y_pct
                })
                
            # Gộp các block trong CÙNG MỘT frame (để gom các dòng của 1 phụ đề)
            merged_frame_blocks = []
            for fb in frame_blocks:
                added = False
                for mb in merged_frame_blocks:
                    # Kiểm tra xem có chung khối phụ đề không (chênh lệch Y nhỏ và CÓ đè lên nhau theo X)
                    y_dist = abs((mb['y_pct'] + mb['max_y_pct'])/2 - (fb['y_pct'] + fb['max_y_pct'])/2)
                    horizontal_overlap = not (mb['max_x_pct'] < fb['x_pct'] or fb['max_x_pct'] < mb['x_pct'])
                    
                    if y_dist < 0.08 and horizontal_overlap:
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
                all_blocks.append(OCRBlock(mb['text'], current_time, current_time + sample_rate, 
                                           mb['x_pct'], mb['max_x_pct'], mb['y_pct'], mb['max_y_pct']))
                    
        frame_count += 1
    cap.release()
    
    valid_blocks_for_main_y = [b for b in all_blocks if b.end - b.start <= 15.0 and len(re.sub(r'[^\w]', '', b.text)) >= 4]
    
    valid_blocks = [
        b for b in all_blocks 
        if len(re.sub(r'[^\w]', '', b.text)) >= 2 
    ]
    
    logger.info(f"Total all_blocks: {len(all_blocks)}")
    for i, b in enumerate(all_blocks):
        if len(b.text) > 2:
            logger.info(f"Block {i}: '{b.text[:20]}', start:{b.start:.2f}, end:{b.end:.2f}, y:{b.y_pct:.3f}")
    
    # === ROBUST Y-TRACKING (Kết hợp Text Similarity + Vị trí + Thời gian) ===
    # Ở bước này, srt_segments vẫn đang chứa text tiếng Trung gốc từ Whisper.
    # Do đó, so sánh chuỗi (SequenceMatcher) cực kỳ hiệu quả để loại bỏ nhiễu từ hậu cảnh (như công thức toán).
    import difflib
    
    matched_y_pcts = []
    
    if srt_segments:
        for seg in srt_segments:
            seg_start = seg.start.total_seconds()
            seg_end = seg.end.total_seconds()
            seg_text = str(seg.content).strip()
            
            best_score = -1
            best_block = None
            matching_blocks = []
            
            for b in valid_blocks:
                # Giao nhau về thời gian
                if b.start <= seg_end and b.end >= seg_start:
                    # 1. Điểm tương đồng chuỗi (0 -> 100)
                    # Vì b.text có thể là chuỗi nối dài của nhiều frame (VD: "text text text"), 
                    # nên ta cắt ra và lấy part có điểm cao nhất để không bị trừ điểm do lệch độ dài.
                    best_sim = 0
                    for part in b.text.split(" "):
                        if not part.strip(): continue
                        sim = difflib.SequenceMatcher(None, part, seg_text).ratio()
                        if sim > best_sim:
                            best_sim = sim
                    
                    score = best_sim * 100
                    
                    # NẾU HOÀN TOÀN KHÔNG GIỐNG NHAU THÌ LOẠI BỎ NGAY LẬP TỨC!
                    if score < 15:
                        continue
                        
                    # Xóa bộ lọc Y cứng nhắc (if 0.35 < b.y_pct < 0.65: continue)
                    # Vì phụ đề có thể xuất hiện ở bất cứ đâu (giữa màn hình)
                    
                    # Phụ đề có thể ở bất cứ đâu, nên không phạt vị trí quá nặng
                    if b.y_pct > 0.65:
                        score += 10
                        
                    if (b.end - b.start) < 15.0:
                        score += 10
                        
                    if score > 40:
                        matching_blocks.append((score, b))
                        if score > best_score:
                            best_score = score
                            best_block = b
            
            if best_block and best_score > 40:
                import copy
                # Tìm tất cả các block khớp tốt trong đoạn thời gian này để gom bao trùm chuyển động (nếu chữ di chuyển)
                strong_blocks = [b for s, b in matching_blocks if s > max(40, best_score - 20) and abs(b.y_pct - best_block.y_pct) < 0.15]
                
                if strong_blocks:
                    strong_blocks.sort(key=lambda b: b.start)
                    overall_y_pct = min(b.y_pct for b in strong_blocks)
                    overall_max_y_pct = max(b.max_y_pct for b in strong_blocks)
                else:
                    overall_y_pct = best_block.y_pct
                    overall_max_y_pct = best_block.max_y_pct
                
                merged_block = copy.copy(best_block)
                merged_block.y_pct = overall_y_pct
                merged_block.max_y_pct = overall_max_y_pct
                
                seg.best_block = merged_block
                seg.tracking_blocks = [merged_block]
                matched_y_pcts.append(overall_y_pct)
            else:
                # Fallback: OCR dự đoán chữ bị sai (gibberish), không khớp chuỗi được.
                # Tìm block CÓ HÌNH DÁNG GIỐNG PHỤ ĐỀ (nằm giữa theo trục X, khá rộng) trong cùng khung giờ!
                # BẮT BUỘC: Nằm trong khoảng 15% - 88% để tránh nhận nhầm tiêu đề video ở trên cùng và watermark ở dưới cùng!
                candidate_blocks = [
                    b for b in valid_blocks
                    if b.start <= seg_end and b.end >= seg_start
                    and b.x_pct < 0.45 and b.max_x_pct > 0.55
                    and b.y_pct > 0.15 and b.y_pct < 0.88
                ]
                if candidate_blocks:
                    # Chọn block dài nhất (thường là phụ đề dài hơn tiêu đề video)
                    best_shape_block = max(candidate_blocks, key=lambda b: b.max_x_pct - b.x_pct)
                    
                    import copy
                    seg.best_block = copy.copy(best_shape_block)
                    seg.tracking_blocks = [seg.best_block]
                    matched_y_pcts.append(best_shape_block.y_pct)
                else:
                    seg.best_block = None
    # Tính main_y_pct từ các block đã khớp (Dùng trung vị - median để chống nhiễu)
    if matched_y_pcts:
        matched_y_pcts.sort()
        mid_idx = len(matched_y_pcts) // 2
        main_y_pct = matched_y_pcts[mid_idx]
    else:
        # Fallback 2: Nếu OCR nhận diện quá tệ (hallucinations), ta lấy bất kỳ block nào nằm trong vùng 0.15 - 0.88.
        fallback_blocks = [b.y_pct for b in valid_blocks if 0.15 < b.y_pct < 0.88]
        if fallback_blocks:
            fallback_blocks.sort()
            main_y_pct = fallback_blocks[len(fallback_blocks) // 2]
            logger.warning(f"String matching failed completely. Fallback to median of bottom blocks: {main_y_pct:.3f}")
        else:
            # Fallback 3: Lấy trung vị của BẤT KỲ block nào trên màn hình nếu không có block ở nửa dưới
            all_y = [b.y_pct for b in valid_blocks]
            if all_y:
                all_y.sort()
                main_y_pct = all_y[len(all_y) // 2]
                logger.warning(f"No bottom blocks found. Fallback to median of all blocks: {main_y_pct:.3f}")
            else:
                main_y_pct = 0.880
                logger.warning(f"No text blocks found at all. Absolute Fallback Y=0.880")
        
    logger.info(f"Robust Y-Tracking detected main subtitle band at: {main_y_pct*100:.1f}%")
    
    # Gán Y cho các segment
    if srt_segments:
        last_good_y_pct = main_y_pct
        last_good_max_y_pct = main_y_pct + 0.05
        for seg in srt_segments:
            if hasattr(seg, 'best_block') and seg.best_block:
                b = seg.best_block
                # Tin tưởng tuyệt đối vào kết quả khớp chuỗi (score > 40), không cần kiểm tra lệch main_y_pct nữa
                seg.y_pct = b.y_pct
                seg.max_y_pct = b.max_y_pct
                seg.x_pct = b.x_pct
                seg.max_x_pct = b.max_x_pct
                if not hasattr(seg, 'tracking_blocks'):
                    seg.tracking_blocks = getattr(b, 'tracking_blocks', [b])
                last_good_y_pct = b.y_pct
                last_good_max_y_pct = b.max_y_pct
                logger.info(f"Sync (Matched): '{seg.content[:15]}' -> Y_range: {seg.y_pct:.3f} - {seg.max_y_pct:.3f}")
            else:
                seg.y_pct = last_good_y_pct
                seg.max_y_pct = last_good_max_y_pct
                logger.warning(f"No good match for '{seg.content[:15]}'. Inheriting Y={last_good_y_pct:.3f}")

    return [], width, height, main_y_pct
