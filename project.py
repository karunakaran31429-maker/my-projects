from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# ------------------ APP CONFIG ------------------

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///project.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ------------------ MODELS ------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ------------------ AUTH ROUTES ------------------

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)

    user = User(username=username, password_hash=hashed_pw)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user = User.query.filter_by(username=data.get('username')).first()

    if not user or not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "user_id": user.id}), 200

# ------------------ POST ROUTES ------------------

# CREATE POST
@app.route('/posts', methods=['POST'])
def create_post():
    data = request.json

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    title = data.get('title')
    body = data.get('body')
    user_id = data.get('user_id')

    if not title or not body or not user_id:
        return jsonify({"error": "title, body, user_id required"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    post = Post(title=title, body=body, author=user)
    db.session.add(post)
    db.session.commit()

    return jsonify({
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "author": user.username,
        "created_at": post.created_at.strftime('%Y-%m-%d %H:%M')
    }), 201


# READ ALL POSTS
@app.route('/posts', methods=['GET'])
def get_posts():
    posts = Post.query.all()
    result = []

    for p in posts:
        result.append({
            "id": p.id,
            "title": p.title,
            "body": p.body,
            "author": p.author.username,
            "created_at": p.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return jsonify(result), 200


# UPDATE POST
@app.route('/posts/<int:id>', methods=['PUT'])
def update_post(id):
    post = Post.query.get_or_404(id)
    data = request.json

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    if data.get('user_id') != post.user_id:
        return jsonify({"error": "Permission denied"}), 403

    post.title = data.get('title', post.title)
    post.body = data.get('body', post.body)

    db.session.commit()
    return jsonify({"message": "Post updated"}), 200


# DELETE POST
@app.route('/posts/<int:id>', methods=['DELETE'])
def delete_post(id):
    post = Post.query.get_or_404(id)
    data = request.json

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    if data.get('user_id') != post.user_id:
        return jsonify({"error": "Permission denied"}), 403

    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted"}), 200


# FILTER POSTS BY USER
@app.route('/users/<string:username>/posts', methods=['GET'])
def get_user_posts(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = []

    for p in user.posts:
        posts.append({
            "id": p.id,
            "title": p.title,
            "body": p.body,
            "created_at": p.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return jsonify(posts), 200


# ------------------ RUN APP ------------------

if __name__ == '__main__':
    app.run(debug=True)
