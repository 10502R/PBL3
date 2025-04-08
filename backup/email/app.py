import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request
import schedule
import time
import threading
from datetime import datetime

app = Flask(__name__)

# 메일 보내는 함수
def send_mail_to_voters():
    with app.app_context():  # 애플리케이션 컨텍스트를 명시적으로 생성
        users = User.query.filter_by(has_voted=True).all()  # 투표한 사용자들만 가져옴
        # users = User.query.all() # 메일 보내지는지 확인
        for user in users:
            from_email = 'sophiang201@gmail.com'  # 발신자 이메일
            from_password = 'zrnr kzqk pcei upxc'  # 발신자 이메일 비밀번호
            try:
                # 메일 설정
                to_email = user.email  # 수신자 이메일 주소
                

                # 메일 제목과 내용
                subject = "투표 결과 안내"
                body = f"{user.email}님, 투표 결과가 준비되었습니다!\n" 

                # 메일 MIME 설정
                msg = MIMEMultipart()
                msg['From'] = from_email
                msg['To'] = to_email
                msg['Subject'] = subject

                # 본문 설정
                msg.attach(MIMEText(body, 'plain'))

                # 이메일 서버 연결 및 보내기
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()  # 보안 연결 시작
                    server.login(from_email, from_password)
                    server.sendmail(from_email, to_email, msg.as_string())
                print(f"메일이 {to_email}로 발송되었습니다.")

            except Exception as e:
                print(f"메일 발송 실패: {e}")     

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
    # 이메일 전송 시간 설정정
    send_time_str = "2025-03-31 22:00:00"  # 예: "2025-03-31 09:00:00"
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

# 첫 번째 페이지 (투표 페이지)
@app.route('/vote_page')
def vote_page():
    return render_template('vote_page.html')

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

if __name__ == '__main__':
    # 이메일 전송 예약을 위한 스레드 시작
    threading.Thread(target=schedule_email_send, daemon=True).start()

    app.run(debug=True)
