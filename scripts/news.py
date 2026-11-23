"""News posts for the site.

Two sources, merged and sorted newest first:

1. posts/*.md written by hand, with front matter:

       ---
       title: Stereo Loom gets a tray menu
       date: 2026-11-23
       summary: One line shown in the news list and the feed.
       project: Stereo Loom        # optional: wiz3D, Stereo Loom or Stereopticon
       ---
       Markdown body. Put images in posts/img/ and write ![alt](img/name.png).

2. GitHub releases of the project repos (RELEASE_REPOS), fetched at build time
   when GITHUB_TOKEN is set. Release notes are used as GitHub renders them, and
   their images are downloaded into the site so they keep working.

Output: data/news.json for the page and feed.xml (Atom) for feed readers.
"""
import datetime, hashlib, html, json, os, re, urllib.request
import yaml

ORG = 'Stereopticon-Org'
SITE_URL = 'https://stereopticon.org/'
RELEASE_REPOS = [('wiz3D', 'wiz3D'), ('StereoLoom', 'Stereo Loom'), ('Stereopticon', 'Stereopticon')]
PROJECTS = ['wiz3D', 'Stereo Loom', 'Stereopticon']
EXT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/gif': 'gif', 'image/webp': 'webp'}


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def _house_style(text):
    # The site uses no em dashes: show them as spaced en dashes (British style).
    return re.sub(r'\s*\u2014\s*', ' \u2013 ', text)


def _summary(html_text, limit=220):
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = html.unescape(re.sub(r'\s+', ' ', text)).strip()
    return text if len(text) <= limit else text[:limit - 1].rsplit(' ', 1)[0] + '…'


def load_posts(root):
    """Read posts/*.md. Returns (posts, problems)."""
    import markdown
    folder = os.path.join(root, 'posts')
    posts, problems = [], []
    if not os.path.isdir(folder):
        return posts, problems
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.md'):
            continue
        raw = open(os.path.join(folder, fn), encoding='utf-8').read()
        m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', raw, re.S)
        if not m:
            problems.append('posts/%s: missing front matter (--- title/date --- block)' % fn)
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        mine = ['posts/%s: missing %s' % (fn, key) for key in ('title', 'date') if not meta.get(key)]
        if meta.get('project') and meta['project'] not in PROJECTS:
            mine.append('posts/%s: project must be one of %s' % (fn, ', '.join(PROJECTS)))
        if mine:
            problems.extend(mine)
            continue
        body = markdown.markdown(m.group(2), extensions=['fenced_code', 'tables', 'sane_lists'])
        body = re.sub(r'(<img[^>]*\bsrc=")img/', r'\1news/img/', body)
        stem = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', fn[:-3])
        body = _house_style(body)
        posts.append({'id': _slug(stem), 'kind': 'post', 'title': _house_style(str(meta['title'])),
                      'date': str(meta['date'])[:10], 'project': meta.get('project') or '',
                      'summary': str(meta.get('summary') or _summary(body)), 'html': body})
    return posts, problems


def load_hidden(root):
    """IDs listed in posts/_hidden.yml are left off the site."""
    path = os.path.join(root, 'posts', '_hidden.yml')
    if not os.path.exists(path):
        return set()
    return {str(x).strip() for x in (yaml.safe_load(open(path, encoding='utf-8')) or [])}


def _get(url, token, accept='application/vnd.github+json'):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token, 'Accept': accept,
                                               'User-Agent': 'stereopticon-site-build'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _localise_images(body_html, img_dir):
    """Download release images into the site and point the HTML at the copies."""
    os.makedirs(img_dir, exist_ok=True)
    def fetch(url):
        key = hashlib.sha1(url.split('?')[0].encode()).hexdigest()[:16]
        for ext in EXT.values():
            if os.path.exists(os.path.join(img_dir, key + '.' + ext)):
                return 'news/img/%s.%s' % (key, ext)
        req = urllib.request.Request(html.unescape(url), headers={'User-Agent': 'stereopticon-site-build'})
        with urllib.request.urlopen(req, timeout=60) as r:
            ext = EXT.get(r.headers.get('Content-Type', '').split(';')[0].strip())
            if not ext:
                return None
            data = r.read()
        with open(os.path.join(img_dir, key + '.' + ext), 'wb') as f:
            f.write(data)
        return 'news/img/%s.%s' % (key, ext)

    def swap_img(m):
        tag = m.group(0)
        src = re.search(r'\bsrc="([^"]+)"', tag)
        if not src or 'githubusercontent.com' not in src.group(1):
            return tag
        try:
            local = fetch(src.group(1))
        except Exception as e:
            print('warning: could not download release image: %s' % e)
            local = None
        if not local:
            return ''
        tag = tag.replace(src.group(1), local)
        return re.sub(r'\s(data-canonical-src|style)="[^"]*"', '', tag)

    out = re.sub(r'<img\b[^>]*>', swap_img, body_html)
    # links that wrapped the images pointed at the expiring URLs; point them at the copies too
    out = re.sub(r'<a\b[^>]*href="https://private-user-images[^"]*"[^>]*>(\s*<img[^>]*src="([^"]+)"[^>]*>\s*)</a>',
                 r'<a href="\2" target="_blank" rel="noopener">\1</a>', out)
    return out


def fetch_releases(site_dir):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return []
    img_dir = os.path.join(site_dir, 'news', 'img')
    posts = []
    for repo, project in RELEASE_REPOS:
        url = 'https://api.github.com/repos/%s/%s/releases?per_page=100' % (ORG, repo)
        try:
            releases = _get(url, token, 'application/vnd.github.html+json')
        except Exception as e:
            print('warning: could not fetch releases for %s: %s' % (repo, e))
            continue
        for r in releases:
            if r.get('draft'):
                continue
            body = _house_style(_localise_images(r.get('body_html') or '', img_dir))
            title = _house_style((r.get('name') or '').strip() or '%s %s' % (project, r['tag_name']))
            posts.append({'id': _slug('%s-%s' % (repo, r['tag_name'])), 'kind': 'release',
                          'title': title, 'date': (r.get('published_at') or r['created_at'])[:10],
                          'project': project, 'tag': r['tag_name'], 'prerelease': bool(r.get('prerelease')),
                          'summary': _summary(body), 'html': body, 'url': r['html_url'],
                          'assets': [{'name': a['name'], 'url': a['browser_download_url'], 'size': a['size']}
                                     for a in r.get('assets') or []]})
    return posts


def write_feed(site_dir, items):
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    e = lambda s: html.escape(str(s), quote=True)
    entries = []
    for it in items[:30]:
        link = SITE_URL + '#post-' + it['id']
        entries.append(
            '<entry><title>%s</title><link href="%s"/><id>%s</id><updated>%sT12:00:00Z</updated>'
            '<summary>%s</summary><content type="html">%s</content></entry>'
            % (e(it['title']), e(link), e(link), e(it['date']), e(it['summary']), e(it['html'])))
    feed = ('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">'
            '<title>Stereopticon news</title><link href="%s"/><link rel="self" href="%sfeed.xml"/>'
            '<id>%s</id><updated>%s</updated>%s</feed>\n' % (SITE_URL, SITE_URL, SITE_URL, now, ''.join(entries)))
    with open(os.path.join(site_dir, 'feed.xml'), 'w', encoding='utf-8') as f:
        f.write(feed)
