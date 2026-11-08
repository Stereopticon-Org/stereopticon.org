"""Apply an approved 'Game test report' issue to games/*.yml.

Run by .github/workflows/report-to-pr.yml when a maintainer adds the
`approved` label. Reads the issue from GITHUB_EVENT_PATH (or a JSON file given
as the first argument), updates or creates the game's file, downloads any
attached screenshots into shots/<slug>/, and writes pr-title.txt and
pr-body.txt for the pull request step.
"""
import datetime, json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gamedata import ROOT, GAMES_DIR, CHECKS, slugify, save_game, load_games
import yaml

RESULT = {'Working': 'working', 'Mostly working': 'mostly', 'Partial': 'partial', 'Not working': 'broken'}
CHECK = {'Correct': 'good', 'Some issues': 'partial', 'Wrong': 'bad'}
LAYOUT = {'Left | Right': 'lr', 'Right | Left (cross-eyed)': 'rl', 'Top / bottom': 'tb', 'Parallel + Cross (L | R | L)': 'lrl'}
FOLDER_SOURCE = [('hd3d', 'hd3d'), ('3d-vision-direct', '3dv-direct'), ('opengl', 'ogl-qb')]
EXT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}
ATTACH = re.compile(r'https://github\.com/user-attachments/(?:assets|files)/[A-Za-z0-9/_.-]+')


def sections(body):
    out, key = {}, None
    for line in (body or '').replace('\r\n', '\n').split('\n'):
        m = re.match(r'^###\s+(.+?)\s*$', line)
        if m:
            key = m.group(1); out[key] = []
        elif key:
            out[key].append(line)
    clean = {}
    for k, v in out.items():
        t = '\n'.join(v).strip()
        clean[k] = '' if t == '_No response_' else t
    return clean


def download(url, dest_base):
    headers = {'User-Agent': 'stereopticon-report-bot'}
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get('Content-Type', '').split(';')[0].strip()
        data = r.read()
    ext = EXT.get(ctype)
    if not ext:
        print('skipping attachment with type %r: %s' % (ctype, url))
        return None
    path = dest_base + '.' + ext
    with open(path, 'wb') as f:
        f.write(data)
    return os.path.basename(path)


def main():
    event_path = sys.argv[1] if len(sys.argv) > 1 else os.environ['GITHUB_EVENT_PATH']
    with open(event_path, encoding='utf-8') as f:
        issue = json.load(f)['issue']
    num = issue['number']
    s = sections(issue.get('body'))
    name = s.get('Game', '').strip()
    if not name:
        sys.exit('Issue #%d has no game name' % num)

    by_name = {g['name'].lower(): g for g in load_games()}
    game = by_name.get(name.lower())
    slug = game['slug'] if game else slugify(name)
    if not game:
        path = os.path.join(GAMES_DIR, slug + '.yml')
        game = yaml.safe_load(open(path, encoding='utf-8')) if os.path.exists(path) else None
        if game: game['slug'] = slug
    is_new = game is None
    folder = s.get('Folder used', '').strip().strip('`')
    if is_new:
        source = 'injector'
        for needle, src in FOLDER_SOURCE:
            if needle in folder.lower(): source = src
        api = s.get('API', 'DX9')
        game = {'slug': slug, 'name': name, 'api': api if api != 'Not sure' else 'DX9', 'source': source,
                'status': 'untested', 'install': [folder] if folder else []}

    result = RESULT.get(s.get('Result', ''))
    if result:
        game['status'] = result
    checks = dict(game.get('checks') or {})
    for label in CHECKS:
        v = CHECK.get(s.get(label, ''))
        if v: checks[label] = v
    if checks:
        game['checks'] = checks

    shots = list(game.get('shots') or [])
    layout = LAYOUT.get(s.get('Screenshot layout', ''), 'lr')
    urls = ATTACH.findall(s.get('Stereo screenshot', ''))
    if urls:
        os.makedirs(os.path.join(ROOT, 'shots', slug), exist_ok=True)
    for i, url in enumerate(urls, 1):
        fn = download(url, os.path.join(ROOT, 'shots', slug, 'issue-%d-%d' % (num, i)))
        if fn:
            shots.append({'file': fn, 'layout': layout, 'issue': num})
    if shots:
        game['shots'] = shots

    report = {'issue': num, 'date': datetime.date.today().isoformat(), 'by': issue['user']['login'],
              'version': s.get('wiz3D version', ''), 'output': s.get('Output mode', ''),
              'display': s.get('Display or glasses', ''), 'result': s.get('Result', ''),
              'notes': s.get('What looks wrong', '')}
    report = {k: v for k, v in report.items() if v not in ('', None)}
    game['reports'] = [r for r in (game.get('reports') or []) if r.get('issue') != num] + [report]

    save_game(game)
    verb = 'Add' if is_new else 'Update'
    with open(os.path.join(ROOT, 'pr-title.txt'), 'w', encoding='utf-8') as f:
        f.write('%s %s: %s (#%d)' % (verb, name, s.get('Result', 'report'), num))
    with open(os.path.join(ROOT, 'pr-body.txt'), 'w', encoding='utf-8') as f:
        f.write('Generated from #%d by @%s.\n\n' % (num, issue['user']['login']))
        f.write('- Game file: `games/%s.yml`%s\n' % (slug, ' (new)' if is_new else ''))
        f.write('- Status: %s\n' % game['status'])
        f.write('- Screenshots added: %d\n\n' % len(urls))
        f.write('Check the notes in the game file before merging. The reporter\'s notes are kept under `reports`, not copied into `notes`.\n\n')
        f.write('Closes #%d\n' % num)
    print('updated games/%s.yml' % slug)


if __name__ == '__main__':
    main()
