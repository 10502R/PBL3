from flask import Flask, render_template, request, jsonify, make_response, redirect, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from datetime import datetime
import redis
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import threading
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# 마감 시간 설정
DEADLINE = datetime(2025, 4, 8, 0, 0, 0)

# Redis 연결 설정
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# 투표 결과 저장
votes = {"떡볶이": 0, "치킨": 0}

@app.route('/')
def index():
    user_cookie = request.cookies.get('vote')
    return render_template('index.html', deadline=DEADLINE.isoformat(), user_vote=user_cookie)

# 딕셔너리 저장
votes = {"tteokbokki": 0, "chicken": 0}

@app.route('/vote', methods=['POST'])
def vote():
    choice = request.form.get('choice')

    if choice not in votes:  
        return "error: Invalid choice", 400

    #votes[choice] += 1  # 투표 수 증가
    redis_client.incr(choice)

    user_cookie = request.cookies.get('vote')
    if user_cookie:
        return f"You have already voted! : {choice}", 400    

    response = make_response(redirect('/results'))
    response.set_cookie('vote', choice, max_age=60*3)  # 쿠키 설정 (3분)
    return response

    return jsonify({"message": "Vote counted"})


@app.route('/results', methods=['GET'])
def results():
    total = sum(votes.values())
    percentages = {
        "tteokbokki": (votes["tteokbokki"] / total) * 100 if total else 50,
        "chicken": (votes["chicken"] / total) * 100 if total else 50
    }

    return jsonify({
        "tteokbokki": round(percentages["tteokbokki"], 1),
        "tteokbokki_votes": votes["tteokbokki"],
        "chicken": round(percentages["chicken"], 1),
        "chicken_votes": votes["chicken"]
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

# 이메일 전송 함수
def send_email(to_email, subject, body):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    from_email = 'sophiang201@gmail.com'
    from_password = 'zrnr kzqk pcei upxc'

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error: {e}")

# 이메일 저장 함수
def save_email_to_json(email):
    try:
        with open('emails.json', 'r') as file:
            emails = json.load(file)
    except FileNotFoundError:
        emails = []

    if email not in emails:
        emails.append(email)
    
    with open('emails.json', 'w') as file:
        json.dump(emails, file)

# 이메일 예약 전송
def schedule_email_send():
    send_time_str = "2025-04-04 06:53:00"
    send_time = datetime.strptime(send_time_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()
    if send_time < current_time:
        send_time = send_time.replace(day=current_time.day + 1)
    
    schedule.every().day.at(send_time.strftime("%H:%M")).do(send_scheduled_email)
    while True:
        schedule.run_pending()
        time.sleep(1)

def send_scheduled_email():
    subject = "투표 결과입니다."
    body = "~~~~~~~~~~결과~~~~~~~~~~~~~~~~~"
    try:
        with open('emails.json', 'r') as file:
            emails = json.load(file)
        for email in emails:
            send_email(email, subject, body)
        print("Emails sent!")
    except FileNotFoundError:
        print("No emails found in the JSON file.")
# Flask-Migrate 초기화
migrate = Migrate(app, db)

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # 로그인 페이지로 리다이렉트할 URL

# User 모델 정의
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    has_voted = db.Column(db.Boolean, default=False)  # 투표 여부 필드

    def __repr__(self):
        return f"User('{self.email}')"
    
# 로그인 시 유저 로드 함수
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 로그인 페이지
@app.route("/login_page", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:  # 이메일이 데이터베이스에 있으면 로그인 처리
            login_user(user)
            return redirect(url_for('index'))  # 로그인 후 대시보드로 리다이렉트
        else:
            #return "User not found. Please try again."  # 이메일이 없으면 오류 메시지
            error_message="가입된 이메일이 없습니다. 다시 확인해주세요."
            return render_template('login_page.html', error_message=error_message)  # 오류 메시지 전달

    return render_template('login_page.html')  # login.html 렌더링

# 회원가입 페이지
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:  # 이메일이 이미 존재하면 오류 메시지 출력
            return render_template('signup.html', message="이메일이 이미 존재합니다. 로그인 페이지로 이동합니다.")
        
        # 새로운 사용자 추가
        new_user = User(email=email)
        db.session.add(new_user)
        db.session.commit()
        return render_template('signup.html', message="회원가입이 완료되었습니다! 로그인 페이지로 이동합니다.")

    return render_template('signup.html')  # signup.html 렌더링

# 로그아웃 처리
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))  # 로그아웃 후 로그인 페이지로 리다이렉트

if __name__ == '__main__':
    threading.Thread(target=schedule_email_send, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)