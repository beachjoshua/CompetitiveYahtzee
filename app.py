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
        "host": "socket_id_placeholder",
        "players": [],
        "started": False
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
    
    if len(rooms[code]["players"]) == 0:
        rooms[code]["host"] = request.sid
    
    rooms[code]["players"].append({
        "name": name,
        "sid": request.sid
    })

    emit("room_update", {
        "players": [p["name"] for p in rooms[code]["players"]],
        "is_host": request.sid == rooms[code]["host"],
        "started": rooms[code].get("started", False)
    }, room=request.sid)

    emit("player_list", 
         [p["name"] for p in rooms[code]["players"]],
         room=code)

@socketio.on("start_game")
def start_game(data):
    code = data["code"]

    if code not in rooms:
        return

    # SECURITY CHECK
    if request.sid != rooms[code]["host"]:
        emit("error", "Only the host can start the game")
        return

    rooms[code]["started"] = True
    emit("game_started", room=code)

@socketio.on("disconnect")
def handle_disconnect():
    for code, room in rooms.items():
        for p in room["players"]:
            if p["sid"] == request.sid:
                room["players"].remove(p)

                # Transfer host
                if room["host"] == request.sid and room["players"]:
                    room["host"] = room["players"][0]["sid"]

                emit("player_list",
                     [x["name"] for x in room["players"]],
                     room=code)
                return


@socketio.on("leave_room")
def handle_leave(data):
    code = data["code"]
    name = data["name"]

    if code in rooms and name in rooms[code]["players"]:
        rooms[code]["players"].remove(name)
        leave_room(code)
        emit("room_update", rooms[code]["players"], room=code)


if __name__ == "__main__":
    socketio.run(app, debug=True)
