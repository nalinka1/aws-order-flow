from flask import Flask, jsonify

application = Flask(__name__)


@application.route("/")
def hello():
    return jsonify(
        {
            "message": "Hello from Elastic Beanstalk",
            "project": "AWS Refresher - Digital Dreamworks Interview Prep",
        }
    )


@application.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8080)