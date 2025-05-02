from flask import Flask, jsonify
from google import genai
import os

app = Flask(__name__)


@app.route("/")
def index():
    return "Hi!"


@app.route("/apis/gemini")
def gemini():
    """
    Gemini への問い合わせ
    """
    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location="us-central1",
        http_options=genai.types.HttpOptions(api_version="v1"),
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash-001",
        contents="こんにちは",
    )
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
