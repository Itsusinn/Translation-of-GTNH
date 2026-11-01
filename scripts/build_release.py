"""Build a reproducible installation ZIP from the checked-out translation files."""

import argparse
from hashlib import file_digest, sha256
import json
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


REPO = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = 'GTNH-2.9.0-zh_CN.zip'
PATCH_MANIFEST = REPO / 'scripts/patch-manifest-2.9.0.json'


def packaged_files():
    manifest = json.loads(PATCH_MANIFEST.read_text(encoding='utf-8'))
    expected = {row['path']: row['sha256'] for row in manifest['files']}
    if len(expected) != len(manifest['files']):
        raise ValueError('Duplicate manifest entry')
    actual = {path.relative_to(REPO).as_posix()
              for folder in ('config', 'resources')
              for path in (REPO / folder).rglob('*') if path.is_file()}
    if actual != expected.keys():
        raise ValueError('Translation files differ from the audited delta; run update_modpack_translation.py --sync')
    for relative, digest in sorted(expected.items()):
        parts = PurePosixPath(relative)
        if parts.is_absolute() or '..' in parts.parts or parts.parts[0] not in ('config', 'resources'):
            raise ValueError(f'Unsafe manifest path: {relative}')
        path = REPO / relative
        data = path.read_text(encoding='utf-8-sig').encode('utf-8')
        if sha256(data).hexdigest() != digest:
            raise ValueError(f'Unaudited translation change: {relative}')
        if relative.startswith('resources/'):
            relative = 'config/txloader/forceload/' + relative[len('resources/'):]
        yield relative, path
    for source, target in (
        ('GTNH介绍.txt', 'GTNH介绍.txt'),
        ('README.md', '看我.md'),
        ('LICENSE', 'LICENSE'),
    ):
        yield target, REPO / source


def build_release(output):
    output = Path(output)
    payload = {}
    for name, path in packaged_files():
        if name in payload:
            raise ValueError(f'Duplicate package entry: {name}')
        # Normalize text so Windows checkouts and Linux CI build the same ZIP.
        text = path.read_text(encoding='utf-8-sig')
        if path.suffix == '.json':
            json.loads(text)
        elif path.suffix == '.xml':
            ET.fromstring(text)
        payload[name] = text.encode('utf-8')
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / ARCHIVE_NAME
    with ZipFile(archive_path, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in payload.items():
            info = ZipInfo(name)
            info.create_system = 3
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    with ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Package CRC check failed')
    with archive_path.open('rb') as archive_file:
        digest = file_digest(archive_file, 'sha256').hexdigest()
    archive_path.with_suffix('.zip.sha256').write_text(
        f'{digest}  {archive_path.name}\n', encoding='ascii', newline='\n')
    print(f'Built {archive_path} ({len(payload)} files), SHA-256 {digest}')
    return archive_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=REPO / 'dist')
    args = parser.parse_args()
    build_release(args.output)
