"""Self-authored procedural PBR base-color tiles for roofs and walls.

These are not photos or assertions about actual façades. In the MSFS SDK the
embedded glTF base-color textures must still be validated at compile/runtime.
"""
from __future__ import annotations
from functools import lru_cache
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE=256


def make_texture(kind:str)->Image.Image:
    rng=random.Random('saintmaurice-hd:'+kind)
    if kind=='roof_clay':
        im=Image.new('RGB',(SIZE,SIZE),(146,76,58));draw=ImageDraw.Draw(im)
        row_h=17;tw=30
        for r,y in enumerate(range(-row_h,SIZE+row_h,row_h)):
            offset=tw//2 if r%2 else 0
            for x in range(-tw-offset,SIZE+tw,tw):
                delta=rng.randint(-17,17)
                fill=(max(80,170+delta),max(40,87+delta//2),max(29,62+delta//3))
                draw.rounded_rectangle((x+1,y,x+tw-2,y+row_h+2),radius=5,
                                       fill=fill,outline=(95,45,38),width=1)
                draw.arc((x+3,y+5,x+tw-5,y+row_h+9),start=5,end=175,
                         fill=(198,111,77),width=1)
    elif kind=='roof_slate':
        im=Image.new('RGB',(SIZE,SIZE),(74,79,82));draw=ImageDraw.Draw(im)
        tw=38;rh=18
        for r,y in enumerate(range(-rh,SIZE+rh,rh)):
            for x in range(-tw-(r%2)*tw//2,SIZE+tw,tw):
                d=rng.randint(-10,10)
                draw.rectangle((x,y,x+tw-2,y+rh-2),fill=(83+d,88+d,91+d),
                               outline=(52,57,62),width=1)
    elif kind=='roof_metal':
        im=Image.new('RGB',(SIZE,SIZE),(110,112,108));draw=ImageDraw.Draw(im)
        for x in range(0,SIZE,16):draw.line((x,0,x,SIZE),fill=(74,76,73),width=2)
    elif kind=='wall_stone':
        im=Image.new('RGB',(SIZE,SIZE),(168,156,138));draw=ImageDraw.Draw(im)
        tw=53;rh=31
        for r,y in enumerate(range(-rh,SIZE+rh,rh)):
            for x in range(-tw-(r%2)*tw//2,SIZE+tw,tw):
                d=rng.randint(-18,18);draw.rectangle((x+1,y+1,x+tw-3,y+rh-3),
                    fill=(min(255,177+d),min(255,165+d),min(255,145+d)),
                    outline=(121,113,100),width=1)
    else:
        tones={'wall_plaster':(212,195,165),'wall_lime':(231,219,188)}
        color=tones.get(kind,(206,195,172))
        im=Image.new('RGB',(SIZE,SIZE),color)
    # Subtle mineral/ceramic noise for close-range normal-like variation.
    a=np.array(im,dtype=np.int16)
    noise=np.random.default_rng(sum(ord(x) for x in kind)).normal(0,3,(SIZE,SIZE,1))
    return Image.fromarray(np.clip(a+noise,0,255).astype('uint8'),'RGB')


@lru_cache(maxsize=12)
def texture(kind):return make_texture(kind)


def choose_kind(material_name:str,mode:str)->str:
    t=(material_name or '').lower()
    if mode=='roof':
        if 'ardoise' in t or 'schiste' in t:return 'roof_slate'
        if 'metal' in t or 'métal' in t or 'bac acier' in t:return 'roof_metal'
        return 'roof_clay'
    if 'pierre' in t or 'moellon' in t or 'granite' in t:return 'wall_stone'
    if 'chaux' in t:return 'wall_lime'
    return 'wall_plaster'


def uv_from_vertices(v:np.ndarray,typ:str)->np.ndarray:
    # glTF +X East, -Z North, +Y up; UV tiles every ~3m (roofs) / ~4m (walls).
    if typ=='roof': return np.column_stack((v[:,0]/3.0,-v[:,2]/3.0))
    return np.column_stack(((v[:,0]*0.75-v[:,2]*0.66)/4.0,v[:,1]/4.0))
