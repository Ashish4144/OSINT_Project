from flask import Flask, Response, request, send_from_directory
import requests, json, time
from sites import sites_config

app = Flask(__name__)

# User-Agent to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_site_for_user(session, site_name, username):
    """
    Checks a single site for the existence of a username using a combination of checks.
    """
    config = sites_config.get(site_name)
    if not config:
        return False, None

    profile_url = config["url"].format(username)

    try:
        r = session.get(profile_url, timeout=7, headers=headers, allow_redirects=True)
        
        # Priority 1: Check for 404 status code
        if r.status_code == 404:
            return False, profile_url

        # Priority 2: Handle specific sites with tricky behaviors
        if site_name == "Twitter (X)":
            if "This account doesn’t exist" in r.text or r.url != profile_url:
                return False, profile_url
            else:
                return True, profile_url
        
        if site_name == "Reddit":
            if "the page not found" in r.text or "404" in r.text:
                return False, profile_url
            else:
                return True, profile_url

        if site_name == "LinkedIn":
            # LinkedIn often redirects to a login page or shows an "unavailable" page.
            # We check the final URL for known indicators of failure.
            if "page isn't available" in r.text.lower() or "authwall" in r.url:
                return False, profile_url
            else:
                return True, profile_url
        
        if site_name == "Instagram":
            # Instagram returns a 200 OK for a not-found page with specific meta content.
            if "og:description" in r.text and "Sorry, this page isn't available." in r.text:
                return False, profile_url
            else:
                return True, profile_url

        # Priority 3: Fallback to general content check for other sites
        if r.status_code == 200:
            not_found_indicator = config.get("not_found_indicator", "").lower()
            if not_found_indicator and not_found_indicator in r.text.lower():
                return False, profile_url
            else:
                return True, profile_url
        
        # Priority 4: All other cases are considered "not found" to avoid false positives
        return False, profile_url

    except requests.exceptions.RequestException:
        # If any network or request error occurs, assume not found
        return False, profile_url

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/search")
def search():
    username = request.args.get("username", "").strip()
    if not username:
        return Response("data: {\"error\": \"No username provided\"}\n\n",
                        mimetype="text/event-stream")

    def generate():
        with requests.Session() as session:
            for site in sites_config.keys():
                found, profile_url = check_site_for_user(session, site, username)
                result = {"site": site, "url": profile_url, "found": found}
                yield f"data: {json.dumps(result)}\n\n"
                time.sleep(0.2)
        
        yield f"data: {json.dumps({'is_complete': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
