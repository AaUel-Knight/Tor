#by AaUel_Knight 



import os
import subprocess
from flask import Flask, request, render_template, jsonify, send_file
import requests
from stem import Signal
from stem.control import Controller
from stem import SocketError
import time
import json
from datetime import datetime
from colorama import Fore, Style, init



def logo():
    init(autoreset=True)

    brown = "\033[38;2;102;76;51m"

    print(f"""{brown} _                     _         _   _      _     _  __      _       _     _   
{brown}| |__  _   _          / \   __ _| | | | ___| |   | |/ /_ __ (_) __ _| |__ | |_ 
{brown}| '_ \| | | | ___    / _ \ / _` | | | |/ _ \ |   | ' /| '_ \| |/ _` | '_ \| __|
{brown}| |_) | |_| ||___|  / ___ \ (_| | |_| |  __/ |   | . \| | | | | (_| | | | | |_ 
{brown}|_.__/ \__, |      /_/   \_\__,_|\___/ \___|_|___|_|\_\_| |_|_|\__, |_| |_|\__|
{brown}       |___/                                 |___|             |___/      
{brown}""")

logo()
app = Flask(__name__)

# List of onion URLs
onion_urls = {
    "Ahmia": "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}",
    "Haystak": "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/?q={query}",
#    "Onion Wiki": "http://zqktlwiuavvvqqt4ybvgvi7tyo4hjl5xgfuvpdf6otjiycgwqbym2qad.onion/wiki/index.php?title=Special%3ASearch&search={query}&go=Go",
    "Torch": "http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion/search?query={query}&action=search",
#    "DuckDuckGo": "https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/?q={query}&ia=web",
#    "Deep Search": "http://search7tdrcvri22rieiwgi5g46qnwsesvnubqav2xakhezv4hjzkkad.onion/result.php?search={query}&url=search7tdrcvri22rieiwgi5g46qnwsesvnubqav2xakhezv4hjzkkad.onion"
}

TOR_CONTROL_PASSWORD = os.getenv("TOR_CONTROL_PASSWORD", "your_password")


def check_and_start_tor():
    # Check if Tor is installed
    try:
        subprocess.run(["tor", "--version"], check=True)
    except subprocess.CalledProcessError:
        print("Tor is not installed. Installing Tor...")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "tor"], check=True)

    # Start Tor service if not running
    subprocess.run(["sudo", "systemctl", "restart", "tor"], check=True)
    print("Tor started.")


def get_tor_session():
    session = requests.Session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    session.timeout = 60  # Increase timeout to 60 seconds
    return session



def renew_tor_identity():
    try:
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password=TOR_CONTROL_PASSWORD)
            controller.signal(Signal.NEWNYM)
            time.sleep(10)  # Wait for 10 seconds to ensure the new identity is fully established
    except SocketError as e:
        print(f"Unable to connect to TOR control port: {e}")
        time.sleep(2)
        print("responding...")
    except Exception as e:
        print(f"An error occurred: {e}")


def access_onion_sites(query, selected_url):
    renew_tor_identity()
    session = get_tor_session()
    formatted_url = selected_url.format(query=query)
    results = []
    try:
        response = session.get(formatted_url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        
        search_data = {
            "posted_date_time": str(datetime.now()),
            "searched_date_time": str(datetime.now()),
            "url": formatted_url,
            "thumbnail": "N/A",
            "location_requested": request.remote_addr,
            "location_used_to_search": "Tor Network",
            "device": request.user_agent.string,
            "languages": request.accept_languages.best,
            "query_displayed": query,
            "time_taken_displayed": response.elapsed.total_seconds(),
            "total_results": "N/A",
            "title": "Search Results",
            "link": formatted_url,
            "source": "Tor Search",
            "snippet": "N/A",
            "description": "N/A"
        }
        
        results.append({
            "search_data": search_data,
            "response_text": response.text
        })
        
    except requests.RequestException as e:
        results.append({
            "search_data": {
                "posted_date_time": str(datetime.now()),
                "searched_date_time": str(datetime.now()),
                "url": formatted_url,
                "thumbnail": "N/A",
                "location_requested": request.remote_addr,
                "location_used_to_search": "Tor Network",
                "device": request.user_agent.string,
                "languages": request.accept_languages.best,
                "query_displayed": query,
                "time_taken_displayed": "N/A",
                "total_results": "N/A",
                "title": "Failed to retrieve data",
                "link": formatted_url,
                "source": "Tor Search",
                "snippet": "N/A",
                "description": f"Failed to retrieve data from {formatted_url}: {e}"
            },
            "response_text": ""
        })
    
    return results


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        query = request.form['query']
        selected_url = onion_urls[request.form['url']]
        results = access_onion_sites(query, selected_url)
        
        # Save results to JSON file
        json_filename = f"{query}_results.json"
        with open(json_filename, 'w') as json_file:
            json.dump(results, json_file, indent=4)
        
        aggregated_results = "<br>".join([result['response_text'] for result in results if 'response_text' in result])
        
        return render_template('combined_results.html', query=query, result=aggregated_results, json_file=json_filename)
        
    return render_template('index.html', onion_urls=onion_urls)


@app.route('/json_results/<filename>')
def json_results(filename):
    return send_file(filename, as_attachment=True)


if __name__ == "__main__":
    check_and_start_tor()
    app.run(debug=True)
