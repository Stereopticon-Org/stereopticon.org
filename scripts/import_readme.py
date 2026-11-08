"""One-off import of the game tables in wiz3D's README.md into games/*.yml.

    python scripts/import_readme.py path/to/wiz3D/README.md

Existing game files are left alone, so it is safe to re-run; it only adds games
that are missing. After the switch-over, edit games/*.yml directly instead.
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gamedata import GAMES_DIR, EXCLUDED, slugify, save_game, dump_game
import yaml

src = open(sys.argv[1], encoding='utf-8').read().split('\n')
SECTIONS = {
    'Nvidia 3D Vision "Direct Mode" Games': ('3dv-direct', 'Native 3D Vision (Direct Mode)'),
    'AMD HD3D Native Games': ('hd3d', 'Native AMD HD3D'),
    'OpenGL Quad-Buffer Stereo Games': ('ogl-qb', 'Native OpenGL quad-buffer'),
    'DirectX 10 / 11 Games': ('injector', 'Stereo injector'),
    'DirectX 9 Games (32-bit)': ('injector', 'Stereo injector'),
    'DirectX 9 Games (64-bit)': ('injector', 'Stereo injector'),
    'DirectX 7 & 8 Games': ('injector', 'Stereo injector'),
    'Nvidia 3D Vision "Automatic-Aware" Games': ('3dv-auto', '3D Vision Automatic-aware'),
}

def status_of(t):
    s = t.lower()
    if 'not working' in s or 'not loading' in s or '❌' in t: return 'broken'
    if 'mostly' in s: return 'mostly'
    if 'partial' in s or '⚠' in t: return 'partial'
    if 'working' in s or '✅' in t: return 'working'
    return 'untested'

def api_of(path, section):
    p = path.lower()
    if 'opengl' in p: return 'OpenGL'
    if 'dx10-11' in p: return 'DX10/11'
    if '/dx11' in p: return 'DX11'
    if '/dx9' in p: return 'DX9'
    if 'dx8' in p and 'dx9' in p: return 'DX8'
    if 'dx8' in p: return 'DX8'
    if 'dx7' in p: return 'DX7'
    if p.startswith('`hd3d') or 'hd3d/' in p: return 'HD3D'
    return '?'

slug = slugify

games, excluded = [], []
section = None
cols = None
seen = {}
for line in src:
    m = re.match(r'^### (.+?)\s*$', line)
    if m:
        section = SECTIONS.get(m.group(1).strip())
        cols = None
        continue
    if line.startswith('## ') and section and 'Test Results' not in line:
        section = None
    if not section: continue
    if line.startswith('| Game'):
        cols = [c.strip() for c in line.strip('|').split('|')]
        continue
    if line.startswith('|---') or line.startswith('| ---'): continue
    if line.startswith('| ') and cols:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        # notes may contain | inside links rarely; pad / join
        if len(cells) > len(cols):
            cells = cells[:len(cols)-1] + ['|'.join(cells[len(cols)-1:])]
        row = dict(zip(cols, cells + [''] * (len(cols) - len(cells))))
        name = row['Game'].strip()
        lm = re.match(r'^\[([^\]]+)\]\((https?://[^)]+)\)$', name)
        link = lm.group(2) if lm else None
        if lm: name = lm.group(1)
        name = name.strip('*_ ')
        path = row.get('Install Path', '')
        paths = re.findall(r'`([^`]+)`', path)
        api = api_of(path, section)
        if section[0] == 'hd3d': api = 'HD3D'
        if section[0] == 'ogl-qb': api = 'OpenGL'
        prof = row.get('iZ3D Profile', '').strip()
        status_raw = row.get('Testing', '').strip()
        st = status_of(status_raw)
        notes = row.get('Notes', '').strip()
        # some DX10/11-section rows actually install the DX9 injector
        g = {
            'name': name,
            'slug': slug(name),
            'source': section[0],
            'api': api,
            'install': paths,
            'install_text': path.strip(),
            'iz3d_profile': True if prof == '✓' else (False if prof == '✕' else None),
            'status': st,
            'status_text': re.sub(r'^[✅⚠️❌️\s]+', '', status_raw).strip() or 'Untested',
            'notes': notes,
            'shots': [],
            'link': link,
        }
        key = g['slug']
        if key in seen:
            g['slug'] = key + '-' + section[0]
        seen[g['slug']] = 1
        games.append(g)
        continue
    m = re.match(r'^- \*\*Excluded \(([^)]+)\):\*\*\s*(.+)$', line)
    if m:
        reason = m.group(1)
        names = re.findall(r'\*([^*]+)\*', m.group(2))
        for n in names:
            excluded.append({'name': n.strip().rstrip('.'), 'reason': reason, 'source': section[0]})


api_fix = {'DX11': 'DX10/11', '?': 'DX9'}
added = 0
for g in games:
    path = os.path.join(GAMES_DIR, g['slug'] + '.yml')
    if os.path.exists(path):
        continue
    rec = {'slug': g['slug'], 'name': g['name'], 'api': api_fix.get(g['api'], g['api']), 'source': g['source'],
           'status': g['status'], 'install': g['install'], 'iz3d_profile': g['iz3d_profile'], 'link': g['link'],
           'notes': g['notes']}
    save_game(rec)
    added += 1
if not os.path.exists(EXCLUDED):
    with open(EXCLUDED, 'w', encoding='utf-8') as f:
        f.write('# Games left out on purpose. reason: shown as the group heading on the site.\n')
        f.write(yaml.safe_dump(excluded, sort_keys=False, allow_unicode=True, width=10000))
print('added %d games (%d in README), %d excluded' % (added, len(games), len(excluded)))
