"""Build the site into _site/ from games/*.yml.

    python scripts/build_site.py            build _site/
    python scripts/build_site.py --check    validate only (used on pull requests)

If GITHUB_TOKEN is set, milestone progress for the wiz3D repo is fetched
into data/github.json so the API page can show release progress bars.
"""
import json, os, shutil, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gamedata import ROOT, load_games, load_excluded, validate

ORG = 'Stereopticon-Org'
MILESTONE_REPOS = ['wiz3D']


def fetch_milestones():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return None
    out = []
    for repo in MILESTONE_REPOS:
        url = 'https://api.github.com/repos/%s/%s/milestones?state=all&per_page=100' % (ORG, repo)
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'User-Agent': 'stereopticon-site-build'})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                for m in json.load(r):
                    out.append({'repo': repo, 'title': m['title'], 'description': m.get('description') or '',
                                'open': m['open_issues'], 'closed': m['closed_issues'], 'state': m['state'],
                                'due_on': m.get('due_on'), 'url': m['html_url']})
        except Exception as e:  # milestones are optional; never fail the build for them
            print('warning: could not fetch milestones for %s: %s' % (repo, e))
    return out


def main():
    games = load_games()
    excluded = load_excluded()
    problems = [p for g in games for p in validate(g)]
    if problems:
        print('\n'.join(problems))
        sys.exit(1)
    print('%d games, %d excluded, all valid' % (len(games), len(excluded)))
    if '--check' in sys.argv:
        return

    site = os.path.join(ROOT, '_site')
    if os.path.exists(site):
        shutil.rmtree(site)
    os.makedirs(os.path.join(site, 'data'))
    shutil.copy(os.path.join(ROOT, 'index.html'), site)
    if os.path.exists(os.path.join(ROOT, 'CNAME')):
        shutil.copy(os.path.join(ROOT, 'CNAME'), site)
    if os.path.exists(os.path.join(ROOT, 'brand')):
        shutil.copytree(os.path.join(ROOT, 'brand'), os.path.join(site, 'brand'))
    if os.path.exists(os.path.join(ROOT, 'shots')):
        shutil.copytree(os.path.join(ROOT, 'shots'), os.path.join(site, 'shots'))
    with open(os.path.join(site, 'data', 'games.json'), 'w', encoding='utf-8') as f:
        json.dump({'games': games, 'excluded': excluded}, f, ensure_ascii=False, separators=(',', ':'))
    ms = fetch_milestones()
    if ms is not None:
        with open(os.path.join(site, 'data', 'github.json'), 'w', encoding='utf-8') as f:
            json.dump({'milestones': ms}, f, ensure_ascii=False, separators=(',', ':'))
    print('built', site)


if __name__ == '__main__':
    main()
