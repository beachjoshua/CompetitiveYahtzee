# Multiplayer Yahtzee Web Game

A real-time multiplayer Yahtzee game built with Flask and Socket.IO. Players can create or join rooms, take turns rolling dice, hold dice between rolls, and score dynamically with live updates across all connected clients.

## Features
- Real-time multiplayer gameplay with room-based matchmaking
- Turn-based dice rolling and score selection
- Automatic scoring logic for all Yahtzee categories
- Live scorecard synchronization for all players

## Tech Stack
- **Backend:** Python, Flask, Flask-SocketIO  
- **Frontend:** HTML, CSS, JavaScript  
- **Real-time Communication:** WebSockets (Socket.IO)

## How to Run
1. Install dependencies: pip install flask flask-socketio

2. Run the server: python app.py

3. Open http://localhost:5000 in your browser.