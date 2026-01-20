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

def calculate_possible_scores(dice_values, room):
    counts = {i: dice_values.count(i) for i in range(1, 7)}
    total = sum(dice_values)

    possible_scores = {
        "Ones": counts[1] * 1,
        "Twos": counts[2] * 2,
        "Threes": counts[3] * 3,
        "Fours": counts[4] * 4,
        "Fives": counts[5] * 5,
        "Sixes": counts[6] * 6,
        "ToK": total if max(counts.values()) >= 3 else 0,
        "FoK": total if max(counts.values()) >= 4 else 0,
        "FH": 25 if sorted(counts.values())[-2:] == [2, 3] else 0,
        "SmS": 30 if any(all(num in dice_values for num in seq) for seq in ([1,2,3,4], [2,3,4,5], [3,4,5,6])) else 0,
        "LgS": 40 if any(all(num in dice_values for num in seq) for seq in ([1,2,3,4,5], [2,3,4,5,6])) else 0,
        "Yahtzee": 50 if max(counts.values()) == 5 else 0,
        "Chance": total
    }

    room["possible_scores"] = possible_scores


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
            "UpperTotal": 0,
            "Bonus": 0,
            "ToK": "__",
            "FoK": "__",
            "FH": "__",
            "SmS": "__",
            "LgS": "__",
            "Yahtzee": "__",
            "Chance": "__",
            "Total": 0
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
    room["rolls_left"] = 3
    room["held_dice"] = [False, False, False, False, False]
    room["dice_values"] = [-1, -1, -1, -1, -1]
    room["total_rounds"] = 13*len(room["players"])
    
    #will be used to store possible scores for the current dice
    #and then will be compared to actual current player's scorecard, and then sent to frontend
    room["possible_scores"] = {
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
            "Chance": "__"}

    emit("startedYahtzeeGame", {
        "current_turn": room["current_turn"],
        "nameForCurrentTurn": nameForCurrentTurn
    }, room=code)


@socketio.on("roll_dice")
def roll_dice(data):
    code = data["code"]
    room = rooms.get(code)
    
    #if no rolls left, make them choose a score
    if room["rolls_left"] <=0:
        emit("no_rolls_left", room=code)
        
        #return as to not allow more rolling
        return
    else: #otherwise decrement rolls left
        room["rolls_left"] -= 1
    
    #roll 5 dice and put in array
    dice = [random.randint(1,6) for _ in range(5)]
    
    for i in range(5):
        if room["held_dice"][i]:
            #set the held dice to the held value
            dice[i] = room["dice_values"][i]
        else:
            #else update the dice to the new value
            room["dice_values"][i] = dice[i]
            
    calculate_possible_scores(room["dice_values"], room)
    
    scorecard_with_possible_scores = room["possible_scores"]
    current_players_scorecard = room["scorecards"][room["current_turn"]]
    for key in scorecard_with_possible_scores:
        if current_players_scorecard[key] != "__":
            scorecard_with_possible_scores[key] = current_players_scorecard[key]
    
    emit("dice_rolled", {"dice": dice}, room=code)
    emit("update_scorecards", {"scorecard_faux": scorecard_with_possible_scores, "scorecard_real": current_players_scorecard, "playerId": room["current_turn"], "name": room["players"][room["current_turn_index"]]["name"]}, room=code)
    
@socketio.on("hold_dice")
def hold_dice(data):
    code = data["code"]
    diceIndex = data["diceIndex"]
    diceValue = data["value"]
    room = rooms.get(code)
    
    #toggles the held status so dont need two seperate events
    room["held_dice"][diceIndex] = not room["held_dice"][diceIndex]
    
    if(room["held_dice"][diceIndex]):
        room["dice_values"][diceIndex] = int(diceValue)
    
    #emit("dice_held", {"diceIndex": diceIndex}, room=code)
    
@socketio.on("select_score")
def select_score(data):
    code = data["code"]
    room = rooms.get(code)
    room["total_rounds"] -= 1
    scoreType = data["category"]
    playerId = room["current_turn"]
    room["scorecards"][playerId][scoreType] = room["possible_scores"][scoreType]
    
    room["scorecards"][playerId]["UpperTotal"] = sum(
        room["scorecards"][playerId][key] for key in ["Ones", "Twos", "Threes", "Fours", "Fives", "Sixes"]
        if isinstance(room["scorecards"][playerId][key], int)
    )
    if room["scorecards"][playerId]["UpperTotal"] >= 63:
        room["scorecards"][playerId]["Bonus"] = 35
    else:
        room["scorecards"][playerId]["Bonus"] = 0
        
    room["scorecards"][playerId]["Total"] = sum(
        value for key, value in room["scorecards"][playerId].items()
        if key not in ["Player_id", "Name", "Total", "UpperTotal"] and isinstance(value, int)
    )
    
    
    
    #update scorecard
    emit("update_scorecards", {"scorecard_faux": None, "scorecard_real": room["scorecards"][playerId], "playerId": room["current_turn"], "name": room["players"][room["current_turn_index"]]["name"]}, room=code)
    
    #reset data for next player
    room["rolls_left"] = 3
    room["dice_values"] = [-1, -1, -1, -1, -1]
    room["held_dice"] = [False, False, False, False, False]
    room["possible_scores"] = {
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
            "Chance": "__"}
    room["current_turn_index"] = (room["current_turn_index"] + 1) % len(room["players"])
    next_player = room["players"][room["current_turn_index"]]

    room["current_turn"] = next_player["id"]
    
    roll_dice(data)
    #go to next player's turn
    emit("turn_ended", {"playerId": room["current_turn"], "name": next_player["name"]}, room=code)
    
    
    if room["total_rounds"] <= 0:
        winner = None
        for player in room["players"]:
            if not winner or room["scorecards"][player["id"]]["Total"] > room["scorecards"][winner["id"]]["Total"]:
                winner = player
        
        emit("game_over", {"winner": winner["name"], "winner_score": room["scorecards"][winner["id"]]["Total"]}, room=code)



if __name__ == "__main__":
    socketio.run(app, debug=True)
