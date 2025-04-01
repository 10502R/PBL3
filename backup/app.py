#left_time import start
from flask import Flask, render_template, request  #cookie 
from datetime import datetime
#left_time import end

#cookie import start
import redis
import request, jsonify, make_response, redirect
#cookie import end

#email import
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import threading
from datetime import datetime

#voteresult import start
from flask import request, jsonify, send_from_directory
import os
#voteresult import end
app = Flask(__name__)


# -------------------------------------------------- left_time start -------------------------------------------------- #
# 마감 시간 설정 (4월 8일 00:00)
DEADLINE = datetime(2025, 4, 8, 0, 0, 0)

@app.route('/')
def index():
    return render_template('index.html', deadline=DEADLINE.isoformat())
#left_time end

# ---------------------------------------------------cookie--------------------------------------------------------------#
# Redis 연결 설정
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@app.route('/')
def index():
    user_vote = request.cookies.get('vote')  # 쿠키에서 투표 내역 가져오기
    return render_template('index.html', user_vote=user_vote)  # HTML 파일 불러오기

@app.route('/vote', methods=['POST'])
def vote():
    print(request.form)
    data = request.form
    choice = data.get('choice')

    if choice not in ['tteokbokki', 'chicken']:
        return "error : Invalid choice", 400

    # 쿠키 확인
    user_cookie = request.cookies.get('vote')

    if user_cookie:
        return f"You have already voted! your_choice: {choice}", 403

    # 투표 수 증가
    redis_client.incr(choice)

    # 응답과 함께 쿠키 설정 (10분 유지)
    response = make_response(redirect('/'))
    response.set_cookie('vote', choice, max_age=60*10)

    return response

@app.route('/my-vote', methods=['GET'])
def my_vote():
    user_cookie = request.cookies.get('vote')
    print(f"cookie value: {user_cookie}")

    if not user_cookie:
        return "You haven't voted yet!", 404

    return f"your choice: {user_cookie}", 200

# -------------------------------------------------email start----------------------------------------------------------#
# 이메일 전송 함수
def send_email(to_email, subject, body):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    from_email = 'sophiang201@gmail.com'  # 발신자 이메일
    from_password = 'zrnr kzqk pcei upxc'     # 발신자 이메일 앱 비밀번호

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # 보안 연결 시작
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error: {e}")

# 이메일 주소를 JSON 파일에 저장하는 함수
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

# 이메일 전송 예약 함수
def schedule_email_send():
    # 이메일 전송 시간 설정
    send_time_str = "2025-04-05 00:00:00"  # 예: "2025-03-31 09:00:00"
    send_time = datetime.strptime(send_time_str, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()

    # 설정된 시간이 이미 지났다면, 다음 날로 설정
    if send_time < current_time:
        send_time = send_time.replace(day=current_time.day + 1)

    # 이메일 전송 예약 (스케줄러 사용)
    schedule.every().day.at(send_time.strftime("%H:%M")).do(send_scheduled_email)

    while True:
        schedule.run_pending()
        time.sleep(1)

# 실제 이메일 전송 작업
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

# 이메일 입력 페이지
@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form['email']
        save_email_to_json(email)  # 이메일 주소 저장
        # 이메일 저장 후, 메시지와 함께 "투표 페이지로 돌아가기" 버튼을 추가하여 렌더링
        return render_template('login_page.html', email=email, message="로그인되었습니다.")
    
    try:
        with open('emails.json', 'r') as file:
            emails = json.load(file)
    except FileNotFoundError:
        emails = []

    return render_template('login_page.html', emails=emails)


## -------------------------------------------------- voteresult function start -------------------------------------------------- ##

# 투표 결과 저장 (간단한 딕셔너리 사용)
votes = {"떡볶이": 0, "치킨": 0}

@app.route('/vote', methods=['POST'])
def vote():
    data = request.json
    choice = data.get('choice')
    
    if choice in votes:
        votes[choice] += 1
    
    return jsonify({"success": True, "votes": votes})

@app.route('/results', methods=['GET'])
def results():
    total = sum(votes.values())
    if total == 0:
        percentages = {"떡볶이": 50, "치킨": 50}  # 초기 값 (0표일 경우 50:50 표시)
    else:
        percentages = {key: (value / total) * 100 for key, value in votes.items()}
    
    return jsonify(percentages)

# 정적 파일 서빙 (필요할 경우만 사용, 기본적으로 Flask는 static 폴더를 자동으로 서빙함)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)


## -------------------------------------------------- main -------------------------------------------------- ##
if __name__ == '__main__':
    threading.Thread(target=schedule_email_send, daemon=True).start()
    app.run(debug=True)
    