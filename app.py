from sqlite3 import IntegrityError
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 시크릿 키 설정???????
# CORS 설정
CORS(app)

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

    # UserSong 모델과 User 모델 간의 관계 정의
    user = db.relationship('User', back_populates='user_songs')


@app.route('/')
def hello_world():
    return 'Hello, World!'



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
        return jsonify({'message': '로그인 성공', 'user': {'user_id': user.user_id, 'email': user.email, 'nickname': user.nickname}})
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






#user 프로필 반환
@app.route('/users/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        # user_id에 해당하는 유저 프로필 데이터 조회
        user = User.query.get(user_id)

        if user is None:
            return jsonify({'error': '유저를 찾을 수 없습니다.'}), 404

        # 프로필 데이터를 JSON 형식으로 변환
        user_data = {
            'user_id': user.user_id,
            'email': user.email,
            'nickname': user.nickname
        }

        return jsonify(user_data)

    except Exception as e:
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





#노래 취향 분석

# GPT-4 API 호출 함수
def generate_song_analysis(songs):
    try:
        # GPT-4를 사용하여 노래 취향 분석 및 추천 생성
        message = [
            {"role": "system", "content": "You are a music analysis and recommendation system."},
            {"role": "user", "content": "내 보관함에 있는 노래 목록:"}
        ]
        for song in songs:
            message.append({"role": "user", "content": f"{song['singer_name']} - {song['song_title']}"})
        message.append({"role": "user", "content": "내가 좋아하는 노래들을 분석해서 내 노래 취향을 세개의 해시태그로 나타내주세요. 세개의 해시태그 외에 다른말은 쓰지 말고, 답변을 다음과 같은 형식으로 써주세요. ex)#발라드, #휴식, #감성적"})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message,
            max_tokens=100
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return str(e)




def find_similar_songs(hashtags):
    try:
        # 세 개의 해시태그를 사용하여 ChatGPT-4에게 명령
        message = [
            {"role": "system", "content": "You are a music recommendation system."},
            {"role": "user", "content": f"세 개의 해시태그로 비슷한 느낌의 노래 두 개를 추천해주세요: {' '.join(hashtags)} 두개의 노래 외에 다른 말은 쓰지 말고, 반드시 다음과 같은 형식으로 써주세요. ex)아이유-밤편지, 폴킴-너를 만나 "}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message,
            max_tokens=100
        )
        return response.choices[0].message["content"].strip()
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
        similar_songs = find_similar_songs(hashtags)

        #similar_songs 두 개로 분할
        songs_list=similar_songs.split(", ")[:2]

        # 가수와 노래 제목을 저장할 리스트
        songs_info = []

        # 각 곡에 대해 가수와 노래 제목을 분리하여 저장
        for song in songs_list:
            parts = song.split("-")
            if len(parts) == 2:
                artist, title = parts[0].strip(), parts[1].strip()
                songs_info.append({'artist': artist, 'title': title})

        # JSON 응답에 가수와 노래 정보를 추가
        response_data = {
            'hashtags': hashtags,
            'similar_songs': songs_info
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
        # 가사 생성을 위한 message
        lyrics_message = [
            {"role": "system", "content": "You are a helpful assistant that generates lyrics and chords."},
            {"role": "user", "content": f"장르: {genre}\n좋아하는 노래: {favorite_song} by {favorite_artist}\n기반하여 새로운 노래의 제목, 가사를 제안해주세요.\n\n"}
        ]
        lyrics_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=lyrics_message,
            max_tokens=150
        )

        # 코드진행 생성을 위한 message
        chord_message = [
            {"role": "system", "content": "You are a helpful assistant that generates lyrics and chords."},
            {"role": "user", "content": f"장르: {genre}\n좋아하는 노래: {favorite_song} by {favorite_artist}\n기반하여 새로운 노래의 코드진행을 제안해주세요.\n\n"}
        ]
        chord_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=chord_message,
            max_tokens=150
        )

        return jsonify({
            'generated_lyrics': lyrics_response.choices[0].message["content"].strip(),
            'generated_chord': chord_response.choices[0].message["content"].strip()
        }), 200
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500



#gpt-c 앨범커버 생성
@app.route('/generate-image', methods=['POST'])
def generate_image():
    data = request.json
    genre = data.get('genre')
    favorite_song = data.get('favorite_song')
    favorite_artist = data.get('favorite_artist')

    if not genre or not favorite_song or not favorite_artist:
        return jsonify({'error': '장르, 좋아하는 노래 제목, 가수를 모두 입력하세요.'}), 400

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
        
        # 이미지 URL에서 이미지 데이터를 가져오기
        response = requests.get(image_url)
        image = BytesIO(response.content)

        return send_file(image, mimetype='image/jpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500



    
    

def letmeknow_genre(song_title, singer_name):
    try:
        # GPT-4를 사용하여 노래의 장르 예측
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
    song_title=data.get('song_title')
    singer_name=data.get('singer_name')
    genre=letmeknow_genre(data.get('song_title'), data.get('singer_name'))

    if not user_id or not song_title or not singer_name:
        return jsonify({'error': '사용자 ID와 노래 ID를 모두 입력하세요.'}), 400

    # UserSong 테이블에 노래를 추가하고 play_count를 증가시킴
    user_song = UserSong.query.filter_by(user_id=user_id, song_title=song_title, singer_name=singer_name).first()
    if user_song:
        user_song.play_count += 1
        user_song.genre=genre
    else:
        new_user_song = UserSong(
            user_id=user_id, 
            song_title=song_title, 
            singer_name=singer_name, 
            play_count=1,
            date=datetime.utcnow(),  # 현재 날짜 및 시간을 저장
            genre=genre  # 장르 정보를 저장)
        )
        db.session.add(new_user_song)
    
    try:
        db.session.commit()
        print(get_total_play_count(user_id))
        return jsonify({'message': '노래 재생 기록이 추가되었습니다.'}), 201
    except Exception as e:
        print(str(e))
        db.session.rollback()
        return jsonify({'error': '노래 재생 기록 추가 실패'}), 500


#user별 총 음악들은 횟수 반환
def get_total_play_count(user_id):
    try:
        # 특정 user_id에 해당하는 사용자의 모든 노래의 play_count 합계를 쿼리로 계산
        total_play_count = db.session.query(db.func.sum(UserSong.play_count)).filter_by(user_id=user_id).scalar()
        return total_play_count
    except Exception as e:
        print(e)
        return None



# 특정 user_id 사용자가 많이 들은 가수
@app.route('/most-listened-singer/<user_id>', methods=['GET'])
def most_listened_singer(user_id):
    try:
        # 특정 사용자가 가장 많이 들은 가수를 조회하는 쿼리
        result = db.session.query(UserSong.singer_name, func.sum(UserSong.play_count).label('total_play_count')) \
            .filter_by(user_id=user_id) \
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
            return jsonify({'message': '사용자가 음악을 듣지 않았거나 데이터가 없습니다.'}), 404

    except Exception as e:
        return jsonify({'error': '서버 오류'}), 500




#월간 장르 통계





if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='80')
