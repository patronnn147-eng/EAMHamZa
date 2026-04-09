import os, re

versions_dir = 'app/backend/alembic/versions'
revisions = {}
all_files = {}

for f in sorted(os.listdir(versions_dir)):
    if f.endswith('.py') and f != '__pycache__':
        filepath = os.path.join(versions_dir, f)
        with open(filepath) as fp:
            content = fp.read()
        
        # Match: revision = 'xxx' or revision: str = 'xxx'
        rev_match = re.search(r"revision\s*(?::\s*str\s*)?=\s*['\"]([^'\"]+)['\"]", content)
        
        # Find down_revision - could be tuple or single
        down_tuple = re.search(r"down_revision\s*(?::\s*[^=]+)?=\s*\(([^)]+)\)", content)
        down_single = re.search(r"down_revision\s*(?::\s*[^=]+)?=\s*['\"]([^'\"]+)['\"]", content)
        
        if rev_match:
            rev_id = rev_match.group(1)
            if down_tuple:
                parts = [x.strip().strip("'\"") for x in down_tuple.group(1).split(',')]
                down_rev = tuple(parts)
            elif down_single:
                down_rev = down_single.group(1)
            else:
                down_rev = None
            revisions[rev_id] = down_rev
            all_files[rev_id] = f

all_down_revs = set()
for v in revisions.values():
    if isinstance(v, tuple):
        all_down_revs.update(v)
    elif v is not None:
        all_down_revs.add(v)

heads = set(revisions.keys()) - all_down_revs

print(f'Total revisions: {len(revisions)}')
print(f'Heads: {len(heads)}')
for h in sorted(heads):
    print(f'  HEAD: {h} ({all_files.get(h, "?")})')

print()
print('=== FULL CHAIN ===')
for rev, down in sorted(revisions.items()):
    print(f'{rev:45s} <- {down}')
