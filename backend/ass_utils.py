import codecs
import textwrap

def generate_ass_file(dialogue_segments, floating_segments, output_path, play_res_x=1080, play_res_y=1920, main_y_pct=0.85):
    # Cố định hoàn toàn độ phân giải ASS là 720x1280 để font size 38 luôn không đổi và có cùng tỷ lệ trên mọi video
    play_res_x = 720
    play_res_y = 1280
    scale_y = 1.0
    scale_x = 1.0
    
    font_size = 38
    outline = 12
    
    # Dùng style đơn giản nhất, chữ trắng viền đen
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BgStyle,Arial,{font_size},&H00F0F0F0,&H00F0F0F0,&H00F0F0F0,&H00F0F0F0,0,0,0,0,100,100,0,0,1,{outline},0,5,0,0,0,1
Style: TextStyle,Arial,{font_size},&H00000000,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def format_time(td):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        centiseconds = int(td.microseconds / 10000)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    if dialogue_segments:
        # TÍNH TOÁN MAX CHARS CHO MỖI LINE
        # Hộp trắng tối đa chiếm 90% chiều rộng màn hình (theo yêu cầu wrap)
        max_allowed_w = int(play_res_x * 0.90)
        # Font width ước tính
        max_chars_per_line = int(max_allowed_w / (22 * scale_x))
        
        # PRE-PROCESSING: Tách các segment quá dài thành các segment nối tiếp nhau
        processed_segments = []
        for seg in dialogue_segments:
            text = str(seg.content).replace('\n', ' ').strip()
            
            # Dùng textwrap thử chia dòng
            lines_test = textwrap.wrap(text, width=max_chars_per_line)
            
            # Nếu text quá dài, chiếm hơn 2 dòng
            if len(lines_test) > 2:
                # Chia thành nhiều segment nhỏ, mỗi segment chứa tối đa 2 dòng
                num_parts = (len(lines_test) + 1) // 2
                
                total_duration = (seg.end - seg.start).total_seconds()
                part_duration = total_duration / num_parts
                
                from copy import copy
                from datetime import timedelta
                
                words = text.split()
                if len(words) >= num_parts:
                    words_per_part = len(words) // num_parts
                    for p in range(num_parts):
                        new_seg = copy(seg)
                        start_idx = p * words_per_part
                        end_idx = len(words) if p == num_parts - 1 else (p + 1) * words_per_part
                        
                        new_seg.content = " ".join(words[start_idx:end_idx])
                        new_seg.start = seg.start + timedelta(seconds=p * part_duration)
                        new_seg.end = seg.start + timedelta(seconds=(p + 1) * part_duration)
                        processed_segments.append(new_seg)
                else:
                    processed_segments.append(seg)
            else:
                processed_segments.append(seg)
                
        for i, seg in enumerate(processed_segments):
            start_time = seg.start
            end_time = seg.end
            
            # Khắc phục hiện tượng nháy chữ: Nối liền các sub nếu khoảng cách giữa chúng rất nhỏ (<= 1.0s)
            if i < len(processed_segments) - 1:
                next_start = processed_segments[i+1].start
                gap = (next_start - end_time).total_seconds()
                if 0 < gap <= 1.0:
                    end_time = next_start
                    
            start_str = format_time(start_time)
            end_str = format_time(end_time)
            text = str(seg.content).replace('\n', ' ').strip()
            
            # --- DYNAMIC MOTION TRACKING ---
            from datetime import timedelta
            sub_events = []
            if hasattr(seg, 'tracking_blocks') and len(seg.tracking_blocks) > 0:
                blocks = sorted(seg.tracking_blocks, key=lambda x: x.start)
                seg_s = start_time.total_seconds()
                seg_e = end_time.total_seconds()
                
                current_s = seg_s
                for i, b in enumerate(blocks):
                    b_end = b.end if i < len(blocks) - 1 else seg_e
                    e_overlap = min(seg_e, b_end)
                    if e_overlap > current_s:
                        sub_events.append({
                            'start': current_s,
                            'end': e_overlap,
                            'block': b
                        })
                        current_s = e_overlap
                # Lấp đầy khoảng trống (nếu có)
                if current_s < seg_e and sub_events:
                    sub_events[-1]['end'] = seg_e
            else:
                sub_events.append({
                    'start': start_time.total_seconds(),
                    'end': end_time.total_seconds(),
                    'block': seg.best_block if hasattr(seg, 'best_block') else None
                })
                
            for event in sub_events:
                ev_start = timedelta(seconds=event['start'])
                ev_end = timedelta(seconds=event['end'])
                start_str = format_time(ev_start)
                end_str = format_time(ev_end)
                
                b = event['block']
                if b:
                    seg_y_pct = getattr(b, 'y_pct', main_y_pct)
                    seg_max_y_pct = getattr(b, 'max_y_pct', seg_y_pct)
                    chinese_w = int((getattr(b, 'max_x_pct', 0) - getattr(b, 'x_pct', 0)) * play_res_x)
                else:
                    seg_y_pct = getattr(seg, 'y_pct', main_y_pct)
                    seg_max_y_pct = getattr(seg, 'max_y_pct', seg_y_pct)
                    chinese_w = 0
                
                # 1. Xác định độ rộng wrap chữ Việt
                # Yêu cầu: Chỉ xuống dòng khi dòng đầu dài khoảng 90% chiều ngang màn hình
                target_box_w = play_res_x * 0.90
                target_chars = int(target_box_w / (22 * scale_x))

                lines = textwrap.wrap(text, width=target_chars)
                formatted_text = "\\N".join(lines)
                num_lines = len(lines)
                char_h = int(42 * scale_y)
                char_w = int(22 * scale_x)
                
                # 2. Tính kích thước chữ Việt THỰC TẾ sau khi wrap
                lines_arr = formatted_text.split('\\N')
                max_line_len = max(len(line) for line in lines_arr) if lines_arr else len(formatted_text)
                
                # Chiều rộng mỗi ký tự trung bình
                actual_text_w = max_line_len * char_w
                required_text_h = num_lines * char_h
                
                # 3. Ép khung trắng ÔM SÁT chữ Việt.
                # Lưu ý: BgStyle có Outline=12, tức là đã có sẵn viền dày 12px tự động tỏa ra xung quanh.
                # Nên padding ở đây bằng 0 thì thực tế vẫn có 12px khoảng trắng!
                padding_x = 0
                padding_y = 0
                
                box_w = actual_text_w + (padding_x * 2)
                box_h = required_text_h + (padding_y * 2)
                
                # Đảm bảo box không tràn màn hình
                max_allowed_w = int(play_res_x * 0.94)
                if box_w > max_allowed_w: box_w = max_allowed_w
                
                # Tính toán tọa độ Y (neo theo ĐÁY của chữ Trung vì đáy luôn chính xác, đỉnh có thể bị dính nhầm description)
                chinese_bottom_y = int(seg_max_y_pct * play_res_y)
                raw_chinese_h = int((seg_max_y_pct - seg_y_pct) * play_res_y)
                
                # Giới hạn chiều cao chữ Trung tối đa để bao phủ chữ di chuyển
                max_allowed_chinese_h = int(play_res_y * 0.35)
                chinese_h = min(raw_chinese_h, max_allowed_chinese_h)
                
                # Bỏ qua việc ép box_h theo chinese_h để hộp trắng luôn ôm sát chữ Việt.
                # chinese_h chỉ dùng để tính tâm dọc.
                    
                chinese_center_y = chinese_bottom_y - (chinese_h // 2)
                
                box_y = chinese_center_y - (box_h // 2)
                if box_y < 0: box_y = 0
                
                box_x = (play_res_x - box_w) // 2
                min_margin = int(play_res_x * 0.04)
                if box_x < min_margin: box_x = min_margin
                if box_x + box_w > play_res_x - min_margin:
                    box_x = play_res_x - min_margin - box_w
                
                draw_cmd = f"{{\\p1}}m 0 0 l {box_w} 0 l {box_w} {box_h} l 0 {box_h}{{\\p0}}"
                bg_line = f"{{\\an7\\pos({box_x},{box_y})}}{draw_cmd}"
                ass_content += f"Dialogue: 0,{start_str},{end_str},BgStyle,,0,0,0,,{bg_line}\n"
                
                text_cx = box_x + (box_w // 2)
                text_cy = box_y + padding_y
                text_line = f"{{\\an8\\pos({text_cx},{text_cy})}}{formatted_text}"
                ass_content += f"Dialogue: 1,{start_str},{end_str},TextStyle,,0,0,0,,{text_line}\n"
            
    with codecs.open(output_path, 'w', 'utf-8-sig') as f:
        f.write(ass_content)
