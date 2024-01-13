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


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 시크릿 키 설정???????


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


class FavoriteSong(db.Model):
    __tablename__ = 'favorite_songs'
    song_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    singer_name = db.Column(db.String(255), nullable=False)
    song_title = db.Column(db.String(255), nullable=False)

    def __init__(self, user_id, singer_name, song_title):
        self.user_id = user_id
        self.singer_name = singer_name
        self.song_title = song_title

class UserSong(db.Model):
    __tablename__ = 'user_songs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.user_id'), nullable=False)
    song_title = db.Column(db.String(255), nullable=False)
    singer_name = db.Column(db.String(255))
    play_count = db.Column(db.Integer, default=0)

    # UserSong 모델과 User 및 Song 모델 간의 관계 정의
    user = relationship('User', back_populates='user_songs')




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
        # 로그인 성공 시 사용자 프로필 반환
        return jsonify({'user_id': user.user_id, 'email': user.email, 'nickname': user.nickname})
    else:
        # 로그인 실패 시 null 반환
        return jsonify({'error': '로그인 실패'}), 401
    

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


#로그아웃
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        # POST 요청을 처리하는 코드
        session.pop('user_id', None)
        flash('로그아웃 되었습니다.', 'success')
        return redirect(url_for('login'))
    else:
        # GET 요청을 처리하는 코드
        # (예: 로그아웃 화면 표시)
        return render_template('logout.html')







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
            'nickname': user.nickname,
            'password': user.password,
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
    # GPT-4를 사용하여 노래 취향 분석 및 추천 생성
    prompt = "내 보관함에 있는 노래 목록:\n"
    for song in songs:
        prompt += f"{song['singer_name']} - {song['song_title']}\n"
    prompt += "\n내 노래 취향을 해시태그로 나타내주세요."

    response = openai.ChatCompletion.create(
        engine="gpt-4",
        prompt=prompt,
        max_tokens=100
    )
    return response.choices[0].text.strip()


# 비슷한 느낌의 노래를 찾는 로직 (단순 예시)
def find_similar_songs(hashtags):
    # 세 개의 해시태그를 사용하여 ChatGPT-4에게 명령
    prompt = "세 개의 해시태그로 비슷한 느낌의 노래 두 개를 추천해주세요:\n"
    for hashtag in hashtags:
        prompt += f"#{hashtag} "

    response = openai.ChatCompletion.create(
        engine="gpt-4",
        prompt=prompt,
        max_tokens=100
    )
    return response.choices[0].text.strip()


# 사용자의 노래 취향을 분석하고 추천을 생성하는 API 엔드포인트
@app.route('/analyze-recommend-songs', methods=['POST'])
def analyze_recommend_songs():
    data = request.json
    user_id = data.get('user_id')
    favorite_songs = data.get('favorite_songs')  # 사용자가 보관한 노래 목록

    if not user_id or not favorite_songs:
        return jsonify({'error': '사용자 ID와 노래 목록을 모두 입력하세요.'}), 400

    try:
        # GPT-4를 사용하여 노래 취향을 분석하고 해시태그 생성
        song_analysis = generate_song_analysis(favorite_songs)

        # 해시태그를 세 개로 분할
        hashtags = song_analysis.split()[:3]

        # 비슷한 느낌의 노래를 찾는 로직을 통해 추천 노래 생성
        similar_songs = find_similar_songs(hashtags)

        #similar_songs 두 개로 분할
        similar_songs=similar_songs.split()[:2]


        return jsonify({'hashtags': hashtags, 'similar_songs': similar_songs})  # 해시태그, 비슷한 느낌의 노래 목록 반환
    except Exception as e:
        return jsonify({'error': str(e)}), 500







#gpt-b 작사작곡
@app.route('/generate-lyrics-and-chord', methods=['POST'])
def generate_lyrics_and_chord():
    data = request.json
    genre = data.get('genre')
    favorite_song = data.get('favorite_song')
    favorite_artist = data.get('favorite_artist')

    if not genre or not favorite_song or not favorite_artist:
        return jsonify({'error': '장르, 좋아하는 노래 제목, 가수를 모두 입력하세요.'}), 400

    try:
        # 가사 생성을 위한 프롬프트
        lyrics_prompt = (f"장르: {genre}\n"
                         f"좋아하는 노래: {favorite_song} by {favorite_artist}\n"
                         f"기반하여 새로운 노래의 제목, 가사를 제안해주세요.\n\n")
        lyrics_response = openai.ChatCompletion.create(
            engine="gpt-4",
            prompt=lyrics_prompt,
            max_tokens=150
        )

        # 코드진행 생성을 위한 프롬프트
        chord_prompt = (f"장르: {genre}\n"
                        f"좋아하는 노래: {favorite_song} by {favorite_artist}\n"
                        f"기반하여 새로운 노래의 코드진행을 제안해주세요.\n\n")
        chord_response = openai.ChatCompletion.create(
            engine="gpt-4",
            prompt=chord_prompt,
            max_tokens=150
        )

        return jsonify({
            'generated_lyrics': lyrics_response.choices[0].text.strip(),
            'generated_chord': chord_response.choices[0].text.strip()
        })
    except Exception as e:
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





#사용자가 들은 노래 저장
@app.route('/play-song', methods=['POST'])
def play_song():
    data = request.json
    user_id = data.get('user_id')
    song_title=data.get('song_title')
    singer_name=data.get('singer_name')

    if not user_id or not song_title or not singer_name:
        return jsonify({'error': '사용자 ID와 노래 ID를 모두 입력하세요.'}), 400

    # UserSong 테이블에 노래를 추가하고 play_count를 증가시킴
    user_song = UserSong.query.filter_by(user_id=user_id, song_title=song_title, singer_name=singer_name).first()
    if user_song:
        user_song.play_count += 1
    else:
        new_user_song = UserSong(user_id=user_id, song_title=song_title, singer_name=singer_name, play_count=1)
        db.session.add(new_user_song)
    
    try:
        db.session.commit()
        return jsonify({'message': '노래 재생 기록이 추가되었습니다.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '노래 재생 기록 추가 실패'}), 500



"""
#노래 통계
    # 사용자가 들은 노래의 장르 정보를 기반으로 월별 장르 비율 계산하는 API 엔드포인트
@app.route('/user-genre-stats/monthly', methods=['POST'])
def calculate_monthly_genre_stats():
    try:
        data = request.json
        user_id = data.get('user_id')
        songs = data.get('songs')  # 사용자가 들은 노래 정보(노래 제목, 가수, 장르 등)

        # 월별 장르 비율 계산 로직 작성
        # songs 리스트를 기반으로 월별 장르 비율 계산

        # 계산된 결과를 GPT-4 API로 전달하여 파이 차트 생성
        gpt4_response = gpt4_api.generate_genre_chart(monthly_genre_stats)

        return jsonify({'chart_url': gpt4_response['chart_url']})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 사용자가 들은 노래의 장르 정보를 기반으로 주별 장르 비율 계산하는 API 엔드포인트
@app.route('/user-genre-stats/weekly', methods=['POST'])
def calculate_weekly_genre_stats():
    try:
        data = request.json
        user_id = data.get('user_id')
        songs = data.get('songs')  # 사용자가 들은 노래 정보(노래 제목, 가수, 장르 등)

        # 주별 장르 비율 계산 로직 작성
        # songs 리스트를 기반으로 주별 장르 비율 계산

        # 계산된 결과를 GPT-4 API로 전달하여 파이 차트 생성
        gpt4_response = gpt4_api.generate_genre_chart(weekly_genre_stats)

        return jsonify({'chart_url': gpt4_response['chart_url']})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

#orrrrrr
    
#통계
def generate_pie_chart(data, labels):
    plt.figure(figsize=(8, 8))
    plt.pie(data, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # 파이차트를 원형으로 설정
    plt.title('Pie Chart')  # 차트 제목 설정

    # 파이차트를 이미지로 변환
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.read()).decode('utf-8')
    plt.close()

    return img_base64

@app.route('/generate-pie-chart', methods=['POST'])
def generate_pie_chart_endpoint():
    try:
        data = request.json.get('data')  # 백분율 데이터 리스트
        labels = request.json.get('labels')  # 라벨 리스트

        if not data or not labels:
            return jsonify({'error': '데이터와 라벨을 모두 입력하세요.'}), 400

        img_base64 = generate_pie_chart(data, labels)

        return jsonify({'pie_chart_image': img_base64})

    except Exception as e:
        return jsonify({'error': str(e)}), 500







if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='80')
