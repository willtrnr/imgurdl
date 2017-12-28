import os
import re
import requests
import sys
import glob
import shutil
from bs4 import BeautifulSoup

PROTO = 'https'
BASE_URL = PROTO + '://imgur.com'

PREFERVIDEO_RE = re.compile(r"prefer_video:\s*(true|false)")
GIFURL_RE = re.compile(r"gifUrl:\s*'(.+?)'")

def add_proto(url):
    if url.startswith('//'):
        return PROTO + ':' + url
    else:
        return url

def get_post_image(album, post):
    url = BASE_URL + '/r/{}/{}'.format(album, post)
    resp = requests.get(url)
    doc = BeautifulSoup(resp.text, 'lxml')
    el = doc.find(class_='post-image')
    if el:
        img = el.find('img')
        if img:
            return add_proto(img['src'])
        script = el.find('script')
        if script:
            script = script.get_text()
            match = PREFERVIDEO_RE.search(script)
            if match and match.group(1) == 'true':
                source = el.find('source')
                if source:
                    return add_proto(source['src'])
            match = GIFURL_RE.search(script)
            if match:
                return add_proto(match.group(1))

def get_page(album, page):
    url = BASE_URL + '/r/{}/new/page/{}/hit?scrolled'.format(album, page)
    resp = requests.get(url)
    doc = BeautifulSoup(resp.text, 'lxml')
    for post in doc.find_all(class_='post'):
        yield post['id']

def is_downloaded(post, dest):
    if glob.glob(os.path.join(dest, post + '.*')):
        return True
    else:
        return False

def download_file(url, dest):
    try:
        with open(dest, 'wb') as f:
            resp = requests.get(url, stream=True)
            shutil.copyfileobj(resp.raw, f)
    except KeyboardInterrupt:
        os.remove(dest)
        raise

def download_post(album, post, dest):
    url = get_post_image(album, post)
    if url is not None:
        download_file(url, os.path.join(dest, post + '.' + url.split('.')[-1]))
    else:
        print('No URL found for post {}'.format(post))

def download_album(album, dest):
    os.makedirs(dest, exist_ok=True)
    seen = set()
    page = 0
    has_new = True
    while has_new:
        has_new = False
        for post in get_page(album, page):
            if not post in seen:
                has_new = True
                seen.add(post)
                if not is_downloaded(post, dest):
                    print('Downloading {}'.format(post))
                    download_post(album, post, dest)
                else:
                    print('Skipping {}, downloaded'.format(post))
            else:
                print('Skipping {}, seen'.format(post))
        page += 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} <album> [dest]'.format(sys.argv[0]))
    else:
        download_album(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
