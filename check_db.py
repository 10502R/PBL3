from app import app, db, User

# 애플리케이션 컨텍스트 설정
with app.app_context():
    users = User.query.all()  # 이제 DB 작업을 안전하게 할 수 있습니다.
    for user in users:
        print(user.email, user.has_voted)  # 사용자 이메일 출력

# #전체 사용자 삭제
# with app.app_context():
#     db.session.query(User).delete()  # 모든 사용자 삭제
#     db.session.commit()  # 변경사항 커밋
#     print("All users have been deleted.")


