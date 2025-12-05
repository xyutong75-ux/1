# models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 用户角色：
# - admin: 管理员
# - author: 作者（也是读者）
# - reader: 纯读者
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(32), nullable=False)  # 这里明文，为简单起见
    role = db.Column(db.String(16), default="reader")    # admin/author/reader
    display_author_ui = db.Column(db.Boolean, default=False)

    favorites = db.relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    visit_logs = db.relationship("VisitLog", back_populates="user", cascade="all, delete-orphan")

    def is_admin(self):
        return self.role == "admin"

    def is_author(self):
        return self.role == "author"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_name = db.Column(db.String(64), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    user = db.relationship("User", backref="author_profile")
    books = db.relationship("Book", back_populates="author", cascade="all, delete-orphan")
    albums = db.relationship("Album", back_populates="author", cascade="all, delete-orphan")


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)

    author_id = db.Column(db.Integer, db.ForeignKey("author.id"), nullable=False)
    author = db.relationship("Author", back_populates="albums")

    notes = db.relationship("Note", back_populates="album", cascade="all, delete-orphan")
    visit_logs = db.relationship("VisitLog", back_populates="album", cascade="all, delete-orphan")


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)

    author_id = db.Column(db.Integer, db.ForeignKey("author.id"), nullable=False)
    author = db.relationship("Author", back_populates="books")

    chapters = db.relationship(
        "Chapter", back_populates="book",
        order_by="Chapter.order_index", cascade="all, delete-orphan"
    )
    notes = db.relationship("Note", back_populates="book", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", back_populates="book", cascade="all, delete-orphan")


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=True)
    order_index = db.Column(db.Integer, default=1)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    book = db.relationship("Book", back_populates="chapters")


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=True)
    album_id = db.Column(db.Integer, db.ForeignKey("album.id"), nullable=True)

    book = db.relationship("Book", back_populates="notes")
    album = db.relationship("Album", back_populates="notes")


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)

    user = db.relationship("User", back_populates="favorites")
    book = db.relationship("Book", back_populates="favorites")


class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visited_at = db.Column(db.DateTime, default=datetime.utcnow)

    album_id = db.Column(db.Integer, db.ForeignKey("album.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    album = db.relationship("Album", back_populates="visit_logs")
    user = db.relationship("User", back_populates="visit_logs")
