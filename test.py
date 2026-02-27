import urllib.request
from urllib.error import HTTPError

def check_url(url):
    try:
        req = urllib.request.Request(url)
        # Prevent following redirects
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                return urllib.response.addinfourl(fp, headers, req.get_full_url(), code)
            http_error_301 = http_error_303 = http_error_307 = http_error_302

        opener = urllib.request.build_opener(NoRedirectHandler())
        response = opener.open(req)
        print(f"URL: {url} - Status: {response.code}")
    except HTTPError as e:
        print(f"URL: {url} - Status: {e.code}")
    except Exception as e:
        print(f"URL: {url} - Error: {e}")

if __name__ == '__main__':
    check_url("http://127.0.0.1:5000/")
    check_url("http://127.0.0.1:5000/about")
    check_url("http://127.0.0.1:5000/view-bookings")
