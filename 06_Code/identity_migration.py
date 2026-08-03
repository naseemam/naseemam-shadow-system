"""Identity export/import utilities for Ameer

Usage:
  python identity_migration.py export --repo . --output ameer_export.zip
  python identity_migration.py import --archive ameer_export.zip --dest /path/to/repo

Behavior:
- By default looks for identity in `.ameer/identity.json` and memories in `.ameer/memory/`.
- Creates a manifest.json with checksums and metadata.
"""

import argparse
import json
import os
import shutil
import zipfile
import hashlib
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid

APP_DIR_NAME = ".ameer"
IDENTITY_FILENAME = "identity.json"
MEMORY_DIRNAME = "memory"
MANIFEST_NAME = "manifest.json"

class Identity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Ameer"
    founder: str
    constitution_version: Optional[str] = None
    created_at: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def collect_files(repo_root: str, identity_file: Optional[str]=None, memory_dir: Optional[str]=None):
    app_dir = os.path.join(repo_root, APP_DIR_NAME)
    files = {}

    id_path = identity_file or os.path.join(app_dir, IDENTITY_FILENAME)
    if os.path.exists(id_path):
        files['identity'] = os.path.relpath(id_path, repo_root).replace('\\\\','/')
    else:
        raise FileNotFoundError(f"Identity file not found at {id_path}")

    mem_dir = memory_dir or os.path.join(app_dir, MEMORY_DIRNAME)
    if os.path.isdir(mem_dir):
        mem_files = []
        for root, _, fnames in os.walk(mem_dir):
            for fn in fnames:
                full = os.path.join(root, fn)
                mem_files.append(os.path.relpath(full, repo_root).replace('\\\\','/'))
        files['memory_files'] = mem_files
    else:
        files['memory_files'] = []

    return files

def create_manifest(repo_root: str, files_map: dict, extra: dict=None):
    manifest = {
        'exported_at': datetime.utcnow().isoformat(),
        'repo_root': os.path.abspath(repo_root),
        'files': {},
    }
    for key, rel in files_map.items():
        if isinstance(rel, list):
            manifest['files'][key] = []
            for r in rel:
                p = os.path.join(repo_root, r)
                manifest['files'][key].append({'path': r, 'sha256': sha256_of_file(p)})
        else:
            p = os.path.join(repo_root, rel)
            manifest['files'][key] = {'path': rel, 'sha256': sha256_of_file(p)}
    if extra:
        manifest['extra'] = extra
    return manifest

def export_identity(repo_root: str, output: str, identity_file: Optional[str]=None, memory_dir: Optional[str]=None):
    files_map = collect_files(repo_root, identity_file, memory_dir)
    manifest = create_manifest(repo_root, files_map)

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        # add identity
        z.write(os.path.join(repo_root, files_map['identity']), arcname=files_map['identity'])
        # add memory files
        for r in files_map.get('memory_files', []):
            z.write(os.path.join(repo_root, r), arcname=r)
        # add manifest
        z.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, ensure_ascii=False))

    print(f"Exported identity bundle to {output}")
    return output

def import_identity(archive: str, dest_repo: str, overwrite: bool=False):
    with zipfile.ZipFile(archive, 'r') as z:
        namelist = z.namelist()
        # extract manifest first
        if MANIFEST_NAME in namelist:
            manifest = json.loads(z.read(MANIFEST_NAME).decode('utf-8'))
        else:
            manifest = None
        # extract files into .ameer dir
        for member in namelist:
            if member == MANIFEST_NAME:
                continue
            # target path
            target = os.path.join(dest_repo, member)
            target_dir = os.path.dirname(target)
            os.makedirs(target_dir, exist_ok=True)
            if os.path.exists(target) and not overwrite:
                raise FileExistsError(f"Target exists: {target}. Use --overwrite to replace.")
            with z.open(member) as src, open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst)
    print(f"Imported identity bundle into {dest_repo}")
    return dest_repo

def cli():
    p = argparse.ArgumentParser(description='Ameer identity export/import tool')
    sub = p.add_subparsers(dest='cmd')

    pe = sub.add_parser('export')
    pe.add_argument('--repo', default='.', help='Repository root')
    pe.add_argument('--output', required=True, help='Output zip file')
    pe.add_argument('--identity-file', help='Path to identity.json (optional)')
    pe.add_argument('--memory-dir', help='Path to memory dir (optional)')

    pi = sub.add_parser('import')
    pi.add_argument('--archive', required=True, help='Zip archive to import')
    pi.add_argument('--dest', default='.', help='Destination repository root')
    pi.add_argument('--overwrite', action='store_true', help='Overwrite existing files')

    args = p.parse_args()
    if args.cmd == 'export':
        export_identity(args.repo, args.output, args.identity_file, args.memory_dir)
    elif args.cmd == 'import':
        import_identity(args.archive, args.dest, args.overwrite)
    else:
        p.print_help()

if __name__ == '__main__':
    cli()
