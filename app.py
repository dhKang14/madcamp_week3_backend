import os
from sqlite3 import IntegrityError
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_cors import CORS
import requests
import openai
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from flask import Flask, send_file
import bcrypt
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from flask import Flask, request, jsonify
import matplotlib.pyplot as plt
import io
import base64
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime 
from sqlalchemy import func
from matplotlib import font_manager, rc
from flask_socketio import SocketIO, emit
from sqlalchemy.orm import Session
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time
from flask_cors import CORS
import base64
from PIL import Image
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 시크릿 키 설정???????
# CORS 설정
CORS(app)
socketio = SocketIO(app)
SAVE_DIR = "./uploads/"

# OpenAI API 키 설정 (API 키는 https://platform.openai.com/signup 에서 얻을 수 있음)
openai.api_key = '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'



# MySQL 데이터베이스 연결 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:madmad@localhost/music_database'
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(50), primary_key=True, unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    imageurl = db.Column(db.String(1000)) 
    # User 모델과 UserSong 모델 간의 관계 정의
    user_songs = db.relationship('UserSong', back_populates='user')


class FavoriteSong(db.Model):
    __tablename__ = 'favorite_songs'
    song_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)
    singer_name = db.Column(db.String(255), nullable=False)
    song_title = db.Column(db.String(255), nullable=False)

    def __init__(self, user_id, singer_name, song_title):
        self.user_id = user_id
        self.singer_name = singer_name
        self.song_title = song_title

class UserSong(db.Model):
    __tablename__ = 'user_songs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'), nullable=False)
    song_title = db.Column(db.String(255), nullable=False)
    singer_name = db.Column(db.String(255))
    play_count = db.Column(db.Integer, default=0)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    genre = db.Column(db.String(255))
    year = db.Column(db.Integer, nullable=False)  # 연도 정보를 저장할 컬럼 추가
    month = db.Column(db.Integer, nullable=False)  # 월 정보를 저장할 컬럼 추가
    week = db.Column(db.Integer, nullable=False) 

    # UserSong 모델과 User 모델 간의 관계 정의
    user = db.relationship('User', back_populates='user_songs')


# 모델 정의 - 게시물
class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.user_id'))
    content = db.Column(db.Text, nullable=False)


# 회원가입 API 엔드포인트
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    user_id = data.get('user_id')
    nickname = data.get('nickname')
    password = data.get('password')

    if not email or not user_id or not nickname or not password:
        return jsonify({'error': '모든 필드를 입력하세요.'}), 400

    # 비밀번호 해싱
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # 사용자 생성 및 데이터베이스에 추가
    new_user = User(email=email, user_id=user_id, nickname=nickname, password=hashed_password.decode('utf-8'))
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': '회원가입 성공'}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': '이미 존재하는 이메일 또는 사용자 아이디입니다.'}), 400
    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify({'error': '회원가입 실패'}), 500


# 로그인 API 엔드포인트
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')

    if not user_id or not password:
        return jsonify({'error': '아이디와 비밀번호를 입력하세요.'}), 400

    user = User.query.filter_by(user_id=user_id).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        # 사용자 정보를 세션에 저장
        session['user_id'] = user.user_id
        # 로그인 성공 시 사용자 프로필 반환
        return jsonify({'message': '로그인 성공', 'user': {'user_id': user.user_id, 'email': user.email, 'nickname': user.nickname, 'imageurl':user.imageurl}})
    else:
        # 로그인 실패 시 null 반환
        return jsonify({'error': '로그인 실패'}), 401
    


# 로그아웃
@app.route('/logout', methods=['POST'])
def logout():
    try:
        # 세션에서 사용자 정보 제거
        session.pop('user_id', None)
        flash('로그아웃 되었습니다.', 'success')
        return "로그아웃 되었습니다"
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


#사진등록
@app.route('/upload_image/<user_id>', methods=['PUT'])
def upload_image(user_id):
    try:
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404

        data = request.json
        if 'imageurl' in data:
            user.imageurl = data['imageurl']
            db.session.commit()
            return jsonify({'message': 'Image URL updated successfully'}), 200
        else:
            return jsonify({'message': 'Image URL not provided in request'}), 400
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500



#user 프로필 반환
@app.route('/users', methods=['GET'])
def get_profile():
    try:
        # GET 요청의 쿼리 파라미터에서 user_id를 가져옵니다.
        user_id = request.args.get('user_id')
        # user_id에 해당하는 유저 프로필 데이터 조회
        user = User.query.filter_by(user_id=user_id).first()

        if user is None:
            return jsonify({'error': '유저를 찾을 수 없습니다.'}), 404

        # 프로필 데이터를 JSON 형식으로 변환
        user_data = {
            'user_id': user.user_id,
            'email': user.email,
            'nickname': user.nickname,
            'imageurl':user.imageurl
        }

        return jsonify(user_data)

    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500





# 사용자가 노래를 보관함에 추가하는 라우트
@app.route('/add-to-favorites', methods=['POST'])
def add_to_favorites():
    data = request.json
    user_id = data.get('user_id')
    singer_name = data.get('singer_name')
    song_title = data.get('song_title')

    if not user_id or not singer_name or not song_title:
        return jsonify({'error': '사용자 ID, 가수 이름, 노래 제목을 모두 입력하세요.'}), 400

    try:
        # FavoriteSong 모델을 사용하여 새로운 노래를 보관함에 추가
        new_song = FavoriteSong(user_id=user_id, singer_name=singer_name, song_title=song_title)
        db.session.add(new_song)
        db.session.commit()

        return jsonify({'message': '노래를 보관함에 추가했습니다.'})
    except Exception as e:
        db.session.rollback()



#  보관함의 노래 목록 클라이언트에 반환
        
# favorite_songs 테이블의 모든 레코드를 조회하는 API 엔드포인트
@app.route('/favorite-songs', methods=['GET'])
def get_favorite_songs():
    try:
        # FavoriteSong 모델을 사용하여 favorite_songs 테이블의 모든 레코드를 조회
        favorite_songs = FavoriteSong.query.all()

        # 레코드를 JSON 형식으로 변환하여 반환
        songs_list = []
        for song in favorite_songs:
            song_data = {
                'user_id': song.user_id,
                'singer_name': song.singer_name,
                'song_title': song.song_title
            }
            songs_list.append(song_data)

        return jsonify({'favorite_songs': songs_list})

    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Spotify API 인증 정보 설정
client_id = 'c10281084ac24836b9c6e5748611b9fb'
client_secret = 'da38a160e71a4d8f93beab376d905c3e'
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))


#노래 취향 분석

# GPT-4 API 호출 함수
def generate_song_analysis(songs):
    try:
        # GPT-4를 사용하여 노래 취향 분석 및 추천 생성
        message = [
            {"role": "system", "content": "You are a music analysis model."}
        ]
        for song in songs:
            singer_name = song.singer_name  # 가수 이름 가져오기
            song_title = song.song_title  # 노래 제목 가져오기
            message.append({"role": "user", "content": f"{singer_name} - {song_title}"})
        message.append({"role": "user", "content": "내가 좋아하는 노래들입니다. 내가 좋아하는 노래들을 분석해서 내 노래 취향을 세개의 해시태그로 나타내주세요.\
                         세개의 해시태그 외에 다른말은 절대로 쓰지 말고, 답변을 다음과 같은 형식으로 써주세요. ex)#발라드, #휴식, #감성적"})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message,
            max_tokens=150
        )

        return response.choices[0].message["content"].strip()
    except Exception as e:
        return str(e)




def find_similar_songs(hashtags):
    try:
        # 세 개의 해시태그를 사용하여 ChatGPT-4에게 명령
        message = [
            {"role": "system", "content": "You are a music recommendation system."},
            {"role": "user", "content": f"이 세 개의 해시태그로 비슷한 느낌의 노래 두 개를 찾아주세요: {' '.join(hashtags)} \
             두개의 노래 외에 다른 말은 절대로 쓰지 말고, 반드시 다음과 같은 형식으로 써주세요. ex)아이유-밤편지\n폴킴-너를 만나\
             외국 노래는 반드시 가수이름과 노래 제목을 영어로 써주세요 "}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message,
            max_tokens=100
        )
        similar_songs = response.choices[0].message["content"].strip()

        # Spotify API를 사용하여 song ID를 가져오기
        songs_list = similar_songs.split("\n")[:2]
        songs_info = []

        for song in songs_list:
            parts = song.split("-")
            if len(parts) == 2:
                artist, title = parts[0].strip(), parts[1].strip()
                # Spotify에서 곡을 검색하고 첫 번째 결과의 song ID를 가져옴
                results = sp.search(q=f"artist:{artist} track:{title}", type='track', limit=1)
                if results and results['tracks']['items']:
                    song_id = results['tracks']['items'][0]['id']
                    # 중복된 곡이 아닌 경우에만 추가
                    if not any(info['song_id'] == song_id for info in songs_info):
                        songs_info.append({'artist': artist, 'title': title, 'song_id': song_id})
                    
                    # songs_info에 2곡이 다 추가되면 for 루프 종료
                    if len(songs_info) == 2:
                        break

        # 두 곡이 모두 찾아지지 않으면 재시도
        if len(songs_info) != 2:
            return find_similar_songs(hashtags)
        else:
            return songs_info
    except Exception as e:
        return str(e)

    


# 사용자의 노래 취향을 분석하고 추천을 생성하는 API 엔드포인트
@app.route('/analyze-recommend-songs', methods=['POST'])
def analyze_recommend_songs():
    data = request.json
    user_id = data.get('user_id')
    favorite_songs = FavoriteSong.query.filter_by(user_id=user_id).all()  # 사용자가 보관한 노래 목록

    

    try:
        # GPT-4를 사용하여 노래 취향을 분석하고 해시태그 생성
        song_analysis = generate_song_analysis(favorite_songs)

        # 해시태그를 세 개로 분할
        hashtags = song_analysis.split(", ")[:3]

        # 비슷한 느낌의 노래를 찾는 로직을 통해 추천 노래 생성
        similar_songs=find_similar_songs(hashtags)

        # JSON 응답에 가수와 노래 정보를 추가
        response_data = {
            'hashtags': hashtags,
            'similar_songs': similar_songs
        }
        return jsonify(response_data)  # 해시태그, 가수와 노래 제목 정보를 함께 반환
    except Exception as e:
        return jsonify({'error': str(e)}), 500







# gpt-b 작사작곡
@app.route('/generate-lyrics-and-chord', methods=['POST'])
def generate_lyrics_and_chord():
    data = request.json
    genre = data.get('genre')
    favorite_song = data.get('favorite_song')
    favorite_artist = data.get('favorite_artist')

    if not genre or not favorite_song or not favorite_artist:
        return jsonify({'error': '장르, 좋아하는 노래 제목, 가수를 모두 입력하세요.'}), 400

    try:
        # 제목 생성을 위한 message
        title_message = [
            {"role": "system", "content": "You are a helpful assistant that generates lyrics and chords."},
            {"role": "user", "content": f"장르: {genre}\n\
             좋아하는 노래: {favorite_song} by {favorite_artist}\n\
            기반하여 새로운 노래의 제목을 제안해주세요. 다른 그 어떤 말도 없이 제목만 써주세요. 앞뒤 설명도 하지 마세요.\n\n"}
        ]
        
        # 가사 생성을 위한 message
        lyrics_message = [
            {"role": "system", "content": "You are a helpful assistant that generates lyrics and chords."},
            {"role": "user", "content": f"장르: {genre}\n\
             좋아하는 노래: {favorite_song} by {favorite_artist}\n\
            기반하여 새로운 노래의 가사를 제안해주세요. 다른 그 어떤 말도 없이, 코드없이, 가사만 주세요. 앞뒤 설명도 하지 마세요.\n\n"}
        ]
        # 코드진행 생성을 위한 message
        chord_message = [
            {"role": "system", "content": "You are a helpful assistant that generates lyrics and chords."},
            {"role": "user", "content": f"장르: {genre}\n\
             좋아하는 노래: {favorite_song} by {favorite_artist}\n\
            기반하여 새로운 노래의 코드진행을 제안해주세요.가사 없이 코드만 주세요. 다른 그 어떤 말도 없이, 코드만 주세요. 앞뒤 설명도 하지 마세요.\n\n"}
        ]
        title_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=title_message,
            max_tokens=150
        )
        lyrics_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=lyrics_message,
            max_tokens=150
        )
        
        chord_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chord_message,
            max_tokens=150
        )

        return jsonify({
            'generated_title' : title_response.choices[0].message["content"].strip(),
            'generated_lyrics': lyrics_response.choices[0].message["content"].strip(),
            'generated_chord': chord_response.choices[0].message["content"].strip()
        }), 200
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500



#gpt-c 앨범커버 생성
# 이미지 URL 생성 함수
def generate_image_url(genre, favorite_song, favorite_artist):
    try:
        prompt = (f"장르: {genre}\n"
                  f"좋아하는 노래: {favorite_song} by {favorite_artist}\n"
                  f"기반하여 이미지를 생성해주세요.\n\n")
        response = openai.Image.create(
            model="dall-e-3",  # 모델을 'dall-e-3'로 설정
            prompt=prompt,
            n=1  # 생성할 이미지 수
        )
        image_url = response['data'][0]['url']
        return image_url
    except Exception as e:
        return str(e)

# 이미지 생성 API 엔드포인트
@app.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.json
    genre = data.get('genre')
    favorite_song = data.get('favorite_song')
    favorite_artist = data.get('favorite_artist')

    if not genre or not favorite_song or not favorite_artist:
        return jsonify({'error': '장르, 좋아하는 노래 제목, 가수를 모두 입력하세요.'}), 400

    try:
        image_url = generate_image_url(genre, favorite_song, favorite_artist)
        return jsonify({'image_url': image_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500




    
    

def letmeknow_genre(song_title, singer_name):
    try:
        # gpt-3.5를 사용하여 노래의 장르 예측
        message = (
            "'발라드', 'k-pop', '댄스', '랩/힙합', 'R&B/Soul', '인디음악', '록/메탈', '트로트', '그 외' 중에서 한 가지를 꼽자면 "
            f"'{singer_name}'의 '{song_title}'은 어떤 장르인지 반드시 한마디(장르이름)로 답변해줘. 절대로 장르 외에 다른말을 붙이면 안돼. ex)발라드"
            )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides information about songs."
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            max_tokens=50,  # 원하는 답변 길이로 조정 가능
            n=1,  # 답변을 1개 받을 것임
            stop=None,  # 중단할 단어를 지정할 수 있지만 이 경우에는 필요 없음
            temperature=0.7  # 낮은 값일수록 보수적인 답변, 높은 값일수록 다양한 답변
        )
        
        # API 응답에서 답변 텍스트 추출
        genre_guess = response.choices[0].message["content"].strip()
        print(genre_guess)
        return genre_guess
    except Exception as e:
        print(e)
        return str(e)


#사용자가 들은 노래 저장
@app.route('/play-song', methods=['POST'])
def play_song():
    data = request.json
    user_id = data.get('user_id')
    song_title = data.get('song_title')
    singer_name = data.get('singer_name')
    genre = letmeknow_genre(data.get('song_title'), data.get('singer_name'))
    
    if not user_id or not song_title or not singer_name:
        return jsonify({'error': '사용자 ID와 노래 ID를 모두 입력하세요.'}), 400

    # 현재 날짜 및 시간 정보 가져오기
    current_date = datetime.utcnow()

    # 현재 년도, 월, 주(Week) 정보 가져오기
    current_year = current_date.year
    current_month = current_date.month
    current_week = current_date.isocalendar()[1]  # ISO 주(Week) 정보

    # UserSong 테이블에 기존 레코드 조회
    user_song = UserSong.query.filter_by(
        user_id=user_id, 
        song_title=song_title, 
        singer_name=singer_name, 
        year=current_year,
        month=current_month,
        week=current_week
    ).first()

    if user_song:
        # 이미 같은 년도, 월, 주에 해당 노래를 들었다면 play_count만 증가
        user_song.play_count += 1
        user_song.genre = genre
    else:
        # 새로운 주(Week)에 해당 노래를 듣는 경우, 새로운 레코드 추가
        new_user_song = UserSong(
            user_id=user_id, 
            song_title=song_title, 
            singer_name=singer_name, 
            play_count=1,
            year=current_year,
            month=current_month,
            week=current_week,
            date=current_date,
            genre=genre
        )
        db.session.add(new_user_song)
    
    try:
        db.session.commit()
        return jsonify({'message': '노래 재생 기록이 추가되었습니다.'}), 201
    except Exception as e:
        print(str(e))
        db.session.rollback()
        return jsonify({'error': '노래 재생 기록 추가 실패'}), 500



#월별로 볼수있게->month 선택할 수 있게 
    
#월간로그-특정 user_id 사용자가 총 음악들은 횟수 반환
@app.route('/total-play-count', methods=['GET'])
def get_total_play_count():
    try:
        user_id = request.args.get('user_id')
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month
        # 특정 user_id에 해당하는 사용자의 모든 노래의 play_count 합계를 쿼리로 계산
        total_play_count = db.session.query(db.func.sum(UserSong.play_count)).filter_by(user_id=user_id, year=current_year, month=current_month).scalar()
        return jsonify({'total_play_count': total_play_count}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'error': '총 음악 횟수를 가져오는 동안 오류가 발생했습니다.'}), 500




#월간로그-특정 user_id 사용자가 많이 들은 가수
@app.route('/most-listened-singer', methods=['GET'])
def most_listened_singer():
    try:
        user_id = request.args.get('user_id')
        # 현재 연도와 월을 가져옵니다.
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        # 특정 사용자가 현재 월에 가장 많이 들은 가수를 조회하는 쿼리
        result = db.session.query(UserSong.singer_name, func.sum(UserSong.play_count).label('total_play_count')) \
            .filter_by(user_id=user_id, year=current_year, month=current_month) \
            .group_by(UserSong.singer_name) \
            .order_by(func.sum(UserSong.play_count).desc()) \
            .first()

        if result:
            singer_name, total_play_count = result
            response = {
                'user_id': user_id,
                'most_listened_singer': singer_name,
                'total_play_count': total_play_count
            }
            return jsonify(response)
        else:
            return jsonify({'message': '사용자가 이번 달에 음악을 듣지 않았거나 데이터가 없습니다.'}), 404

    except Exception as e:
        return jsonify({'error': '서버 오류'}), 500


#월간로그-특정 user_id 사용자가 많이 들은 장르
@app.route('/most-listened-genre', methods=['GET'])
def most_listened_genre():
    try:
        user_id = request.args.get('user_id')
        # 현재 연도와 월을 가져옵니다.
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        # 특정 사용자가 이번 달에 가장 많이 들은 장르를 조회하는 쿼리
        result = db.session.query(UserSong.genre, func.sum(UserSong.play_count).label('total_play_count')) \
            .filter_by(user_id=user_id, year=current_year, month=current_month) \
            .group_by(UserSong.genre) \
            .order_by(func.sum(UserSong.play_count).desc()) \
            .first()

        if result:
            most_listened_genre, total_play_count = result
            response = {
                'user_id': user_id,
                'most_listened_genre': most_listened_genre,
                'total_play_count': total_play_count
            }
            return jsonify(response)
        else:
            return jsonify({'message': '사용자가 이번 달에 음악을 듣지 않았거나 데이터가 없습니다.'}), 404

    except Exception as e:
        return jsonify({'error': '서버 오류'}), 500


#월간로그-특정 user_id 사용자의 최다감상곡
# 이번 달 가장 많이 들은 최다 감상 곡 조회 API 엔드포인트
@app.route('/most-listened-song', methods=['GET'])
def most_listened_song():
    try:
        user_id = request.args.get('user_id')
        # 현재 연도와 월을 가져옵니다.
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        # 특정 사용자가 이번 달에 가장 많이 들은 곡을 조회하는 쿼리
        result = db.session.query(UserSong.singer_name, UserSong.song_title, func.sum(UserSong.play_count).label('total_play_count')) \
            .filter_by(user_id=user_id, year=current_year, month=current_month) \
            .group_by(UserSong.singer_name, UserSong.song_title) \
            .order_by(func.sum(UserSong.play_count).desc()) \
            .first()

        if result:
            singer_name, song_title, total_play_count = result
            response = {
                'user_id': user_id,
                'most_listened_song': f'{singer_name} - {song_title}',
                'total_play_count': total_play_count
            }
            return jsonify(response)
        else:
            return jsonify({'message': '사용자가 이번 달에 음악을 듣지 않았거나 데이터가 없습니다.'}), 404

    except Exception as e:
        return jsonify({'error': '서버 오류'}), 500




#월간 장르 통계
@app.route('/month-genre',methods=['POST'])
def month_genre():
    try:
        data = request.json
        user_id = data.get('user_id')
        current_year = datetime.utcnow().year
        current_month = datetime.utcnow().month

        user_songs = UserSong.query.filter_by(
            user_id=user_id,
            year=current_year,
            month=current_month
        ).all()

        if not user_songs:
            return jsonify({'error': '이번 달에 들은 노래가 없습니다.'}), 404

        genre_counts = {}
        total_play_count = 0

        for song in user_songs:
            total_play_count += song.play_count
            if song.genre:
                if song.genre in genre_counts:
                    genre_counts[song.genre] += song.play_count
                else:
                    genre_counts[song.genre] = song.play_count

        # 각 장르별 비율을 계산하고 스케일링하여 합을 100%로 조절
        total_scaled_ratio = 0
        scaled_genre_ratio = {}
        for genre, count in genre_counts.items():
            ratio = (count / total_play_count) * 100
            scaled_ratio = round(ratio, 2)  # 원하는 소수점 자릿수로 반올림
            scaled_genre_ratio[genre] = scaled_ratio
            total_scaled_ratio += scaled_ratio

        # 합을 다시 계산하여 100%인지 확인하고 조절
        if total_scaled_ratio != 100:
            scaling_factor = 100 / total_scaled_ratio
            for genre, ratio in scaled_genre_ratio.items():
                scaled_genre_ratio[genre] = round(ratio * scaling_factor, 2)
        return jsonify({'genre_ratio': scaled_genre_ratio}), 200
    except Exception as e:
        print(str(e))
        return {'error': '장르 비율을 가져오는 동안 오류가 발생했습니다.'}




#주간 장르 통계
@app.route('/week-genre',methods=['POST'])
# 이번 달에 해당하는 사용자의 노래 재생 기록 가져오기
def week_genre():
    try:
        data = request.json
        user_id = data.get('user_id')
        # 현재 날짜 및 시간 정보 가져오기
        current_date = datetime.utcnow()

    # 현재 년도, 월, 주(Week) 정보 가져오기
        current_year = current_date.year
        current_month = current_date.month
        current_week = current_date.isocalendar()[1]  # ISO 주(Week) 정보

        user_songs = UserSong.query.filter_by(
            user_id=user_id,
            year=current_year,
            month=current_month,
            week=current_week
        ).all()

        if not user_songs:
            return jsonify({'error': '이번 달에 들은 노래가 없습니다.'}), 404

        genre_counts = {}
        total_play_count = 0

        for song in user_songs:
            total_play_count += song.play_count
            if song.genre:
                if song.genre in genre_counts:
                    genre_counts[song.genre] += song.play_count
                else:
                    genre_counts[song.genre] = song.play_count

        # 각 장르별 비율을 계산하고 스케일링하여 합을 100%로 조절
        total_scaled_ratio = 0
        scaled_genre_ratio = {}
        for genre, count in genre_counts.items():
            ratio = (count / total_play_count) * 100
            scaled_ratio = round(ratio, 2)  # 원하는 소수점 자릿수로 반올림
            scaled_genre_ratio[genre] = scaled_ratio
            total_scaled_ratio += scaled_ratio

        # 합을 다시 계산하여 100%인지 확인하고 조절
        if total_scaled_ratio != 100:
            scaling_factor = 100 / total_scaled_ratio
            for genre, ratio in scaled_genre_ratio.items():
                scaled_genre_ratio[genre] = round(ratio * scaling_factor, 2)
        return jsonify({'genre_ratio': scaled_genre_ratio}), 200
    except Exception as e:
        print(str(e))
        return {'error': '장르 비율을 가져오는 동안 오류가 발생했습니다.'}



#게시판
@app.route('/add_post', methods=['POST'])
def add_post():
    data = request.get_json()
    user_id=data.get('user_id')
    content = data.get('content')
    if content:
        post = Post(user_id=user_id, content=content)
        db.session.add(post)
        db.session.commit()
        return jsonify({'message': '게시글이 추가되었습니다.', 'post_id': post.id}), 201
    else:
        return jsonify({'error': '제목과 내용을 모두 입력하세요.'}), 400


@app.route('/delete_post', methods=['DELETE'])
def delete_post():
    data = request.get_json()
    post_id = data.get('post_id')
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': '게시글을 찾을 수 없습니다.'}), 404
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': '게시글이 삭제되었습니다.'})


@app.route('/get_posts', methods=['GET'])
def get_posts():
    posts = Post.query.all()
    post_list = [{'post_id':post.id, 'user_id':post.user_id, 'content': post.content} for post in posts]
    return jsonify({'posts': post_list})




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='80')
