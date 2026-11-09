"""Download official IGN LiDAR HD tile URL lists exported by the IGN portal.

Use *both* MNT and MNS URL text files from the geographic 3 km selection.
These are 0.5 m GeoTIFF products in IGN69/Lambert-93 where available.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests
import time


def download_list(url_file:Path,dest:Path,*,session=None)->list[Path]:
    if not url_file.exists():raise FileNotFoundError(url_file)
    links=[]
    for line in url_file.read_text(encoding='utf-8-sig').splitlines():
        u=line.strip()
        if not u or u.startswith('#'):continue
        pu=urlparse(u)
        if pu.scheme!='https' or not pu.hostname or pu.username or pu.password:
            raise ValueError('Unexpected or insecure tile URL; only HTTPS is allowed')
        filename=Path(unquote(pu.path)).name
        if not filename.lower().endswith(('.tif','.tiff','.zip')):
            raise ValueError(f'IGN URL does not end with tif/zip: {u[:120]}')
        links.append((u,filename))
    if not links:raise ValueError('IGN link list is empty')
    dest.mkdir(parents=True,exist_ok=True)
    sess=session or requests.Session()
    paths=[]
    for idx,(url,filename) in enumerate(links,1):
        target=dest/filename
        if target.is_file() and target.stat().st_size>1000:
            paths.append(target);continue
        part=target.with_suffix(target.suffix+'.part')
        headers={}
        if part.exists():headers['Range']=f'bytes={part.stat().st_size}-'
        for attempt in range(4):
            try:
                with sess.get(url,headers=headers,stream=True,timeout=180) as r:
                    r.raise_for_status()
                    append=(r.status_code==206 and 'Range' in headers)
                    with part.open('ab' if append else 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:f.write(chunk)
                if part.stat().st_size<=1000:raise ValueError('Tile file too small')
                part.replace(target);break
            except (requests.RequestException,OSError,ValueError):
                if attempt==3:raise
                time.sleep(2*(attempt+1))
        paths.append(target)
        if idx%10==0:print(f'LiDAR: {idx}/{len(links)} downloaded or reused')
    return paths


def main():
    p=argparse.ArgumentParser(description='IGN 0.5m MNT/MNS from exported tile URLs')
    p.add_argument('url_file',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();files=download_list(a.url_file,a.output)
    print(f'{len(files)} LiDAR files present under {a.output}')

if __name__=='__main__':main()
