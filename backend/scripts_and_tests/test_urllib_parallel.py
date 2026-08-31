import urllib.request
import concurrent.futures
import time
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://sns-video-bd.xhscdn.com/pre_post/1040g2t0323qhv950744g5n21ujghaj977vjudfo'

def download_part(url, start, end, part_num, tmp_base):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    req.add_header('Range', f'bytes={start}-{end}')
    part_name = f"{tmp_base}_{part_num}.part"
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        with open(part_name, 'wb') as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    return part_name

def parallel_download(url, dest_path, workers=8):
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
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        for i in range(workers):
            start = i * chunk_size
            end = total_size - 1 if i == workers - 1 else (start + chunk_size - 1)
            futures.append(executor.submit(download_part, url, start, end, i, tmp_base))
            
        part_files = [f.result() for f in futures]
        
    with open(dest_path, 'wb') as out_f:
        for p in part_files:
            with open(p, 'rb') as in_f:
                out_f.write(in_f.read())
            try: os.remove(p)
            except: pass
            
    dt = time.time() - t0
    print(f"Downloaded {os.path.getsize(dest_path)} bytes in {dt:.2f}s ({os.path.getsize(dest_path)/(1024*1024)/dt:.2f} MB/s)")
    return True

if __name__ == '__main__':
    parallel_download(url, 'test_clean_video.mp4', workers=8)
