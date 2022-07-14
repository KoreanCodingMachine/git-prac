from pymongo import MongoClient
import jwt
import datetime
import hashlib
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

client = MongoClient(
    'mongodb+srv://test:sparta@cluster0.rrtmj.mongodb.net/?retryWrites=true&w=majority',)
db = client.dbsparta


# 홈 화면
# 로그인 되면 토큰을 보내주고
# 로그인이 되지 않으면 로그인을 해야한다고 알려줌

# @app.route('/')
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('index.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 로그인 페이지 라우터
@app.route('/login')
def login():
    # msg = request.args.get("msg")
    return render_template('login.html')


@app.route('/user/<username>')
def user(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 내 프로필이면 True, 다른 사람 프로필 페이지면 False
        status = (username == payload["id"])
        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template('user.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# 회원가입 api(토큰을 이용해서)
@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one(
        {'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# 회원정보를 db에 저장하는 api
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(
        password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
        "profile_name": username_receive,  # 프로필 이름 기본값은 아이디
        "profile_pic": "",  # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지
        "profile_info": ""  # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


# 회원가입 중복확인 api
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


@app.route("/gameData", methods=["POST"])
def movie_post():
    url_receive = request.form['url_give']
    star_receive = request.form['star_give']
    title_receive = request.form['title_give']

    doc = {
        'url': url_receive,
        'star': star_receive,
        'title': title_receive
    }

    db.movies.insert_one(doc)

    return jsonify({'msg': 'POST 연결 완료!'})


@app.route("/gameData", methods=["GET"])
def movie_get():
    movie_list = list(db.movies.find({}, {'_id': False}))
    return jsonify({'movies': movie_list})


# 화면 뒤로가기했을때 로그임 풀림 방지
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.route("/game", methods=["GET"])
def game_get():
    # 게임 카드 메인페이지에 전송
    game_list = list(db.games.find({}, {'_id': False}))
    return jsonify({'games': game_list})


# 게임 타이틀을 통해 db에서 게임을 찾아 detail 페이지에 전송
@app.route('/detail/<gamename>')
def detail(gamename):
    game = db.movies.find_one({'title': gamename}, {'_id': False})
    comment_list = list(db.comments.find({}, {'_id': False}))
    print(game)
    return render_template("detail.html", game=game, name=gamename, comment_list=comment_list)

# api를 하나 더 만들어서 index쪽에서 get요청을 하면 서버에서 movies db를 조회해서 game 데이터 뽑아내려주는 식으로 해보자

# @app.route('/')
# def main(gamename):
#     game = db.games.find_one({'title': gamename})
#     comment_list = list(db.comments.find({}, {'_id': False}))
#     return render_template("index.html", game=game, name=gamename, comment_list=comment_list)


@app.route("/api/save_comments", methods=["POST"])
def save_comments():
    star_receive = request.form['star_give']
    comment_receive = request.form['comment_give']
    name_receive = request.form['name_give']

    doc = {'star': star_receive, 'comment': comment_receive, 'name': name_receive}
    db.comments.insert_one(doc)

    return jsonify({'msg': '작성 완료!'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
