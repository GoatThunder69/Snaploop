from flask import Flask, request, jsonify
import requests
import re
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from redis import Redis

app = Flask(__name__)

# API KEY
ZEPH_KEY = "ZEPH-ZRJD1U"

# Redis connection
redis = Redis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True
)

# Session + Retry
session = requests.Session()

retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)


# -------- CLEAN @USERNAME --------
def clean_data(data):

    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [clean_data(i) for i in data]

    elif isinstance(data, str):
        return re.sub(r'@\S+', '', data)

    return data


# -------- STATS UPDATE --------
def update_stats(ip):

    redis.incr("total_hits")
    redis.set("last_hit_ip", ip)

    redis.hincrby(
        "ip_hits",
        ip,
        1
    )


# -------- STATS API --------
@app.route("/api/stats", methods=["GET"])
def stats():

    total_hits = int(
        redis.get("total_hits") or 0
    )

    last_hit_ip = (
        redis.get("last_hit_ip") or ""
    )

    ip_hits = (
        redis.hgetall("ip_hits") or {}
    )

    top_ips = dict(
        sorted(
            ip_hits.items(),
            key=lambda x: int(x[1]),
            reverse=True
        )[:10]
    )

    return jsonify({
        "total_hits": total_hits,
        "unique_ips": len(ip_hits),
        "last_hit_ip": last_hit_ip,
        "top_ips": top_ips,
        "all_ip_hits": ip_hits
    })


# -------- VEHICLE API --------
@app.route("/api/vehicle", methods=["GET"])
def vehicle():

    number = request.args.get("number")

    if not number:
        return jsonify({
            "success": False,
            "error": "number parameter missing"
        }), 400

    number = (
        number.upper()
        .replace(" ", "")
    )

    # Real IP
    ip = request.headers.get(
        "x-forwarded-for",
        request.remote_addr
    )

    if "," in ip:
        ip = ip.split(",")[0].strip()

    # Update count
    try:
        update_stats(ip)
    except:
        pass

    api1 = (
        f"https://www.zephrexdigital.site/api?"
        f"key={ZEPH_KEY}"
        f"&type=VNUM"
        f"&term={number}"
    )

    api2 = (
        f"https://vehicle-infox.profilework239.workers.dev/"
        f"?number={number}"
    )

    merged_data = {}

    # API1
    try:
        r1 = session.get(
            api1,
            timeout=15
        )

        d1 = clean_data(
            r1.json()
        )

        if isinstance(d1, dict):

            if (
                "data" in d1
                and isinstance(
                    d1["data"],
                    dict
                )
            ):
                merged_data.update(
                    d1["data"]
                )

            else:
                merged_data.update(d1)

    except:
        pass

    # API2
    try:
        r2 = session.get(
            api2,
            timeout=15
        )

        d2 = clean_data(
            r2.json()
        )

        if isinstance(d2, dict):

            if (
                "data" in d2
                and isinstance(
                    d2["data"],
                    dict
                )
            ):
                merged_data.update(
                    d2["data"]
                )

            else:
                merged_data.update(d2)

    except:
        pass

    return jsonify({
        "success": True,
        "regn_no": number,
        "data": merged_data
    })


@app.route("/")
def home():
    return jsonify({
        "status": "online"
    })


if __name__ == "__main__":
    app.run(debug=True)
