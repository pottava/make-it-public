#!/bin/bash
set -e

apt-get update
apt-get install -y python3 python3-pip
pip3 install Flask

mkdir -p /apps
cat <<EOF > /apps/main.py
from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello!"

@app.route("/api/gemini")
def gemini():
    return "Hey Gemini:)"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
EOF

python3 /apps/main.py &
