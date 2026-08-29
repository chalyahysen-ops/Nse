from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
  return """
    <html dir="rtl">
    <head>
        <title>تاقیکردنەوەی سیستەم</title>
        <meta charset="UTF-8">
        <style>
            body { background-color: #0A0F1D; color: #FFFFFF; font-family: sans-serif; text-align: center; padding-top: 50px; }
            h1 { color: #F59E0B; }
            .card { background: #151d30; padding: 20px; border-radius: 10px; display: inline-block; border: 1px solid #334155; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>✨ سیستەمی شاهوور کار دەکات!</h1>
            <p>پەیوەندی لەگەڵ ڕێندەر و ئایپاد بە سەرکەوتوویی سەرکەوت.</p>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=10000)
