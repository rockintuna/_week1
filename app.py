from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import jwt
import hashlib

client = MongoClient('localhost', 27017)
db = client.honorablejudge
app = Flask(__name__)

SECRET_KEY = '99judge2'

@app.route('/')
def main():
    posts = list(db.post.find({}))
    for post in posts:
        post["_id"] = str(post["_id"])
    return render_template('index.html', posts=posts)

@app.route('/login_main')
def login_main():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route('/register', methods=['POST'])
def register_user():
    id_receive = request.form['id']
    pw_receive = request.form['pw']
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    doc = {
        "id": id_receive,  # 아이디
        "pw": pw_hash,  # 비밀번호
    }

    user_id_exist_check(id_receive)
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/login', methods=['POST'])
def login():
    id_receive = request.form['id']
    pw_receive = request.form['pw']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'id': id_receive, 'pw': pw_hash})

    if result is not None:
        payload = {
         'id': id_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }

        # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')
        # 3.9
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

@app.route('/user_info', methods=['GET'])
def get_user_info():
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userinfo = db.user.find_one({'id': payload['id']})
        return jsonify({'result': 'success', 'nickname': userinfo['nick']})
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

@app.route('/posts', methods=['GET'])
def get_post_list():
    posts = list(db.post.find({}))
    for post in posts:
        post["_id"] = str(post["_id"])
    return jsonify({'posts': posts})

@app.route('/post', methods=['GET'])
def get_post():
    # writing_id_receive = request.form['writing_id']
    writing_id_receive = request.args.get("writing_id")
    writing_id_valid_check(writing_id_receive)
    post = db.post.find_one({'writing_id':writing_id_receive},{'_id':False})
    return render_template('post.html', post=post)

@app.route('/post', methods=['POST'])
def add_post():
    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        # writing_id_receive = request.form['writing_id']
        title_receive = request.form['title']
        content_receive = request.form['content']
        image_receive = request.form['image']
        id = db.users.find_one({"id": payload["id"]}, {'_id':False})

        doc = {
            'id': id,
            'title': title_receive,
            'content': content_receive,
            'image': image_receive,
            'postDate': datetime.now(),
            'like': 0,
            'unlike': 0
        }

        db.post.insert_one(doc)
        return jsonify({'msg': '고민이 성공적으로 작성되었습니다.'})
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

@app.route('/comment', methods=['POST'])
def add_comment():

    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        id = db.users.find_one({"id": payload["id"]})
        writing_id_receive = request.form['writing_id']
        comment_receive = request.form['com']
        writing_id_valid_check(writing_id_receive)
        db.post.update_one({'writing_id': writing_id_receive},
                           {'$push': {'comments': {'comment': comment_receive, 'id': id}}})
        return jsonify({'msg': '댓글이 작성되었습니다.'})
    except jwt.ExpiredSignatureError:
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

@app.route('/post', methods=['DELETE'])
def delete_post():
    writing_id_receive = request.form['writing_id']

    writing_id_valid_check(writing_id_receive)
    db.post.delete_one({'writing_id': writing_id_receive})
    return jsonify({'msg': '고민이 삭제되었습니다.'})

@app.route('/post', methods=['PUT'])
def update_post():
    writing_id_receive = request.form['writing_id']
    title_receive = request.form['title']
    content_receive = request.form['content']
    image_receive = request.form['image']

    writing_id_valid_check(writing_id_receive)

    db.post.update_one({'writing_id': writing_id_receive},{'$set': {'title': title_receive,'content': content_receive,'image': image_receive}})
    return jsonify({'msg': '고민이 수정되었습니다.'})

@app.route('/like', methods=['POST'])
def like_post():
    writing_id_receive = request.form['writing_id']
    writing_id_valid_check(writing_id_receive)
    db.post.update_one({'writing_id': writing_id_receive}, {'$inc': {'like':1}})
    return jsonify({'msg': '추천.'})

@app.route('/unlike', methods=['POST'])
def unlike_post():
    writing_id_receive = request.form['writing_id']
    writing_id_valid_check(writing_id_receive)
    db.post.update_one({'writing_id': writing_id_receive}, {'$inc': {'unlike':1}})
    return jsonify({'msg': '비추천.'})

def writing_id_valid_check(writing_id):
    # todo try catch
    if db.post.find_one({'writing_id': writing_id}) is None:
        raise Exception('존재하지 않는 글 ID 입니다.')

# def writing_id_exist_check(writing_id):
#     # todo try catch
#     if db.post.find_one({'writing_id': writing_id}) is not None:
#         raise Exception('이미 존재하는 글 ID 입니다.')

def user_id_exist_check(id):
    # todo try catch
    if db.users.find_one({'id': id}) is not None:
        raise Exception('이미 존재하는 사용자 ID 입니다.')

if __name__ == '__main__':
   app.run('0.0.0.0',port=5000,debug=True)