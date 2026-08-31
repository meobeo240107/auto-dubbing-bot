import requests
import concurrent.futures
import time
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

url = 'http://sns-video-bd.xhscdn.com/pre_post/1040g2t0323qhv950744g5n21ujghaj977vjudfo'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def download_chunk(url, start_byte, end_byte, part_index, temp_prefix):
    part_headers = headers.copy()
    part_headers['Range'] = f'bytes={start_byte}-{end_byte}'
    part_file = f"{temp_prefix}.part{part_index}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=part_headers, timeout=10)
            if r.status_code in [200, 206]:
                with open(part_file, 'wb') as f:
                    f.write(r.content)
                return part_file, True
        except Exception as e:
            time.sleep(1)
    return part_file, False

def fast_multi_download(url, dest_path, num_threads=8):
    t0 = time.time()
    res = requests.head(url, headers=headers, timeout=5)
    total_size = int(res.headers.get('Content-Length', 0))
    print(f"Total size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
    if total_size <= 0:
        return False
        
    chunk_size = total_size // num_threads
    futures = []
    temp_prefix = dest_path + ".tmp"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for i in range(num_threads):
            start = i * chunk_size
            end = total_size - 1 if i == num_threads - 1 else (start + chunk_size - 1)
            futures.append(executor.submit(download_chunk, url, start, end, i, temp_prefix))
            
        results = [f.result() for f in futures]
        
    for part_file, success in results:
        if not success or not os.path.exists(part_file):
            print("Failed to download a chunk!")
            return False
            
    # Combine parts
    with open(dest_path, 'wb') as outfile:
        for i in range(num_threads):
            part_file = f"{temp_prefix}.part{i}"
            with open(part_file, 'rb') as infile:
                outfile.write(infile.read())
            try: os.remove(part_file)
            except: pass
            
    dt = time.time() - t0
    speed_mb = (total_size / (1024*1024)) / dt if dt > 0 else 0
    print(f"SUCCESS: Downloaded {total_size} bytes to {dest_path} in {dt:.2f}s (Speed: {speed_mb:.2f} MB/s)")
    return True

if __name__ == "__main__":
    fast_multi_download(url, "test_fast_origin.mp4", num_threads=8)
