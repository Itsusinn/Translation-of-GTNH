"""Generate and audit translation additions without copying official Chinese assets."""

import argparse
from collections import Counter
from hashlib import file_digest, sha256
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile

from build_release import build_release, PATCH_MANIFEST, REPO


SUPPLEMENT = 'config/txloader/forceload/____gtnh_additions_zhcn/lang/zh_CN.lang'
CUSTOM_NAMES = 'config/txloader/forceload/____gtnhoverridenames_zhcn/lang/zh_CN.lang'
INFLECTION = 'config/txloader/load/gregtech/inflection/zh_CN.json'
FORMAT = re.compile(r'%(?:\d+\$)?[-#+0,(<]*\d*(?:\.\d+)?[tT]?[a-zA-Z%]')


def entries(text, unique=False):
    result = {}
    for line in text.splitlines():
        if '=' not in line or line.lstrip().startswith(('#', '//')):
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        if key.startswith('S:'):
            key = key[2:].strip('"')
        if unique and key in result:
            raise ValueError(f'Duplicate delta language key: {key}')
        result[key] = value
    return result


def inventory(archive, prefix):
    english, chinese, owners = {}, {}, {}
    for info in archive.infolist():
        if not info.filename.startswith(prefix) or info.is_dir():
            continue
        relative = info.filename[len(prefix):]
        if relative.startswith('mods/') and relative.endswith('.jar'):
            with ZipFile(BytesIO(archive.read(info))) as jar:
                for name in jar.namelist():
                    if not re.fullmatch(r'assets/[^/]+/lang/(en_US|zh_CN)\.lang', name, re.I):
                        continue
                    values = entries(jar.read(name).decode('utf-8-sig'))
                    if name.lower().endswith('zh_cn.lang'):
                        chinese.update(values)
                    else:
                        english.update(values)
                        owners.update({key: relative + '!' + name for key in values})
        elif relative.lower().endswith('zh_cn.lang'):
            chinese.update(entries(archive.read(info).decode('utf-8-sig')))
        elif relative.endswith(('/en_US.lang', 'betterquesting/lang/template.lang')):
            values = entries(archive.read(info).decode('utf-8-sig'))
            english.update(values)
            owners.update({key: relative for key in values})
    return english, chinese, owners


def package_path(relative):
    if relative.startswith('resources/'):
        return 'config/txloader/forceload/' + relative[len('resources/'):]
    return relative


def delta_assets(archive, prefix, baseline):
    assets = {}
    for relative in (SUPPLEMENT, CUSTOM_NAMES):
        text = (REPO / relative).read_text(encoding='utf-8-sig')
        values = entries(text, unique=True)
        redundant = {key for key, value in values.items() if baseline.get(key) == value}
        lines = [line for line in text.splitlines()
                 if '=' not in line or line.split('=', 1)[0].strip() not in redundant]
        assets[relative] = '\n'.join(lines) + '\n'
    # This grammar rule is maintained by this patch, not supplied by the pack.
    inflection = (REPO / INFLECTION).read_text(encoding='utf-8-sig')
    official = prefix + INFLECTION
    if official not in archive.namelist() or archive.read(official).decode('utf-8-sig') != inflection:
        assets[INFLECTION] = inflection
    corrections = json.loads((REPO / 'scripts/corrections-2.9.0.json').read_text(encoding='utf-8'))
    grouped = {}
    for row in corrections:
        relative = row['file']
        if not relative.startswith('resources/') or '..' in Path(relative).parts:
            raise ValueError(f'Correction must use a separate resource overlay: {relative}')
        original = prefix + 'config/txloader/load/' + relative[len('resources/'):]
        baseline_file = entries(archive.read(original).decode('utf-8-sig'))
        key, value = row['key'], row['translation']
        if baseline_file.get(key) not in (row['source'], value):
            raise ValueError(f'Official correction source changed: {relative}: {key}')
        if value == baseline_file.get(key) or value == baseline.get(key):
            continue
        values = grouped.setdefault(relative, {})
        if key in values:
            raise ValueError(f'Duplicate correction: {relative}: {key}')
        values[key] = value
    for relative, values in grouped.items():
        lines = ['# GTNH 2.9.0 中文增量校正；官方完整语言文件保持原样。']
        lines.extend(key + '=' + value for key, value in sorted(values.items()))
        assets[relative] = '\n'.join(lines) + '\n'
    return assets, corrections


def current_assets():
    return {path.relative_to(REPO).as_posix(): path
            for folder in ('config', 'resources')
            for path in (REPO / folder).rglob('*') if path.is_file()}


def write_delta(assets, archive_digest):
    removed = []
    for relative, path in current_assets().items():
        if relative not in assets:
            if not path.resolve().is_relative_to(REPO):
                raise ValueError(f'Refusing to remove path outside repository: {path}')
            path.unlink()
            removed.append(relative)
    for relative, text in assets.items():
        path = REPO / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != text.encode('utf-8'):
            path.write_text(text, encoding='utf-8', newline='\n')
    legacy = REPO / 'GregTech.lang'
    if legacy.exists():
        legacy.unlink()
        removed.append('GregTech.lang')
    for folder in ('config', 'resources'):
        for path in sorted((REPO / folder).rglob('*'), key=lambda path: len(path.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()  # Only empty directories; never recursively removes a tree.
                except OSError:
                    pass
    manifest = {
        'modpack': 'GT New Horizons 2.9.0',
        'official_archive_sha256': archive_digest,
        'policy': 'Only additions and corrections; no official asset paths or identical language pairs',
        'files': [{'path': relative, 'sha256': sha256(text.encode('utf-8')).hexdigest()}
                  for relative, text in sorted(assets.items())],
    }
    PATCH_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--sync', action='store_true', help='Generate delta assets and remove full copies from config/resources')
    parser.add_argument('--output', type=Path, default=REPO / 'dist')
    parser.add_argument('--build', action='store_true', help='Build only after the delta audit passes')
    args = parser.parse_args()
    with ZipFile(args.archive) as archive:
        prefixes = {name.split('/.minecraft/', 1)[0] + '/.minecraft/'
                    for name in archive.namelist() if '/.minecraft/' in name}
        if len(prefixes) != 1:
            raise ValueError('Expected exactly one Prism .minecraft directory')
        prefix = prefixes.pop()
        if prefix.split('/')[0] != 'GT New Horizons 2.9.0':
            raise ValueError('This delta targets GTNH 2.9.0')
        english, baseline, owners = inventory(archive, prefix)
        assets, corrections = delta_assets(archive, prefix, baseline)
        patch = {}
        for relative, text in assets.items():
            if relative.lower().endswith('zh_cn.lang'):
                for key, value in entries(text, unique=True).items():
                    if key in patch:
                        raise ValueError(f'Key appears in multiple delta files: {key}')
                    patch[key] = value
        effective = baseline | patch
        repeated = sorted(key for key, value in patch.items() if baseline.get(key) == value)
        overwritten = sorted(relative for relative in assets if prefix + package_path(relative) in archive.namelist())
        missing = [{'key': key, 'source': value, 'owner': owners[key]}
                   for key, value in english.items() if value.strip() and key not in effective]
        format_errors = [key for key, value in patch.items() if key in english
                         and Counter(FORMAT.findall(english[key])) != Counter(FORMAT.findall(value))]
        correction_errors = [row['key'] for row in corrections
                             if effective.get(row['key']) != row['translation']]
        template = entries(archive.read(prefix + 'config/txloader/forceload/betterquesting/lang/template.lang').decode('utf-8-sig'))
        quest_missing = sorted(template.keys() - effective.keys())
        quest_obsolete = sorted(key for key in patch if key.startswith('betterquesting.quest') and key not in template)
        with args.archive.open('rb') as source:
            archive_digest = file_digest(source, 'sha256').hexdigest()
        report = {
            'modpack': prefix.split('/')[0],
            'archive_sha256': archive_digest,
            'scope': 'Official Chinese baseline plus incremental patch; excludes hardcoded and dynamically generated text',
            'english_keys': len(english),
            'official_chinese_keys': len(baseline),
            'delta_keys': len(patch),
            'delta_files': len(assets),
            'corrected_keys': len(corrections),
            'quest_keys': len(template),
            'quest_covered': len(template.keys() & effective.keys()),
            'quest_missing': quest_missing,
            'quest_obsolete': quest_obsolete,
            'missing': missing,
            'translation_format_errors': format_errors,
            'correction_errors': correction_errors,
            'repeated_official_language_keys': repeated,
            'overwritten_official_asset_paths': overwritten,
            'inherited_english_paragraph_candidates': [
                {'key': key, 'source': value, 'owner': owners[key]}
                for key, value in english.items() if effective.get(key) == value
                and len(value) > 90 and re.search(r'[A-Za-z]{3} [A-Za-z]{3}', value)],
        }
    args.output.mkdir(parents=True, exist_ok=True)
    invalid = any((missing, format_errors, correction_errors, repeated, overwritten, quest_missing, quest_obsolete))
    if not invalid:
        if args.sync:
            report['removed_redundant_files'] = write_delta(assets, archive_digest)
        else:
            current = current_assets()
            if current.keys() != assets.keys() or any(
                    current[name].read_text(encoding='utf-8-sig') != text for name, text in assets.items()):
                raise ValueError('Repository contains full copies or stale delta files; run --sync')
    (args.output / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'Delta: {len(patch)} keys in {len(assets)} files; '
          f'{len(repeated)} official duplicates; {len(overwritten)} official paths overwritten; '
          f'{len(missing)} missing keys; quests {report["quest_covered"]}/{len(template)}; '
          f'{len(format_errors)} format errors')
    if invalid:
        raise SystemExit('Delta audit failed; see validation.json')
    if args.build:
        build_release(args.output)


if __name__ == '__main__':
    main()
