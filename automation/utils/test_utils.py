import urllib


def verify_url(url):
    if urllib.urlopen(url) == 400:
        return False
    return True
