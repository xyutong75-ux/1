# app.py
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from config import Config
from models import db, User, Author, Album, Book, Chapter, Note, Favorite, VisitLog

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# ------------- 辅助函数 -------------

def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            flash("请先登录。", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin():
            flash("需要管理员权限。", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def author_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_author():
            flash("只有作者可以使用此功能。", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


# ------------- 初始化数据库 & 默认管理员 -------------

def init_db():
    """
    创建数据库表，并初始化一个默认管理员账号：
    用户名：admin  密码：123456
    """
    db.create_all()

    admin_username = "admin"
    admin_password = "123456"   # 全数字短密码，方便你测试
    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(username=admin_username, password=admin_password, role="admin")
        db.session.add(admin)
        db.session.commit()


# ------------- 路由 -------------

@app.route("/")
def index():
    """首页：表格展示书名和作者"""
    books = Book.query.join(Author).order_by(Book.id.desc()).all()
    user = get_current_user()
    return render_template("index.html", books=books, user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    user = get_current_user()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        u = User.query.filter_by(username=username, password=password).first()
        if u:
            session["user_id"] = u.id
            flash("登录成功。", "success")
            next_url = request.form.get("next") or request.args.get("next") or url_for("index")
            return redirect(next_url)
        else:
            flash("用户名或密码错误。", "danger")
    return render_template("login.html", user=user)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("已退出登录。", "info")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    # 注册时可以选择 reader / author
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "reader")
        if not username or not password:
            flash("用户名和密码不能为空。", "warning")
        elif User.query.filter_by(username=username).first():
            flash("该用户名已存在。", "danger")
        else:
            if role not in ("reader", "author"):
                role = "reader"
            user = User(username=username, password=password, role=role)
            db.session.add(user)
            db.session.commit()

            # 如果注册的是作者，同时创建 Author 资料
            if role == "author":
                author = Author(pen_name=username, user=user)
                db.session.add(author)
                db.session.commit()

            flash("注册成功，请登录。", "success")
            return redirect(url_for("login"))
    user = get_current_user()
    return render_template("register.html", user=user)


@app.route("/search", methods=["GET", "POST"])
def search():
    user = get_current_user()
    query = ""
    results = None
    if request.method == "POST":
        query = request.form.get("q", "").strip()
        if query:
            results = Book.query.join(Author).filter(
                (Book.title.ilike(f"%{query}%")) |
                (Author.pen_name.ilike(f"%{query}%"))
            ).all()
        else:
            results = []
    return render_template("search.html", user=user, query=query, results=results)


@app.route("/authors")
def authors():
    user = get_current_user()
    authors = Author.query.order_by(Author.pen_name).all()
    return render_template("authors.html", user=user, authors=authors)


@app.route("/author/<int:author_id>")
def author_detail(author_id):
    user = get_current_user()
    author = Author.query.get_or_404(author_id)
    # 统计每个专辑访问数
    album_stats = []
    for album in author.albums:
        count = VisitLog.query.filter_by(album_id=album.id).count()
        album_stats.append((album, count))
    return render_template(
        "author_detail.html",
        user=user,
        author=author,
        album_stats=album_stats
    )


@app.route("/album/<int:album_id>")
def album_view(album_id):
    user = get_current_user()
    album = Album.query.get_or_404(album_id)
    # 记录访问日志
    log = VisitLog(album=album, user=user)
    db.session.add(log)
    db.session.commit()
    return render_template("album_view.html", user=user, album=album)


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    user = get_current_user()
    book = Book.query.get_or_404(book_id)
    is_favorite = False
    if user:
        is_favorite = Favorite.query.filter_by(user_id=user.id, book_id=book.id).first() is not None
    return render_template(
        "book_detail.html",
        user=user,
        book=book,
        is_favorite=is_favorite
    )


@app.route("/chapter/<int:chapter_id>")
def chapter_detail(chapter_id):
    user = get_current_user()
    chapter = Chapter.query.get_or_404(chapter_id)
    book = chapter.book
    chapters = book.chapters
    # 这里利用列表索引找上一章/下一章
    idx = chapters.index(chapter)
    prev_chapter = chapters[idx - 1] if idx > 0 else None
    next_chapter = chapters[idx + 1] if idx < len(chapters) - 1 else None
    return render_template(
        "chapter_detail.html",
        user=user,
        chapter=chapter,
        prev_chapter=prev_chapter,
        next_chapter=next_chapter
    )


@app.route("/favorites")
@login_required
def favorites():
    user = get_current_user()
    favs = Favorite.query.filter_by(user_id=user.id).all()
    return render_template("favorites.html", user=user, favorites=favs)


@app.route("/favorite/toggle/<int:book_id>", methods=["POST"])
@login_required
def toggle_favorite(book_id):
    user = get_current_user()
    book = Book.query.get_or_404(book_id)
    fav = Favorite.query.filter_by(user_id=user.id, book_id=book.id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        flash("已取消收藏。", "info")
    else:
        fav = Favorite(user=user, book=book)
        db.session.add(fav)
        db.session.commit()
        flash("已收藏该书。", "success")
    return redirect(request.referrer or url_for("book_detail", book_id=book.id))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = get_current_user()
    if request.method == "POST":
        # 只有作者角色才会显示并使用这个开关
        if user.is_author():
            flag = request.form.get("display_author_ui") == "on"
            user.display_author_ui = flag
            db.session.commit()
            flash("设置已保存。", "success")
        else:
            flash("当前账号不是作者，无法打开作者界面。", "warning")
    return render_template("settings.html", user=user)


# ------------- 作者后台 -------------

@app.route("/author/dashboard")
@author_required
def author_dashboard():
    user = get_current_user()
    author = Author.query.filter_by(user_id=user.id).first()
    if not author:
        # 保险：如果没有作者资料就创建一个
        author = Author(pen_name=user.username, user=user)
        db.session.add(author)
        db.session.commit()
    return render_template("author_dashboard.html", user=user, author=author)


@app.route("/author/book/create", methods=["POST"])
@author_required
def create_book():
    user = get_current_user()
    author = Author.query.filter_by(user_id=user.id).first()
    title = request.form.get("title", "").strip()
    desc = request.form.get("description", "").strip()
    if not title:
        flash("书名不能为空。", "warning")
    else:
        book = Book(title=title, description=desc, author=author)
        db.session.add(book)
        db.session.commit()
        flash("新书已创建。", "success")
    # 从哪里来回哪里去（可以从作者后台发起，也可以从作者详情页发起）
    return redirect(request.referrer or url_for("author_dashboard"))


@app.route("/author/album/create", methods=["POST"])
@author_required
def create_album():
    user = get_current_user()
    author = Author.query.filter_by(user_id=user.id).first()
    title = request.form.get("title", "").strip()
    desc = request.form.get("description", "").strip()
    if not title:
        flash("专辑名不能为空。", "warning")
    else:
        album = Album(title=title, description=desc, author=author)
        db.session.add(album)
        db.session.commit()
        flash("新专辑已创建。", "success")
    # 同样：从哪里来回哪里去
    return redirect(request.referrer or url_for("author_dashboard"))


@app.route("/author/book/<int:book_id>/chapter/create", methods=["POST"])
@author_required
def create_chapter(book_id):
    user = get_current_user()
    book = Book.query.get_or_404(book_id)
    if book.author.user_id != user.id:
        flash("你不是该书的作者。", "danger")
        return redirect(url_for("author_dashboard"))

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title:
        flash("章节标题不能为空。", "warning")
    else:
        from sqlalchemy import func
        max_order = db.session.query(func.max(Chapter.order_index)).filter_by(book_id=book.id).scalar() or 0
        chapter = Chapter(
            title=title,
            content=content,
            book=book,
            order_index=max_order + 1
        )
        db.session.add(chapter)
        db.session.commit()
        flash("新章节已创建。", "success")
    return redirect(url_for("book_detail", book_id=book.id))


@app.route("/author/chapter/<int:chapter_id>/delete", methods=["POST"])
@author_required
def delete_chapter(chapter_id):
    user = get_current_user()
    chapter = Chapter.query.get_or_404(chapter_id)
    if chapter.book.author.user_id != user.id:
        flash("你不是该章节所在书的作者。", "danger")
        return redirect(url_for("index"))
    book_id = chapter.book_id
    db.session.delete(chapter)
    db.session.commit()
    flash("章节已删除。", "info")
    return redirect(url_for("book_detail", book_id=book_id))


@app.route("/author/note/create", methods=["POST"])
@author_required
def create_note():
    user = get_current_user()
    author = Author.query.filter_by(user_id=user.id).first()
    content = request.form.get("content", "").strip()
    book_id = request.form.get("book_id")
    album_id = request.form.get("album_id")

    if not content:
        flash("笔记内容不能为空。", "warning")
        return redirect(request.referrer or url_for("author_dashboard"))

    note = Note(content=content)
    if book_id:
        book = Book.query.get(int(book_id))
        if book and book.author_id == author.id:
            note.book = book
    if album_id:
        album = Album.query.get(int(album_id))
        if album and album.author_id == author.id:
            note.album = album

    db.session.add(note)
    db.session.commit()
    flash("笔记已添加。", "success")
    # 从哪来的表单就回哪：作者后台 / 专辑页 / 以后你加的其他页面
    return redirect(request.referrer or url_for("author_dashboard"))


@app.route("/author/note/<int:note_id>/delete", methods=["POST"])
@author_required
def delete_note(note_id):
    user = get_current_user()
    note = Note.query.get_or_404(note_id)
    author = Author.query.filter_by(user_id=user.id).first()
    # 安全：只能删自己名下书/专辑的笔记
    if (note.book and note.book.author_id != author.id) or (note.album and note.album.author_id != author.id):
        flash("你无权删除该笔记。", "danger")
        return redirect(url_for("author_dashboard"))
    db.session.delete(note)
    db.session.commit()
    flash("笔记已删除。", "info")
    return redirect(url_for("author_dashboard"))


# ------------- 管理员后台 -------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    user = get_current_user()
    total_users = User.query.count()
    total_books = Book.query.count()
    total_albums = Album.query.count()
    total_visits = VisitLog.query.count()
    return render_template(
        "admin_dashboard.html",
        user=user,
        total_users=total_users,
        total_books=total_books,
        total_albums=total_albums,
        total_visits=total_visits
    )


@app.route("/admin/export", methods=["GET", "POST"])
@admin_required
def admin_export():
    user = get_current_user()
    albums = Album.query.order_by(Album.title).all()
    data_preview = None

    if request.method == "POST":
        album_id = int(request.form.get("album_id"))
        start = request.form.get("start_date")
        end = request.form.get("end_date")

        album = Album.query.get_or_404(album_id)

        start_dt = datetime.strptime(start, "%Y-%m-%d") if start else datetime.min
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.max

        logs = VisitLog.query.filter(
            VisitLog.album_id == album.id,
            VisitLog.visited_at >= start_dt,
            VisitLog.visited_at <= end_dt
        ).all()

        total_visits = len(logs)
        unique_user_ids = {log.user_id for log in logs if log.user_id is not None}
        unique_users_count = len(unique_user_ids)

        from io import StringIO
        output = StringIO()
        output.write("album_id,album_title,start_date,end_date,total_visits,unique_users\n")
        output.write(f"{album.id},{album.title},{start_dt.date()},{end_dt.date()},{total_visits},{unique_users_count}\n")
        csv_text = output.getvalue()
        data_preview = csv_text

        flash("导出数据已生成（下方为预览）。", "success")

    return render_template(
        "admin_export.html",
        user=user,
        albums=albums,
        data_preview=data_preview
    )


# ------------- 主程序入口 -------------

if __name__ == "__main__":
    # 先初始化数据库和默认管理员
    with app.app_context():
        init_db()
    app.run(debug=True)
