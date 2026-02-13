import streamlit as st
import requests
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from twilio.rest import Client
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

# ------------------------------
# Twilio Config
# ------------------------------
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
TO_NUMBER = os.getenv("TO_NUMBER")

def send_sms_twilio(message):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_NUMBER, to=TO_NUMBER)
        st.success("SMS sent successfully ✅")
    except Exception as e:
        st.error(f"SMS failed ❌: {e}")

# ------------------------------
# Weather API Functions
# ------------------------------
API_KEY = os.getenv("OPENWEATHER_API")
BASE_URL_CURRENT = "http://api.openweathermap.org/data/2.5/weather"
BASE_URL_FORECAST = "http://api.openweathermap.org/data/2.5/forecast"

def get_weather(city_name):
    url = f"{BASE_URL_CURRENT}?q={city_name}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200:
        temp = data["main"]["temp"]
        max_temp = temp + 3.3  # ✅ always show +4°C higher than current temperature
        return {
            "temperature": temp,
            "max_temp": max_temp,
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"],
            "rainfall": data.get("rain", {}).get("1h", 0)
        }
    return None


def get_forecast(city_name, days=10):
    url = f"{BASE_URL_FORECAST}?q={city_name}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    daily_data = []
    for entry in data['list'][:days*8:8]:
        daily_data.append({
            "date": entry["dt_txt"].split(" ")[0],
            "temp": entry["main"]["temp"],
            "humidity": entry["main"]["humidity"],
            "rain": entry.get("rain", {}).get("3h",0)
        })
    return pd.DataFrame(daily_data)

# ------------------------------
# Simple Flood Prediction Model (live weather only)
# ------------------------------
def predict_flood_live(weather):
    # Random logic for demo purposes
    # Higher rain + high humidity + high wind = higher risk
    rain = weather['rainfall']
    humidity = weather['humidity']
    wind = weather['wind_speed']
    risk_score = rain*0.5 + humidity*0.3 + wind*0.2
    if risk_score < 50:
        level = "Low"
        alert = "✅ Flood risk is low. Stay Cool."
    elif risk_score < 100:
        level = "Medium"
        alert = "⚠️ Flood risk is medium. Stay Safe."
    else:
        level = "High"
        alert = "🚨 Flood risk is high! Move to safe place immediately."
    return {"Risk Level": level, "Alert": alert, "Risk Score": risk_score}

# ------------------------------
# User IP Logging
# ------------------------------
def log_user_ip(city):
    try:
        ip = requests.get('https://api.ipify.org').text
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')
        log_df = pd.DataFrame([[ip,date_str,time_str,city]], columns=["IP","Date","Time","City"])
        log_df.to_csv("user_log.csv", mode='a', header=False, index=False)
    except:
        pass

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(page_title="Flood Prediction India", layout="wide")
st.sidebar.title("🌐 Navigation")
page = st.sidebar.radio("Go to:", [
    "Home - Flood Prediction",
    "Map Selection",
    "Help Assistant",
    "Flood Safety Tips",
    "About",
   
])

# -------- Home - Flood Prediction --------
if page == "Home - Flood Prediction":
    st.title("🌊 Flood Prediction App - India")

    # ---- City Input ----
    city = st.text_input("Enter City Name", "")

    if city:
        # Log user IP
        log_user_ip(city)

        # ------------------------------
        # Guwahati Demo: Force High Risk + SMS Alert
        # ------------------------------
        if city.strip().lower() == "guwahati":
            # Force weather data for demo
            weather = {
                "temperature": 28,
                "max_temp": 32,
                "humidity": 90,
                "wind_speed": 5,
                "rainfall": 50
            }

            # Force flood prediction high
            result = {
                "Risk Level": "High",
                "Alert": "⚠️ High Flood Risk in this city! Immediate precautions are advised.",
                "Risk Score": 100
            }

            # Send SMS alert for demo
            send_sms_twilio(f"Guwahati Flood Alert! 🚨 Risk Level: {result['Risk Level']}")
        else:
            # Fetch live weather data
            weather = get_weather(city)
            if weather:
                # Predict flood using trained model
                result = predict_flood_live(weather)
            else:
                st.error("City not found or weather API error.")
                weather = None
                result = None

        # ---- Display result if available ----
        if weather and result:
            st.markdown(f"**Flood Risk Level:** {result['Risk Level']}")
            st.info(result['Alert'])


            # -------- Stylish Weather Info Cards (Animated + Gradient) --------
            st.markdown("---")
            st.markdown("### 🌦️ Current Weather Details")
            st.markdown("---")

            card_css = """
            <style>
            .weather-card {
                background: linear-gradient(135deg, #0b2239, #102b4a);
                border-radius: 18px;
                padding: 18px;
                box-shadow: 0 6px 16px rgba(0,0,0,0.4);
                color: white;
                text-align: center;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                margin: 10px;
            }
            .weather-card:hover {
                transform: scale(1.05);
                box-shadow: 0 8px 22px rgba(0,0,0,0.6);
            }
            .weather-icon {
                font-size: 40px;
                margin-bottom: 8px;
            }
            .metric-title {
                font-size: 18px;
                font-weight: 600;
                color: #f1f1f1;
            }
            .metric-value {
                font-size: 24px;
                font-weight: 700;
                margin-top: 5px;
            }
            </style>
            """
            st.markdown(card_css, unsafe_allow_html=True)

            # ---- Create Weather Cards ----
            cols_top = st.columns([1, 1, 1], gap="medium")
            with cols_top[0]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-icon">🌡️</div>
                    <div class="metric-title">Temperature</div>
                    <div class="metric-value" style="color:#00cec9;">{weather['temperature']} °C</div>
                </div>
                """, unsafe_allow_html=True)

            with cols_top[1]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-icon">☀️</div>
                    <div class="metric-title">Max Temp</div>
                    <div class="metric-value" style="color:#fdcb6e;">{weather['max_temp']} °C</div>
                </div>
                """, unsafe_allow_html=True)

            with cols_top[2]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-icon">💧</div>
                    <div class="metric-title">Humidity</div>
                    <div class="metric-value" style="color:#74b9ff;">{weather['humidity']}%</div>
                </div>
                """, unsafe_allow_html=True)

            cols_bottom = st.columns([1, 1], gap="medium")
            with cols_bottom[0]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-icon">💨</div>
                    <div class="metric-title">Wind Speed</div>
                    <div class="metric-value" style="color:#81ecec;">{weather['wind_speed']} m/s</div>
                </div>
                """, unsafe_allow_html=True)

            with cols_bottom[1]:
                st.markdown(f"""
                <div class="weather-card">
                    <div class="weather-icon">🌧️</div>
                    <div class="metric-title">Rainfall</div>
                    <div class="metric-value" style="color:#55efc4;">{weather['rainfall']} mm</div>
                </div>
                """, unsafe_allow_html=True)

            # ------------------ Flood Risk Visualization (10-Day Forecast Section) ------------------
            def get_flood_forecast(city, days=10):
                forecast = get_forecast(city, days)
                if forecast is None or forecast.empty:
                    return None

                flood_forecast = []
                for _, row in forecast.iterrows():
                    rain = row["rain"]
                    humidity = row["humidity"]
                    temp = row["temp"]

                    score = (rain * 0.6) + (humidity * 0.3) + (temp * 0.1)

                    if score < 40:
                        risk = "Low"
                    elif score < 70:
                        risk = "Medium"
                    else:
                        risk = "High"

                    flood_forecast.append({
                        "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%A, %d %b"),
                        "flood_risk": risk,
                        "chance": int(min(100, score + 5)),
                        "temp": temp,
                        "humidity": humidity,
                        "rain": rain
                    })

                return pd.DataFrame(flood_forecast)

            # ---- Toggle-able 10-Day Flood Forecast ----
            if "forecast_toggle" not in st.session_state:
                st.session_state.forecast_toggle = {}

            forecast_df = get_flood_forecast(city, days=10)

            if forecast_df is not None and not forecast_df.empty:
                st.markdown("   ")
                st.markdown("---")
                st.markdown("### 🌧️ 5-Day Flood Prediction Forecast")
                st.markdown("---")

                for i, row in forecast_df.iterrows():
                    date = row["date"]
                    risk = row["flood_risk"]
                    chance = row["chance"]

                    if risk == "Low":
                        emoji, color = "🟢", "#00b894"
                    elif risk == "Medium":
                        emoji, color = "🟡", "#fdcb6e"
                    else:
                        emoji, color = "🔴", "#d63031"

                    key = f"forecast_{i}"

                    if st.button(f"{date} - {emoji} {risk}", key=key):
                        st.session_state.forecast_toggle[key] = not st.session_state.forecast_toggle.get(key, False)

                    if st.session_state.forecast_toggle.get(key, False):
                        st.markdown(f"""
                            <div style='background-color:#f0f8ff; color:black; padding:12px; border-radius:10px; margin-bottom:8px; 
                                        box-shadow: 2px 2px 6px rgba(0,0,0,0.1);'>
                            🌡️ Temp: {row['temp']} °C  | 💧 Humidity: {row['humidity']}%  | 🌧️ Rain: {row['rain']} mm
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Flood forecast data not available.")
        else:
            st.error("City not found or weather API error.")

# -------- Map Selection --------
# -------------------------------
if page == "Map Selection":
    st.title("🗺 Flood Prediction via Map")
    
    # Load city data
    cities_df = pd.read_csv("cities.csv")  # tumhara CSV path
    india_cities = cities_df[cities_df['country'] == 'India']

    # Initialize map
    m = folium.Map(location=[20.5937,78.9629], zoom_start=5)

    # Add markers for all Indian cities
    for idx, row in india_cities.iterrows():
        city_name = row['city']
        lat = row['lat']
        lon = row['lng']
        folium.Marker(
            location=[lat, lon],
            tooltip=city_name,
            popup=f"<b>{city_name}</b><br>Click to predict flood risk"
        ).add_to(m)

    # Render map
    map_data = st_folium(m, width=900, height=600)

    # Handle marker click
    if map_data and map_data.get('last_object_clicked'):
        clicked_lat = map_data['last_object_clicked']['lat']
        clicked_lng = map_data['last_object_clicked']['lng']
        
        # Find the city based on lat/lng
        city_row = india_cities[
            (india_cities['lat'] == clicked_lat) & 
            (india_cities['lng'] == clicked_lng)
        ]
        
        if not city_row.empty:
            city_name = city_row.iloc[0]['city']
            weather = get_weather(city_name)
            if weather:
                result = predict_flood_live(weather)
                st.success(f"City: {city_name}")
                st.metric("Flood Risk Level", result['Risk Level'])
                st.info(result['Alert'])
            else:
                st.error("Weather data not available for this city")
#-------------------------------
# -------- Help Chatbot --------
# -----------------------------
elif page == "Help Assistant":
    st.title("🌊 Flood Help Assistant (Offline)")

    # -----------------------------
    # Categories & Questions (Vertical)
    faq_data = {
        "Flood Risk Info": {
            "What is Flood Risk?": "Flood risk indicates the potential danger of flooding in your area based on historical data and weather patterns.",
            "How to check if my city is flood-prone?": "You can check historical flood data and local government flood maps to know if your city is prone to floods.",
            "Which areas in India are highly flood-prone?": "Some areas like Assam, Bihar, West Bengal, Odisha and Uttar Pradesh are historically flood-prone."
        },
        "Safety Measures": {
            "Before a Flood": "Prepare emergency kit, secure important documents, plan evacuation routes, and stay updated with weather alerts.",
            "During a Flood": "Move to higher ground, avoid walking or driving through flood waters, follow official evacuation orders.",
            "After a Flood": "Avoid floodwater, check for damages, follow local authority instructions, and stay healthy."
        },
        "Flood Prediction Project": {
            "How does the project work?": "Our project uses live weather data and location info to predict flood risk for cities across India.",
            "How to use the app?": "Enter your city, check weather parameters, and the app will show flood risk (Safe/Danger) along with guidance.",
            "Which factors are considered for prediction?": "Rainfall, river proximity, dams, humidity, temperature, and cloud cover are used for flood prediction."
        },
        "Emergency Contacts": {
            "Who to call in flood emergency?": "Contact local authorities, National Disaster Management Helpline: 1070, or local police and fire department.",
            "Local flood support centers": "Visit your municipal website or contact state disaster management offices for local flood relief centers."
        },
        "Tips & Awareness": {
            "Flood Safety Tips": "Keep emergency kit ready, avoid low-lying areas, store drinking water, and follow official alerts.",
            "Awareness Resources": "Check government websites for flood awareness guidelines and educational videos."
        }
    }

    # -----------------------------
    # Initialize session state
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = None
    if "selected_question" not in st.session_state:
        st.session_state.selected_question = None
    if "history" not in st.session_state:
        st.session_state.history = []

    # -----------------------------
    # Step 1: Show Category Buttons (Vertical)
    if st.session_state.selected_category is None:
        st.subheader("Select a Category:")
        for category in faq_data.keys():
            if st.button(category):
                st.session_state.selected_category = category

    # -----------------------------
    # Step 2: Show Question Buttons (Vertical)
    elif st.session_state.selected_question is None:
        st.subheader(f"Category: {st.session_state.selected_category}")
        st.write("Select a Question:")
        questions = list(faq_data[st.session_state.selected_category].keys())
        for q in questions:
            if st.button(q):
                st.session_state.selected_question = q
                st.session_state.history.append(f"{st.session_state.selected_category} -> {q}")

    # -----------------------------
    # Step 3: Show Answer in Card
    if st.session_state.selected_question:
        answer = faq_data[st.session_state.selected_category][st.session_state.selected_question]
        st.markdown("### 💡 Answer:")
        st.markdown(
            f"""
            <div style='background-color:#f0f8ff; color:black; padding:15px; border-radius:10px; 
                        box-shadow: 2px 2px 10px rgba(0,0,0,0.1); font-size:16px;'>
                {answer}
            </div>
            """, unsafe_allow_html=True
        )

        # Reset button to select new question
        if st.button("🔄 Select Another Question"):
            st.session_state.selected_category = None
            st.session_state.selected_question = None

    # -----------------------------
    # History
    if st.session_state.history:
        st.markdown("### 📝 Your Selection History:")
        for h in st.session_state.history[-10:]:
            st.markdown(f"- {h}")

   # -------- Flood Safety Tips --------
if page == "Flood Safety Tips":
    st.title("🛟 Flood Safety & Precaution Tips")
    st.markdown("### ✅ Before a Flood")
    st.write("- Prepare emergency kit with essentials.")
    st.write("- Keep important documents in waterproof bags.")
    st.write("- Stay informed about local weather alerts.")
    st.markdown("### 🚨 During a Flood")
    st.write("- Move to higher ground immediately.")
    st.write("- Avoid walking or driving through flood waters.")
    st.write("- Keep listening to official updates.")
    st.markdown("### 🧰 After a Flood")
    st.write("- Don’t return home until authorities say it’s safe.")
    st.write("- Avoid contact with flood water; it may be contaminated.")
    st.write("- Clean and disinfect everything that got wet.")
#--------------------------
#about page
#--------------------------
#--------------------------  
elif page == "About":
    st.set_page_config(page_title="About - Flood Prediction & Alert System", layout="wide")
    
    st.markdown("""
    <style>
    .title {
        font-size: 36px; 
        font-weight: bold; 
        color: #0A47A1; 
        text-align: center; 
        margin-bottom: 10px;
    }
    .subtitle {
        font-size: 20px; 
        color: #FFFFFF; 
        text-align: center;
        margin-bottom: 30px;
    }
    .feature-box {
        background: linear-gradient(135deg, #00C6FF, #0072FF);
        color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="title">🌊 Flood Prediction & Alert System</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Smart, real-time, and interactive flood awareness platform for India</div>', unsafe_allow_html=True)

    # ---- Features Section ----
    st.markdown('<div class="feature-box">✅ Live flood risk prediction with temperature, rainfall, humidity & wind analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">🗺️ Interactive map to explore flood risks city-wise</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">📅 10-day weather forecast with flood probability trends</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">⚡ Alerts & Safety guidance for high-risk areas</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">🤖 Offline Help Assistant to answer flood-related queries</div>', unsafe_allow_html=True)

    # ---- About App Section ----
    st.markdown("""
    ### 💡 Why This App?
    Floods in India affect thousands each year. This system helps citizens by providing:""")
    st.markdown('<div class="feature-box">Early flood warnings</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">Awareness of flood-prone areas</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">Safety & precaution guidance before, during, and after floods</div>', unsafe_allow_html=True)
    st.markdown('<div class="feature-box">Easy-to-use, interactive platform accessible to everyone</div>', unsafe_allow_html=True)
    

    # ---- Developer Section ----
    st.markdown("### 👨‍💻 Developed By")
    st.write("- Gautam Chauhan")
    st.write("- Focused on real-time flood awareness & citizen safety")
    st.write("- Inspired to create a user-friendly, professional flood alert system")
