from flask import Flask, render_template, redirect, url_for, flash, abort,request 
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from form import LoginForm, RegisterForm, CreatePostForm, CommentForm
from flask_gravatar import Gravatar
import smtplib
from markupsafe import escape
MY_EMAIL = "katilpythontest@gmail.com"
MY_PASSWORD = "bbshoiqsgoebskmo"
R_EMAIL="tiwariayush222@gmail.com"
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
bootsrtap=Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://wwe_fan_update_user:796l8pQZk78sm71WVRdvnGKzcjlTY3D0@dpg-d0coeh3e5dus73aj9klg-a/wwe_fan_update'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class BlogPost(db.Model):  
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comments = relationship("Comment", back_populates="parent_post")

class User(UserMixin, db.Model):  # Parent
    __tablename__ = "users"  # Name of the table
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = db.relationship("BlogPost", backref="author")
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)        
    return decorated_function



@app.route('/',methods=["GET",'POST'])
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,current_user=current_user)

@app.route("/new-post", methods=["GET", "POST"])

def add_new_post():
    if not current_user.is_authenticated:
        # User is not logged in, redirect to the login page
        flash("You need to login to create a new post.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_post = BlogPost(
            title=request.form['title'],
            subtitle=request.form['subtitle'],
            body=request.form['body'],
            img_url=request.form['img_url'],
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", current_user=current_user)

@app.route('/login',methods=['GET','POST'])
def login():
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html",current_user=current_user)

@app.route('/register', methods=["GET",'POST'])
def register():
    if request.method =='POST':

        if User.query.filter_by(email=request.form['email']).first():
            print(User.query.filter_by(email=request.form['email']).first())
            #User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        hash_and_salted_password = generate_password_hash(
            request.form['password'],
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form['email'],
            name=request.form['name'],
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", current_user=current_user)




@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=current_user,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/post/<int:post_id>",methods=['GET','POST'])

def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    
    if request.method=='POST':
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        else:
            new_comment = Comment(
                text=request.form['comment_text'],
                comment_author=current_user,
                parent_post=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            return render_template("post.html", post=requested_post, current_user=current_user)
    return render_template("post.html", post=requested_post,current_user=current_user)

@app.route("/about")
def about():
    return render_template("about.html",current_user=current_user)
      
@app.route("/contact", methods=["GET", "POST"])

def contact():
    if not current_user.is_authenticated:
        flash("You need to login or register to contact.")
        return redirect(url_for('login'))
    
    else:
        if request.method == "POST":
            name=request.form["name"]
            email=request.form["email"]
            phone=request.form["phone"]
            message=request.form["message"]
            with smtplib.SMTP_SSL("smtp.googlemail.com") as connection:
                    connection.login(MY_EMAIL, MY_PASSWORD)
                    connection.sendmail(
                            from_addr=MY_EMAIL,
                            to_addrs=R_EMAIL,
                        msg=f"Subject: Details!!! \n\nName:{name}\nE-mail:{email}\nPhone no.:{phone}\nMessage:{message}"
                )
            return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
