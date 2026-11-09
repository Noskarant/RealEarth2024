"""MSFS2024-compatible glTF writer: external PNG textures and shared assets.

Trimesh glTF defaults to embedding PIL textures in bufferViews. MSFS2024 only
supports external image URIs, so material images must be extracted to PNG.
Repeated texture content is stored once, with a BitmapConfiguration sidecar.
References: MSFS2024 glTF Format, Texture XML Properties (SDK).
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import uuid

PNG_SIG = b'\x89PNG\r\n\x1a\n'


def emit_scene(scene, name: str, model_dir: Path, namespace: uuid.UUID) -> dict:
    model_dir.mkdir(parents=True, exist_ok=True)
    parts = scene.export(file_type='gltf', include_normals=True)
    gltf_key = next((x for x in parts if x.endswith('.gltf')), None)
    if gltf_key is None:
        raise ValueError('Trimesh did not produce a .gltf')
    raw = parts[gltf_key]
    doc = json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
    old_views = doc.get('bufferViews', [])
    old_buffers = doc.get('buffers', [])
    used_view = set()
    for accessor in doc.get('accessors', []):
        if 'bufferView' in accessor:
            used_view.add(accessor['bufferView'])
        sparse = accessor.get('sparse', {})
        for part_name in ('indices', 'values'):
            if 'bufferView' in sparse.get(part_name, {}):
                used_view.add(sparse[part_name]['bufferView'])
    written_textures = set()
    tex_dir = model_dir / 'texture'
    for img in doc.get('images', []):
        if 'bufferView' in img:
            view = old_views[img['bufferView']]
            uri = old_buffers[view['buffer']]['uri']
            buffer_bytes = parts[uri]
            if not isinstance(buffer_bytes, bytes):
                buffer_bytes = buffer_bytes.encode('utf-8')
            start = view.get('byteOffset', 0)
            image_bytes = buffer_bytes[start:start + view['byteLength']]
        elif 'uri' in img:
            uri = img['uri']
            if uri not in parts:
                raise ValueError(f'Missing exported texture {uri}')
            image_bytes = parts[uri]
            if not isinstance(image_bytes, bytes):
                image_bytes = image_bytes.encode('utf-8')
        else:
            raise ValueError('Texture must have bufferView or URI')
        if not image_bytes.startswith(PNG_SIG):
            raise ValueError('Non-PNG texture: MSFS2024 requires an external PNG')
        digest = hashlib.sha256(image_bytes).hexdigest()[:18]
        filename = f'sm_material_{digest}.png'
        tex_dir.mkdir(exist_ok=True)
        texture_file = tex_dir / filename
        if not texture_file.exists():
            texture_file.write_bytes(image_bytes)
        sidecar = tex_dir / (filename + '.xml')
        if not sidecar.exists():
            sidecar.write_text(
                '<BitmapConfiguration>\n'
                '  <BitmapSlot>MTL_BITMAP_DECAL0</BitmapSlot>\n'
                '  <UserFlags Type="_DEFAULT">+QUALITYHIGH</UserFlags>\n'
                '</BitmapConfiguration>\n', encoding='utf-8')
        img.clear()
        img['uri'] = 'texture/' + filename
        written_textures.add(filename)
    # Remove the image-only buffers. Rebuild referenced bufferView indices.
    view_map = {old: new for new, old in enumerate(sorted(used_view))}
    view_list = [dict(old_views[x]) for x in sorted(used_view)]
    used_buffers = sorted({v['buffer'] for v in view_list})
    buffer_map = {old: new for new, old in enumerate(used_buffers)}
    new_buffers = []
    for old_idx in used_buffers:
        original = old_buffers[old_idx]
        uri = original['uri']
        if uri not in parts:
            raise ValueError('Missing binary glTF payload ' + uri)
        raw_bin = parts[uri]
        if not isinstance(raw_bin, bytes):
            raw_bin = raw_bin.encode('utf-8')
        new_uri = f'{name}_geom_{len(new_buffers)}.bin'
        (model_dir / new_uri).write_bytes(raw_bin)
        new_buffers.append({'uri': new_uri, 'byteLength': len(raw_bin)})
    for v in view_list:
        v['buffer'] = buffer_map[v['buffer']]
    for a in doc.get('accessors', []):
        if 'bufferView' in a:
            a['bufferView'] = view_map[a['bufferView']]
        sparse = a.get('sparse', {})
        for k in ('indices', 'values'):
            if 'bufferView' in sparse.get(k, {}):
                sparse[k]['bufferView'] = view_map[sparse[k]['bufferView']]
    doc['bufferViews'] = view_list
    doc['buffers'] = new_buffers
    target = model_dir / f'{name}.gltf'
    target.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    guid = '{' + str(uuid.uuid5(namespace, 'model:' + name)).upper() + '}'
    model_info = ET.Element('ModelInfo', guid=guid, version='1.1')
    lods = ET.SubElement(model_info, 'LODS')
    ET.SubElement(lods, 'LOD', minSize='0', ModelFile=target.name)
    ET.ElementTree(model_info).write(model_dir / f'{name}.xml', encoding='utf-8', xml_declaration=True)
    return {'name':name,'guid':guid,'path':str(target),
            'textures':sorted(written_textures)}


def validate_gltf_files(model_dir: Path) -> dict:
    checked = 0
    pngs = set()
    for file in model_dir.glob('*.gltf'):
        doc = json.loads(file.read_text(encoding='utf-8'))
        assert doc.get('asset', {}).get('version') == '2.0'
        for buf in doc.get('buffers', []):
            uri = buf.get('uri', '')
            assert uri and not uri.startswith('data:'), file.name
            assert (model_dir / uri).is_file(), f'{file.name}: missing {uri}'
        for image in doc.get('images', []):
            assert 'bufferView' not in image, f'{file.name}: embedded image unsupported by SDK'
            uri = image.get('uri','')
            assert uri.startswith('texture/') and uri.endswith('.png'), f'{file.name}: bad image uri {uri}'
            path = model_dir / uri
            assert path.is_file() and path.read_bytes().startswith(PNG_SIG)
            assert (model_dir / (uri + '.xml')).is_file(), f'{file.name}: missing texture sidecar'
            pngs.add(uri)
        for mesh in doc.get('meshes', []):
            for primitive in mesh.get('primitives', []):
                attrs = primitive.get('attributes', {})
                assert 'NORMAL' in attrs, f'{file.name}: missing NORMAL required by FS2024'
                pos = doc['accessors'][attrs['POSITION']]
                norm = doc['accessors'][attrs['NORMAL']]
                assert norm['type'] == 'VEC3' and norm['componentType'] == 5126, file.name
                assert norm['count'] == pos['count'], file.name
        checked += 1
    return {'gltf_checked':checked,'shared_png_textures':len(pngs)}
