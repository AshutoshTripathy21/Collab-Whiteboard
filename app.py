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
import base64

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
    profile_picture = db.Column(db.LargeBinary)

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

@app.route('/dashboard')
@login_required
def dashboard():
    # Retrieve the user's profile picture from the database
    profile_picture_data = current_user.profile_picture

    # Encode the profile picture data as base64
    if profile_picture_data:
        profile_picture_base64 = base64.b64encode(profile_picture_data).decode('utf-8')
    else:
        # Provide a default base64 encoded image if profile picture is not available
        with open('static/default_profile_picture.png', 'rb') as f:
            profile_picture_base64 = base64.b64encode(f.read()).decode('utf-8')

    return render_template('dashboard.html', current_user=current_user, profile_picture_base64=profile_picture_base64)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        bio = request.form.get('bio')
        current_user.bio = bio

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                # Encode the image as bytes and store it in the database
                current_user.profile_picture = file.read()

        flash('Profile updated!')
        db.session.commit()
        return redirect(url_for('dashboard'))

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
        return redirect(url_for('login', next=url_for('create_room')))
    return render_template("home.html")

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
    if not room or not name:
        return

    if room in rooms:
        leave_room(room)  # Use Flask-SocketIO's leave_room() function
        send({"name": name, "message": "has left the room"}, to=room)
        rooms[room]["members"] -= 1

        if name == rooms[room]["creator"]:
            # If the creator is leaving, emit a message to all clients in the room to leave
            emit("leave_room", room=room, broadcast=True, include_self=False)
            del rooms[room]
        else:
            # If other members are leaving
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

@app.route('/leave_room')
@login_required
def leave_room_route():
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return redirect(url_for("home"))  # Redirect to home if not in a room or not authenticated

    if room in rooms:
        if name == rooms[room]["creator"]:
            # If the creator leaves, delete the room and redirect to home
            del rooms[room]
            #flash("You've left the room and the room has been deleted.")
            return redirect(url_for("home"))
        else:
            # If other users leave, reduce member count and redirect to home
            #leave_room(room)
            #send({"name": name, "message": "has left the room"}, to=room)
            rooms[room]["members"] -= 1
            if rooms[room]["members"] <= 0:
                del rooms[room]
    session.pop("room")
    session.pop("name")
    return redirect(url_for('home'))

@socketio.on("leave_room")
def leave_room_event():
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return

    leave_room(room)
    send({"name": name, "message": "has left the room"}, to=room)

# ... (other code)

@app.cli.command("initdb")
def initdb_command():
    """Initialize the database."""
    db.create_all()
    print("Initialized the database.")


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
