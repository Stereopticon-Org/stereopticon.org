"""Shared helpers for the game data in games/*.yml."""
import os, re, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES_DIR = os.path.join(ROOT, 'games')
EXCLUDED = os.path.join(GAMES_DIR, '_excluded.yml')

STATUSES = ['working', 'mostly', 'partial', 'broken', 'untested']
SOURCES = ['injector', 'hd3d', '3dv-direct', '3dv-auto', 'ogl-qb']
APIS = ['DX7', 'DX8', 'DX9', 'DX10/11', 'DX12', 'Vulkan', 'OpenGL', 'HD3D']
CHECKS = ['Scene depth', 'HUD and menus', 'Shadows', 'Lighting and reflections', 'Post-processing', 'Cutscenes']
CHECK_VALUES = ['good', 'partial', 'bad']
LAYOUTS = ['lr', 'rl', 'tb', 'lrl']
FIELD_ORDER = ['name', 'api', 'source', 'status', 'install', 'iz3d_profile', 'link', 'notes', 'checks', 'shots', 'reports']


def slugify(name):
    s = name.lower().replace('&', 'and').replace("'", '').replace('’', '').replace('²', '2')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


class _Dumper(yaml.SafeDumper):
    pass


def _str(dumper, data):
    style = '|' if '\n' in data else None
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)


_Dumper.add_representer(str, _str)


def dump_game(game):
    ordered = {k: game[k] for k in FIELD_ORDER if k in game and game[k] not in (None, [], {}, '')}
    for k, v in game.items():
        if k not in ordered and k != 'slug' and v not in (None, [], {}, ''):
            ordered[k] = v
    return yaml.dump(ordered, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10000)


def load_games():
    games = []
    for fn in sorted(os.listdir(GAMES_DIR)):
        if not fn.endswith('.yml') or fn.startswith('_'):
            continue
        with open(os.path.join(GAMES_DIR, fn), encoding='utf-8') as f:
            g = yaml.safe_load(f) or {}
        g['slug'] = fn[:-4]
        games.append(g)
    return games


def load_excluded():
    if not os.path.exists(EXCLUDED):
        return []
    with open(EXCLUDED, encoding='utf-8') as f:
        return yaml.safe_load(f) or []


def save_game(game):
    path = os.path.join(GAMES_DIR, game['slug'] + '.yml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(dump_game(game))
    return path


def validate(game):
    """Return a list of problems with one game record."""
    p = []
    where = game.get('slug', '?')
    if not game.get('name'): p.append(where + ': missing name')
    if game.get('status') not in STATUSES: p.append(where + ': status must be one of ' + ', '.join(STATUSES))
    if game.get('source') not in SOURCES: p.append(where + ': source must be one of ' + ', '.join(SOURCES))
    if game.get('api') not in APIS: p.append(where + ': api must be one of ' + ', '.join(APIS))
    for k, v in (game.get('checks') or {}).items():
        if k not in CHECKS: p.append(where + ': unknown check "%s"' % k)
        if v not in CHECK_VALUES: p.append(where + ': check "%s" must be good, partial or bad' % k)
    for s in game.get('shots') or []:
        if not isinstance(s, dict) or not s.get('file'): p.append(where + ': each shot needs a file'); continue
        if s.get('layout', 'lr') not in LAYOUTS: p.append(where + ': shot layout must be one of ' + ', '.join(LAYOUTS))
        if not os.path.exists(os.path.join(ROOT, 'shots', where, s['file'])):
            p.append(where + ': screenshot not found: shots/%s/%s' % (where, s['file']))
    return p
