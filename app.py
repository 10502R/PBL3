from flask import Flask, render_template, request, jsonify, make_response, redirect, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from datetime import datetime
import redis
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

#vote table 생성
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    menu = db.Column(db.String(50), unique=True, nullable=False)
    count = db.Column(db.Integer, default=0)

#vote tavle 초기화
def initialize_vote_table():
    with app.app_context():
        if not db.session.query(Vote).first():
            db.session.add_all([
                Vote(menu='chicken', count=0),
                Vote(menu='tteok', count=0)
            ])
            db.session.commit()


# 마감 시간 설정
DEADLINE = datetime(2025, 4, 9, 0, 0, 0)

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
@login_required
def vote():
    user_cookie = request.cookies.get('vote')
    if user_cookie:
        return f"You have already voted. Your choice: {user_cookie}", 400  # 중복 투표 방지

    choice = request.form.get('choice')
    if choice not in votes:
        return "error: Invalid choice", 400

    if current_user.has_voted:
        return "You have already voted!"    

    votes[choice] += 1  # 투표 수 증가

    vote_entry.count += 1
    current_user.has_voted = True
    db.session.commit()

    response = make_response(redirect('/results'))
    response.set_cookie('vote', choice, max_age=60*5)  # 쿠키 설정 (5분)
    return response


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

# Flask-Migrate 초기화
migrate = Migrate(app, db)

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_page"  # 로그인 페이지로 리다이렉트할 URL

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
    return redirect(url_for('/results'))  # 로그아웃 후 페이지로 리다이렉트

def send_mail_to_voters():
    with app.app_context():
        users = User.query.filter_by(has_voted=True).all()

        # 더 많은 표를 받은 메뉴 계산
        winner = max(votes, key=votes.get)
        vote_count = votes[winner]
        total_votes = sum(votes.values())

        if total_votes == 0:
            result_message = "아직 투표 결과가 없습니다."
        else:
            result_message = f"가장 많은 표를 받은 메뉴는 '{winner}'이며, 총 {vote_count}표를 받았습니다!"

        for user in users:
            from_email = 'sophiang201@gmail.com'
            from_password = 'zrnr kzqk pcei upxc'
            try:
                to_email = user.email
                subject = "투표 결과 안내"
                body = (
                    f"{user.email}님, 안녕하세요!\n\n"
                    f"투표에 참여해주셔서 감사합니다.\n\n"
                    f"{result_message}\n\n"
                    "즐거운 하루 보내세요 :)"
                )

                msg = MIMEMultipart()
                msg['From'] = from_email
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(from_email, from_password)
                    server.sendmail(from_email, to_email, msg.as_string())
                print(f"메일이 {to_email}로 발송되었습니다.")

            except Exception as e:
                print(f"메일 발송 실패: {e}") 
                

# 특정 시간에 메일 보내기 (쓰레드 사용)
def send_mail_schedule():
    send_time_str = "2025-04-08 21:22:00"  # 메일을 보내고 싶은 시간
    send_time = datetime.strptime(send_time_str, "%Y-%m-%d %H:%M:%S")
    # send_time = datetime.strptime(DEADLINE)  #투표 마감시간에 발송
    current_time = datetime.now()

    # 설정된 시간이 이미 지났다면, 다음 날로 설정
    if send_time < current_time:
        send_time = send_time.replace(day=current_time.day + 1)

    # 이메일 전송 예약 (스케줄러 사용)
    schedule.every().day.at(send_time.strftime("%H:%M")).do(send_mail_to_voters)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # 데이터베이스 테이블 생성
    
    threading.Thread(target=send_mail_schedule, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)