from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 투표 결과 저장 (간단한 딕셔너리 사용)
votes = {"떡볶이": 0, "치킨": 0}

@app.route('/')
def home():
    return render_template('index.html')

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

@app.route('/assets/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'assets'), filename)

if __name__ == '__main__':
    app.run(debug=True)
