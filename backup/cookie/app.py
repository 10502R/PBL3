from flask import Flask, request, jsonify, make_response, render_template,redirect
import redis

app = Flask(__name__)

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

    # 응답과 함께 쿠키 설정 (1일 유지)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)