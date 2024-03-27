import os
from flask import Flask, abort, appcontext_popped, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import csv
import random
import string
from datetime import datetime
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt 
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['SECRET_KEY'] = 'major_project_whiteboard'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whiteboard.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
bcrypt = Bcrypt(app) 
#migrate = Migrate(app, db)
socketio = SocketIO(app)
migrate = Migrate(app, db)

app.config['MAIL_SERVER'] = 'smtp.office365.com'
app.config['MAIL_PORT'] = '587'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'exampleflask365@outlook.com'
app.config['MAIL_PASSWORD'] = 'Flask2024'
app.config['MAIL_DEFAULT_SENDER'] = 'exampleflask365@outlook.com'  # Update with your Outlook email address
app.config['MAIL_USE_SSL'] = False
#app.config['MAIL_DEFAULT_SENDER'] = 'examplework138@gmail.com'

mail = Mail(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_otp():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    joined_on = db.Column(db.DateTime, default=datetime.utcnow)  # Added joined_on field
    bio = db.Column(db.Text)  # Added bio field
    profile_picture = db.Column(db.String(255))

rooms = {}

def generate_group_code():
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(9))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password)

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash('Username already exists. Please choose another username.')
        else:
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('login'))

    return render_template('register.html')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route("/", methods=["POST", "GET"])
def home():
    if request.method == "POST":
        name = current_user.username
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        #if not name:
            #return render_template("create_room.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:
            room = generate_group_code()
            rooms[room] = {"members": 0, "messages": [], "creator": name}

        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))
    if not current_user.is_authenticated:
        # User is not logged in, redirect to login page with 'next' parameter
        return redirect(url_for('login', next=url_for('home')))
    return render_template("home.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html', current_user=current_user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Handle form submission to update user profile
        bio = request.form.get('bio')
        # Update user's bio
        current_user.bio = bio

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                username_folder = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username)
                if not os.path.exists(username_folder):
                    os.makedirs(username_folder)
                filename = secure_filename(file.filename)
                file.save(os.path.join(username_folder, filename))
                # Update user's profile picture URL
                current_user.profile_picture = os.path.join(current_user.username, filename)
        
        flash('Profile updated!')

        # Commit changes to the database
        db.session.commit()

        return redirect(url_for('dashboard'))  # Redirect to dashboard after profile update

    return render_template('editProfile.html', current_user=current_user)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            otp = generate_otp()
            session['reset_email'] = email
            session['reset_otp'] = otp
            msg = Message('Reset Your Password', recipients=[email])
            msg.body = f'Your OTP is: {otp}'
            mail.send(msg)
            return redirect(url_for('verify_otp'))
        else:
            flash('Email address not found. Please enter a valid email.')

    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_email' in session and 'reset_otp' in session:
        if request.method == 'POST':
            otp = request.form['otp']
            if otp == session['reset_otp']:
                return redirect(url_for('reset_password'))
            else:
                flash('Invalid OTP. Please try again.')

        return render_template('verify_otp.html')
    else:
        return redirect(url_for('forgot_password'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' in session:
        if request.method == 'POST':
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            if new_password == confirm_password:
                user = User.query.filter_by(email=session['reset_email']).first()
                if user:
                    user.password = bcrypt.generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password reset successful. You can now login with your new password.')
                    session.pop('reset_email')
                    session.pop('reset_otp')
                    return redirect(url_for('login'))
                else:
                    flash('User not found.')
            else:
                flash('Passwords do not match. Please try again.')

        return render_template('reset_password.html')
    else:
        return redirect(url_for('forgot_password'))

@app.route('/create_room', methods=['GET', 'POST'])
@login_required
def create_room():
    #session.clear()
    if request.method == "POST":
        name = current_user.username
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        #if not name:
            #return render_template("create_room.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("create_room.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:
            room = generate_group_code()
            rooms[room] = {"members": 0, "messages": [], "creator": name}

        elif code not in rooms:
            return render_template("create_room.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))
    if not current_user.is_authenticated:
        # User is not logged in, redirect to login page with 'next' parameter
        return redirect(url_for('login', next=url_for('create_room')))
    return render_template("create_room.html")

@app.route("/room")
@login_required
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("create_room"))
    group_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'group_uploads', room)
    if not os.path.exists(group_folder):
        os.makedirs(group_folder)
    uploaded_files = os.listdir(group_folder)
    return render_template("room.html", code=room, messages=rooms[room]["messages"], uploaded_files=uploaded_files)

# SocketIO event handler for file upload
@socketio.on("fileUpload")
def handle_file_upload(file_data):
    filename = file_data["filename"]
    file_data = file_data["data"]

    # Create a folder for group uploads if it doesn't exist
    group_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'group_uploads', session.get("room"))
    app.logger.info("Saving file %s in folder %s", filename, group_folder)
    if not os.path.exists(group_folder):
        os.makedirs(group_folder)

    # Save the uploaded file in the group uploads folder
    file_path = os.path.join(group_folder, secure_filename(filename))
    
    with open(file_path, 'wb') as file:
        file.write(file_data)

    # Broadcast file upload event to all clients in the room
    socketio.emit("fileUploaded", {"filename": filename}, room=session.get("room"))


@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")
    if room in rooms:
        rooms[room]["members"] -= 1
        if name == rooms[room]["creator"]:
            # If the creator is leaving but there are still members, update creator info
            rooms[room]["creator"] = next(iter(rooms[room]["members"]))
        if rooms[room]["members"] == 1:
            pass
        if rooms[room]["members"] <= 0:
            del rooms[room]

@socketio.on("drawing")
def handle_drawing(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    emit("drawing", data, to=room, broadcast=True)
    rooms[room]["messages"].append(data)
    
@app.route('/uploads/group_uploads/<room>/<path:filename>')
@login_required
def uploaded_file(room, filename):
    group_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'group_uploads', room)
    file_path = os.path.join(group_folder, filename)
    if os.path.exists(file_path):
        return send_from_directory(group_folder, filename, as_attachment=True)
    else:
        abort(404)
# ... (other code)

@app.cli.command("initdb")
def initdb_command():
    """Initialize the database."""
    db.create_all()
    print("Initialized the database.")


if __name__ == "__main__":
    socketio.run(app, debug=True)
