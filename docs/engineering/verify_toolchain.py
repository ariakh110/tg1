"""Validate project-local skill discovery and mirrored Claude/Codex contents."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
left, right = root / '.agents/skills', root / '.claude/skills'

def inventory(directory):
    return {str(p.relative_to(directory)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts}

a, b = inventory(left), inventory(right)
assert a == b, 'Claude and Codex skill trees differ; synchronize before use'
skills = list(left.glob('*/SKILL.md'))
assert len(skills) == 46, f'Expected 46 installed skills, found {len(skills)}'
names = []
for p in skills:
    text = p.read_text(encoding='utf-8')
    assert text.startswith('---\n'), f'Missing skill frontmatter: {p}'
    name = re.search(r'^name:\s*(.+)$', text, re.M)
    assert name and re.search(r'^description:', text, re.M), f'Incomplete metadata: {p}'
    names.append(name[1].strip())
assert len(names) == len(set(names)), 'Duplicate skill names'
for filename in ['AGENTS.md', 'CLAUDE.md', '_bmad/scripts/render_skill.py',
                 'docs/engineering/WORKFLOW.md', 'docs/engineering/PROJECT_CONTEXT.md']:
    assert (root / filename).is_file(), filename
lock = json.loads((root / 'docs/engineering/toolchain-lock.json').read_text())
assert lock['bmad']['version'] == '6.12.4'
print(json.dumps({'status': 'PASS', 'skills_per_tool': len(skills),
                  'identical_files_per_tool': len(a), 'bmad': lock['bmad']['version']}))
if '--runtime' in sys.argv:
    subprocess.run(['uv', '--version'], check=True)
    result = subprocess.run(['uv', 'run', '--no-cache', str(root / '_bmad/scripts/resolve_config.py'),
                             '--project-root', str(root)], check=True, capture_output=True, encoding='utf-8')
    config = json.loads(result.stdout)
    assert config['core']['communication_language'] == 'Persian'
    print('PASS: uv runtime and merged Persian BMAD configuration')
