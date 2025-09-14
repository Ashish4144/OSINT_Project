from flask import Flask, Response, request, send_from_directory
import requests, json, time
from sites import sites_config

app = Flask(__name__)

# User-Agent to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_site_for_user(session, site_name, username):
    config = sites_config.get(site_name)
    if not config:
        return False, None

    profile_url = config["url"].format(username)
    found = False

    try:
        r = session.get(profile_url, timeout=7, headers=headers, allow_redirects=True)
        
        # Check for authentication redirect as a definitive "not found"
        if config.get("redirect_indicator") and config["redirect_indicator"] in r.url:
            return False, profile_url

        # Explicitly check for a 404 Not Found status code.
        if r.status_code == 404:
            return False, profile_url
        
        # If the status code is 200, check the content for "not found" phrases.
        elif r.status_code == 200:
            if config.get("not_found_indicator"):
                if config["not_found_indicator"].lower() in r.text.lower():
                    found = False
                else:
                    found = True
            else:
                found = True
        
        # For any other status code, assume not found.
        else:
            found = False
        
    except requests.exceptions.RequestException:
        found = False

    return found, profile_url

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
            for site, _ in sites_config.items():
                found, profile_url = check_site_for_user(session, site, username)
                result = {"site": site, "url": profile_url, "found": found}
                yield f"data: {json.dumps(result)}\n\n"
                time.sleep(0.2)
        
        yield f"data: {json.dumps({'is_complete': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, threaded=True)