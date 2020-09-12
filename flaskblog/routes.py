import os
from secrets import token_hex
from random import choice
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from flaskblog import *
from flaskblog.forms import (
    RegistrationForm,
    LoginForm,
    ConfirmDeleteForm,
    UpdateAccountForm,
    PostForm,
    RequestResetForm,
    ChangePasswordForm,
    ConfirmDeleteForm,
)


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message(
        "Password Reset Request", sender="noreply@demo.com", recipients=[user.email]
    )

    msg.html = f"""
    <h1 style="font-family: Poppins;text-align: center; ">
Password Reset | FlaskBlog </h1>
<p style="text-align: center; font-family: Poppins;
font-size: larger;">
Looks like you've forgotten your password.
Don't worry! It happens to everyone.
Reset it by clicking on the link below.
If you did not request for this reset,
simply ignorethis email and no changes
will be made to your FlaskBlog account.
</p>

<div class="wrapper" style="text-align: center;">
<a href="{url_for('reset_token', token=token, _external=True)}
" style="
text-decoration: none; font-family: Poppins;
padding: 20px; background: rgb(255, 206, 92);
margin: 50px; display: block; color: black;
font-size: 1.8em;
">
Reset my Password
</a>
</div>
"""
    mail.send(msg)


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get("page", 1, type=int)
    posts = Post.query.order_by(
        Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template("index.html", posts=posts, current_user=current_user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("You already have an account.", "warning")
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )
        user = User(
            username=form.username.data, email=form.email.data, password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created! You are now able to log in", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form, legend="Join Us")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.", "warning")
        return redirect(url_for("home"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            flash("Log in Successful.", "success")
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for("home"))
        else:
            flash("Login Unsuccessful. Please check email and password", "danger")
    return render_template("login.html", form=form, legend="Login")


@app.route("/logout/")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully!", "success")
    return redirect(url_for("home"))


def save_picture(form_picture):
    random_hex = token_hex(16)
    _, f_extn = os.path.splitext(form_picture.filename)
    picture_filename = random_hex + f_extn
    picture_path = os.path.join(
        app.root_path, "static/profile_pics", picture_filename)

    final_size = (200, 200)
    image = Image.open(form_picture)
    image.thumbnail(final_size)
    image.save(picture_path)

    return picture_filename


@app.route("/account/", methods=["GET", "POST"])
@login_required
def account():
    form = UpdateAccountForm()
    user = User.query.filter_by(username=current_user.username).first()

    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()

        flash("Your account has been updated!", "success")
        return redirect(url_for("account"))

    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for(
        "static", filename=f"profile_pics/{current_user.image_file}")
    return render_template(
        "account.html", image_file=image_file, form=form, legend="Update your Account"
    )


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():

        post = Post(
            title=form.title.data,
            content=form.content.data,
            author=current_user,
            font=form.font.data,
            font_color=form.font_color.data,
        )

        db.session.add(post)
        db.session.commit()

        flash("Your post has been created successfully!", "success")
        return redirect(url_for("home"))
    return render_template("post_actions.html", form=form, legend="Create a Post")


@app.route("/post/<int:post_id>/view", methods=["GET", "POST"])
@login_required
def post(post_id):
    validated = False

    if current_user.username == "__FLASKBLOG_ADMIN__":
        validated = True

    post = Post.query.get_or_404(post_id)

    # this is to prevent users from refreshing the page to gain more views
    choices = [1, 1, 0, 0, 0, 0]
    incrementing_number = choice(choices)
    post.views += incrementing_number
    db.session.commit()

    return render_template("post.html", post=post, validated=validated)


@login_required
@app.route("/post/<int:post_id>/update", methods=["GET", "POST"])
def update_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.author != current_user:
        abort(403)

    form = PostForm()

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.font = form.font.data
        post.font_color = form.font_color.data
        post.is_edited = True
        db.session.commit()
        flash("Your post has been updated successfully", "success")
        return redirect(url_for("post", post_id=post.id))

    elif request.method == "GET":
        form.title.data = post.title
        form.content.data = post.content

    return render_template("post_actions.html", form=form, legend="Update Post")


@app.route("/post/<int:post_id>/delete", methods=["GET", "POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.author != current_user:
        abort(403)

    db.session.delete(post)
    db.session.commit()

    flash("Your post has been deleted successfully.", "success")
    return redirect(url_for("home"))


@app.route("/user/<string:username>")
def user_post(username):
    page = request.args.get("page", 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = (
        Post.query.filter_by(author=user)
        .order_by(Post.date_posted.desc())
        .paginate(page=page, per_page=5)
    )
    return render_template("filter_post.html", posts=posts, user=user)


@app.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RequestResetForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash(
            "An email has been sent with instructions to reset your password. You can close this tab now.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template(
        "reset_request.html",
        title="Reset Password",
        form=form,
        legend="Request a Password Reset",
    )


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token", "warning")
        return redirect(url_for("reset_request"))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode(
            "utf-8"
        )
        user.password = hashed_password
        db.session.commit()
        flash("Your password has been updated! You are now able to log in", "success")
        return redirect(url_for("login"))
    return render_template(
        "reset_token.html",
        title="Reset Password",
        form=form,
        legend="Change your Password",
    )


@login_required
@app.route("/validate_post/<int:post_id>", methods=["GET", "POST"])
def validate_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user.username != "__FLASKBLOG_ADMIN__":
        abort(403)

    elif current_user.username == "__FLASKBLOG_ADMIN__":
        validated = True

    form = VerifyPostForm()

    if form.validate_on_submit():
        post.is_verified = form.verify.data
        db.session.commit()
        flash("That post has been verified.", "success")
        return redirect(url_for("home"))

    return render_template(
        "verify_post.html", form=form, post=post, legend="Verify this Post"
    )


@app.route("/confirm_delete_post/<int:post_id>", methods=["GET", "POST"])
@login_required
def confirm_delete_post(post_id):
    form = ConfirmDeleteForm()
    post = Post.query.get_or_404(post_id)

    if form.validate_on_submit():
        return redirect(url_for("delete_post", post_id=post.id))

    return render_template(
        "confirm_post_deletion.html",
        form=form,
        post=post,
        legend="Are you sure?",
    )


@app.route("/post/forward/<int:post_id>", methods=["POST"])
@login_required
def forward_post(post_id):
    original_post = Post.query.get_or_404(post_id)
    new_post = Post(
        title=original_post.title,
        content=original_post.content,
        author=current_user,
        font=original_post.font,
        font_color=original_post.font_color,
        is_forwarded=True
    )
    db.session.add(new_post)
    db.session.commit()
    flash("You have forwarded that post successfully.", "success")
    return redirect(url_for("home"))


# Errorhandlers!
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html")


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html")


@app.errorhandler(403)
def no_permission(error):
    return render_template("403.html")
