from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import requests
import traceback

app = Flask(__name__)
CORS(app)

# shows the html on main localhost page
@app.route("/")
def home():
    return render_template("index.html")

'''
# sends json of the data to the frontend at localhost:5000/api/weather
@app.route("/api/weather")
def get_weather():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    city = request.args.get('city')
    state = request.args.get('state')
    state_name = request.args.get('state_name')
    
    l = LocationData()

    if lat and lon:
        # if coordinates provided (from search system)
        l.lat = float(lat)
        l.lon = float(lon)
        
        # use the provided city/state info from the search results
        if city:
            l.city = city
        if state:
            l.state = state
        if state_name:
            l.state_name = state_name
            
        try:
            w = WeatherData(l.lat, l.lon)
        except Exception as e:
            return jsonify({
                "location": l.to_dict(),
                "weather": {"error": f"Failed to get weather data: {str(e)}"}
            })
    else:
        # use ip location
        l.get_user_location()
        w = WeatherData(l.lat, l.lon)

    return jsonify({
        "location": l.to_dict(),
        "weather": w.to_dict()
    })
'''

def main() -> None:
    pass

if __name__ == "__main__":
    app.run(debug=True)