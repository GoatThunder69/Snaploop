from flask import Flask, request, jsonify
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

app = Flask(__name__)

# Secure API key from Vercel ENV
ZEPH_KEY = os.getenv("ZEPH_KEY")

# Retry + timeout session
session = requests.Session()

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


@app.route("/api/vehicle", methods=["GET"])
def vehicle():

    number = request.args.get("number")

    if not number:
        return jsonify({
            "success": False,
            "error": "number parameter missing"
        }), 400

    number = number.upper().replace(" ", "")

    api1 = f"https://www.zephrexdigital.site/api?key={ZEPH_KEY}&type=VNUM&term={number}"
    api2 = f"https://vehicle-infox.profilework239.workers.dev/?number={number}"

    data1 = None
    data2 = None

    # API 1
    try:
        r1 = session.get(api1, timeout=15)
        data1 = r1.json()
    except Exception as e:
        data1 = {
            "error": str(e)
        }

    # API 2
    try:
        r2 = session.get(api2, timeout=15)
        data2 = r2.json()
    except Exception as e:
        data2 = {
            "error": str(e)
        }

    return jsonify({
        "success": True,
        "vehicle_number": number,
        "source1": data1,
        "source2": data2
    })


if __name__ == "__main__":
    app.run(debug=True)
