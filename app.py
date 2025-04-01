from flask import Flask, render_template, request, jsonify, make_response, redirect, send_from_directory
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

# 마감 시간 설정
DEADLINE = datetime(2025, 4, 8, 0, 0, 0)

# Redis 연결 설정
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 투표 결과 저장
votes = {"떡볶이": 0, "치킨": 0}

@app.route('/')
def index():
    user_vote = request.cookies.get('vote')
    return render_template('index.html', deadline=DEADLINE.isoformat(), user_vote=user_vote)

@app.route('/vote', methods=['POST'])
def vote():
    data = request.form
    choice = data.get('choice')

    if choice not in ['tteokbokki', 'chicken']:
        return "error : Invalid choice", 400

    user_cookie = request.cookies.get('vote')
    if user_cookie:
        return f"You have already voted! your_choice: {choice}", 403

    redis_client.incr(choice)
    votes[choice] += 1
    
    response = make_response(redirect('/'))
    response.set_cookie('vote', choice, max_age=60*10)
    return response

@app.route('/my-vote', methods=['GET'])
def my_vote():
    user_cookie = request.cookies.get('vote')
    if not user_cookie:
        return "You haven't voted yet!", 404
    return f"your choice: {user_cookie}", 200

@app.route('/results', methods=['GET'])
def results():
    total = sum(votes.values())
    percentages = {key: (value / total) * 100 for key, value in votes.items()} if total else {"떡볶이": 50, "치킨": 50}
    return jsonify(percentages)

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
    send_time_str = "2025-04-05 00:00:00"
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

@app.route('/login_page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form['email']
        save_email_to_json(email)
        return render_template('login_page.html', email=email, message="로그인되었습니다.")
    
    try:
        with open('emails.json', 'r') as file:
            emails = json.load(file)
    except FileNotFoundError:
        emails = []
    
    return render_template('login_page.html', emails=emails)

if __name__ == '__main__':
    threading.Thread(target=schedule_email_send, daemon=True).start()
    app.run(debug=True)