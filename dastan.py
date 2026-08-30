from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
  return """
    <html dir="rtl">
    <head>
        <title>تاقیکردنەوە</title>
        <meta charset="UTF-8">
        <style>
            body { background-color: #0b0f19; color: #ffffff; font-family: sans-serif; text-align: center; padding-top: 100px; }
            h1 { color: #f59e0b; font-size: 32px; }
        </style>
    </head>
    <body>
        <h1>بەخێرنێن بۆ سیستەمی شاهوور!</h1>
    </body>
    </html>
    """


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
