from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, emit
import random
import string
import uuid

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ---------- ROUTES ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/create-room", methods=["POST"])
def create_room():
    code = generate_code()
    rooms[code] = {
        "host": "",
        "players": [],
        "phase": "waiting"
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
    player_id = str(uuid.uuid4())

    if not rooms[code]["players"]:
        rooms[code]["host"] = player_id

    rooms[code]["players"].append({
        "id": player_id,
        "name": name,
        "sid": request.sid
    })

    emit("joined", {
        "player_id": player_id,
        "is_host": player_id == rooms[code]["host"]
    })

    emit("player_list",
         [p["name"] for p in rooms[code]["players"]],
         room=code)


@socketio.on("start_game")
def start_game(data):
    code = data["code"]
    room = rooms.get(code)

    if not room:
        return

    host = room["host"]
    player = next((p for p in room["players"] if p["sid"] == request.sid), None)

    if not player or player["id"] != host:
        emit("error", "Only host can start")
        return

    room["phase"] = "playing"
    emit("game_started", room=code)


@socketio.on("disconnect")
def handle_disconnect():
    for room in rooms.values():
        room["players"] = [
            p for p in room["players"]
            if p["sid"] != request.sid
        ]
        
@socketio.on("create_scorecards")
def create_scorecards(data):
    code = data["code"]
    room = rooms.get(code)

    if not room:
        return

    scorecards = {}

    for player in room["players"]:
        scorecards[player["id"]] = {
            "Player_id": player["id"],
            "Name": player["name"],
            "Ones": "__",
            "Twos": "__",
            "Threes": "__",
            "Fours": "__",
            "Fives": "__",
            "Sixes": "__",
            "ToK": "__",
            "FoK": "__",
            "FH": "__",
            "SmS": "__",
            "LgS": "__",
            "Yahtzee": "__",
            "Chance": "__"
        }

    room["scorecards"] = scorecards
    emit("scorecards_created", scorecards, room=code)


@socketio.on("start_playing")
def start_playing(data):
    code = data["code"]
    room = rooms.get(code)

    room["current_turn_index"] = 0
    room["current_turn"] = room["players"][0]["id"]
    nameForCurrentTurn = room["players"][0]["name"]

    emit("startedYahtzeeGame", {
        "current_turn": room["current_turn"],
        "nameForCurrentTurn": nameForCurrentTurn
    }, room=code)

    
@socketio.on("end_turn")
def end_turn(data):
    code = data["code"]
    room = rooms.get(code)

    room["current_turn_index"] = (room["current_turn_index"] + 1) % len(room["players"])
    next_player = room["players"][room["current_turn_index"]]

    room["current_turn"] = next_player["id"]

    emit("turn_ended", {
        "current_turn": room["current_turn"],
        "nameForCurrentTurn": next_player["name"]
    }, room=code)

    
    


if __name__ == "__main__":
    socketio.run(app, debug=True)
