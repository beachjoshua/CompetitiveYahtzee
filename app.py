from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
import string

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory room storage
rooms = {}

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/create-room", methods=["POST"])
def create_room():
    code = generate_code()
    rooms[code] = {
        "players": []
    }
    return jsonify({"code": code})

@app.route("/room/<code>")
def room(code):
    if code not in rooms:
        return "Room not found", 404
    return render_template("room.html", code=code)

# ---------- SOCKET EVENTS ----------

@socketio.on("join_room")
def handle_join(data):
    code = data["code"]
    name = data["name"]

    if code not in rooms:
        emit("error", "Room does not exist")
        return

    join_room(code)
    rooms[code]["players"].append(name)

    emit("room_update", rooms[code]["players"], room=code)

@socketio.on("leave_room")
def handle_leave(data):
    code = data["code"]
    name = data["name"]

    if code in rooms and name in rooms[code]["players"]:
        rooms[code]["players"].remove(name)
        leave_room(code)
        emit("room_update", rooms[code]["players"], room=code)

@socketio.on("disconnect")
def handle_disconnect():
    print("User disconnected")

if __name__ == "__main__":
    socketio.run(app, debug=True)
