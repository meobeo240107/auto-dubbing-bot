import urllib.request
import concurrent.futures
import time
import os
import cv2
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://sns-video-bd.xhscdn.com/pre_post/1040g2t0323qhv950744g5n21ujghaj977vjudfo'

def download_part_with_retry(url, start, end, part_num, tmp_base, max_retries=10):
    part_name = f"{tmp_base}_{part_num}.part"
    
    current_start = start
    if os.path.exists(part_name):
        current_start += os.path.getsize(part_name)
        
    while current_start <= end:
        success = False
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                req.add_header('Range', f'bytes={current_start}-{end}')
                with urllib.request.urlopen(req, timeout=12) as resp:
                    with open(part_name, 'ab') as f:
                        while True:
                            chunk = resp.read(128 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            current_start += len(chunk)
                success = True
                break
            except Exception as e:
                time.sleep(0.5)
        if not success:
            return part_name, False
    return part_name, True

def robust_parallel_download(url, dest_path, workers=6):
    t0 = time.time()
    req = urllib.request.Request(url, method='HEAD')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    with urllib.request.urlopen(req, timeout=10) as resp:
        total_size = int(resp.headers.get('Content-Length', 0))
        
    print(f"Total size: {total_size} bytes ({total_size/(1024*1024):.2f} MB)")
    if total_size <= 0:
        return False
        
    chunk_size = total_size // workers
    futures = []
    tmp_base = dest_path + "_tmp"
    
    # Clean previous temp files
    for i in range(workers):
        p = f"{tmp_base}_{i}.part"
        if os.path.exists(p):
            try: os.remove(p)
            except: pass
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for i in range(workers):
            start = i * chunk_size
            end = total_size - 1 if i == workers - 1 else (start + chunk_size - 1)
            futures.append(executor.submit(download_part_with_retry, url, start, end, i, tmp_base))
            
        results = [f.result() for f in futures]
        
    for p, ok in results:
        if not ok:
            print("Download failed for part", p)
            return False
            
    with open(dest_path, 'wb') as out_f:
        for p, ok in results:
            with open(p, 'rb') as in_f:
                out_f.write(in_f.read())
            try: os.remove(p)
            except: pass
            
    dt = time.time() - t0
    final_size = os.path.getsize(dest_path)
    print(f"DOWNLOAD SUCCESS: {final_size} bytes in {dt:.2f}s ({final_size/(1024*1024)/dt:.2f} MB/s)")
    
    # Verify no watermark on frame 1s
    cap = cv2.VideoCapture(dest_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite("final_clean_frame.jpg", frame)
        print("Saved final_clean_frame.jpg for watermark inspection!")
    cap.release()
    return True

if __name__ == '__main__':
    robust_parallel_download(url, 'test_final_clean.mp4', workers=6)
