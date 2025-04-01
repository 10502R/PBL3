from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

# 마감 시간 설정 (4월 8일 00:00)
DEADLINE = datetime(2025, 4, 8, 0, 0, 0)

@app.route('/')
def index():
    return render_template('index.html', deadline=DEADLINE.isoformat())

if __name__ == '__main__':
    app.run(debug=True)
