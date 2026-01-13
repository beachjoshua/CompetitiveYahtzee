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
        "host": "",
        "players": [],
        "started": False,
        "turn_index": 0,
        "phase": "waiting",
        "dice": [1,1,1,1,1],
        "scorecards": [
            #{"0s":<value>...}... # one for each player
        ]
    }
    return jsonify({"code": code})

@app.route("/room/<code>")
def room(code):
    if code not in rooms:
        return "Room not found", 404
    return render_template("room.html", code=code)

@app.route("/game/<code>")
def game(code):
    if code not in rooms:
        return "Game not found", 404
    room_data = rooms[code]  # server dictionary
    # Only sending "safe" info
    safe_data = {
        "players": [{"name": p["name"]} for p in room_data["players"]],
        "phase": room_data["phase"],
        "turn_index": room_data["turn_index"]
    }
    return render_template("game.html", code=code, room=safe_data)

# ---------- SOCKET EVENTS ----------

@socketio.on("join_room")
def handle_join(data):
    code = data["code"]
    name = data["name"]

    if code not in rooms:
        emit("error", "Room does not exist")
        return

    join_room(code)

    # Assign host if first player
    if not rooms[code]["players"]:
        rooms[code]["host"] = request.sid

    rooms[code]["players"].append({
        "name": name,
        "sid": request.sid
    })

    # Send personal info to this client
    emit("joined", {
        "sid": request.sid,
        "is_host": request.sid == rooms[code]["host"]
    })

    # Broadcast player list
    emit("player_list",
         [p["name"] for p in rooms[code]["players"]],
         room=code)


@socketio.on("start_game")
def start_game(data):
    code = data["code"]
    #name = data["name"]
    room = rooms.get(code)

    if not room:
        return

    #safety check
    if request.sid != room["host"]:
        emit("error", "Only host can start")
        return

    room["phase"] = "playing"
    room["turn_index"] = 0

    first_player = room["players"][0]

    emit("game_page_redirect", {
        "current_turn_sid": first_player["sid"],
        "current_player": first_player["name"]
    }, room=code)

@socketio.on("disconnect")
def handle_disconnect():
    for code, room in rooms.items():
        for i, p in enumerate(room["players"]):
            if p["sid"] == request.sid:
                room["players"].remove(p)

                # Fix turn index
                if i <= room["turn_index"]:
                    room["turn_index"] = max(0, room["turn_index"] - 1)

                if room["players"]:
                    emit("turn_update", {
                        "current_player":
                        room["players"][room["turn_index"]]["name"]
                    }, room=code)
                return

@socketio.on("leave_room")
def handle_leave(data):
    code = data["code"]
    name = data["name"]

    if code in rooms and name in rooms[code]["players"]:
        rooms[code]["players"].remove(name)
        leave_room(code)
        emit("room_update", rooms[code]["players"], room=code)
        
@socketio.on("join_game")
def handle_join(data):
    code = data["code"]
    name = data["name"]

    if code not in rooms:
        emit("error", "Room does not exist")
        return

    #join_room(code)

    # Send personal info to this client
    emit("joined_game", {
        "sid": request.sid,
        "is_host": request.sid == rooms[code]["host"]
    })

    # Broadcast player list
    emit("player_list",
         [p["name"] for p in rooms[code]["players"]],
         room=code) 
        
@socketio.on("take_turn")
def take_turn(data):
    code = data["code"]
    room = rooms.get(code)

    if not room or room["phase"] != "playing":
        return

    current = room["players"][room["turn_index"]]

    #AUTHORITY CHECK
    if request.sid != current["sid"]:
        emit("error", "Not your turn")
        return

    # Advance turn
    room["turn_index"] = (room["turn_index"] + 1) % len(room["players"])
    next_player = room["players"][room["turn_index"]]

    emit("turn_update", {
        "current_turn_sid": next_player["sid"],
        "current_player": next_player["name"]
    }, room=code)

@socketio.on("roll_dice")
def roll_dice(data):
    code = data["code"]
    room = rooms.get(code)

    if not room:
        return

    # Roll 5 dice
    room["dice"] = [random.randint(1, 6) for _ in range(5)]

    emit("dice_rolled", {
        "dice": room["dice"]
    }, room=code)
    print(f"Dice rolled in room {code}: {room['dice']}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
