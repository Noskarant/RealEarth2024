import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lidar_autofetch import tile_grid, fetch_tile, discover


def test_grid_tiles_are_in_circle_and_not_bbox_only():
    c=tile_grid(4.6312222,45.5829444,3000)
    assert 20<len(c)<75
    assert len(c)==len(set(c))


def test_real_wfs_layer_and_lambert_bbox():
    sess=MagicMock()
    response=sess.get.return_value
    response.json.return_value={"features":[{"properties":{"url":"https://data.geopf.fr/tiles/MNT_0860_6522.tif","name":"MNT_0860_6522.tif"}}]}
    result=fetch_tile('mnt',860000,6522000,session=sess)
    assert result['name']=='MNT_0860_6522.tif'
    assert sess.get.call_args.kwargs['params']['typeName']=='IGNF_LIDAR-HD_TA:mnt-dalle'
    assert sess.get.call_args.kwargs['params']['bbox']=='860001,6522001,860999,6522999'


def test_discover_writes_reusable_lists_without_downloading(tmp_path,monkeypatch):
    monkeypatch.setattr('lidar_autofetch.tile_grid',lambda *args:[(860000,6522000)])
    monkeypatch.setattr('lidar_autofetch.fetch_tile',lambda k,x,y,**kw:{'url':f'https://data.geopf.fr/{k}.tif','name':f'{k}.tif','grid':[x,y]})
    center=[4.6312222,45.5829444]
    r=discover(center,3000,tmp_path,delay=0)
    assert r['counts']=={'mnt':1,'mns':1}
    assert 'mnt.tif' in (tmp_path/'mnt_urls.txt').read_text()
    assert (tmp_path/'index_lidar_hd.json').exists()
    monkeypatch.setattr('lidar_autofetch.fetch_tile',lambda *a,**kw:pytest.fail('must use cache'))
    reread=discover(center,3000,tmp_path)
    assert reread['counts']==r['counts']


def test_no_urls_when_index_empty(tmp_path,monkeypatch):
    monkeypatch.setattr('lidar_autofetch.tile_grid',lambda *args:[(860000,6522000)])
    monkeypatch.setattr('lidar_autofetch.fetch_tile',lambda *a,**kw:None)
    r=discover((4.6312222,45.5829444),3000,tmp_path,delay=0)
    assert r['counts']=={'mnt':0,'mns':0}
    assert (tmp_path/'mnt_urls.txt').read_text()==''
