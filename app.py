import os
import requests
import threading
import traceback
from datetime import datetime
from dotenv import load_dotenv
import customtkinter as ctk
from PIL import Image, ImageTk

try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except Exception:
    SPEECH_AVAILABLE = False

load_dotenv()

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
HISTORY_FILE = "history.txt"

WEATHER_ICON = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌧️", 55: "🌧️",
    56: "🌧️❄️", 57: "🌧️❄️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    66: "🌧️❄️", 67: "🌧️❄️",
    71: "❄️", 73: "❄️", 75: "❄️", 77: "❄️",
    80: "🌦️", 81: "🌦️", 82: "🌦️",
    85: "❄️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️"
}

WEATHER_TEXT = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Heavy Drizzle",
    56: "Freezing Drizzle",
    57: "Heavy Freezing Drizzle",
    61: "Light Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Light Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Rain Showers",
    81: "Moderate Rain Showers",
    82: "Heavy Rain Showers",
    85: "Light Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Hail",
    99: "Severe Thunderstorm"
}

def ensure_history_file():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8"):
            pass

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_to_history(city):
    history = load_history()
    if city in history:
        history.remove(city)
    history.insert(0, city)
    history = history[:30]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for item in history:
            f.write(item + "\n")

def geocode_city(city_name):
    try:
        resp = requests.get(GEOCODING_URL, params={"name": city_name, "count": 5}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return None
        best = results[0]
        for r in results:
            if r.get("name", "").lower() == city_name.lower():
                best = r
                break
        return {
            "latitude": best["latitude"],
            "longitude": best["longitude"],
            "timezone": best.get("timezone", "UTC"),
            "display_name": f"{best.get('name')}, {best.get('country','')}".strip(", ")
        }
    except Exception:
        traceback.print_exc()
        return None

def fetch_weather(lat, lon, timezone):
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "temperature_2m,weathercode",
            "daily": "temperature_2m_max,temperature_2m_min,weathercode,sunrise,sunset",
            "timezone": timezone
        }
        r = requests.get(WEATHER_URL, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        traceback.print_exc()
        return None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class WeatherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Weather Dashboard")
        self.geometry("1150x720")
        self.minsize(900,600)

        ensure_history_file()
        self.dark_mode = True

        self.header_frame = ctk.CTkFrame(self, corner_radius=12)
        self.header_frame.pack(fill="x", padx=16, pady=14)
        self.header_frame.grid_columnconfigure(3, weight=1)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Weather Dashboard",
                                        font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=5, sticky="w", padx=10, pady=(8,6))

        self.search_entry = ctk.CTkEntry(self.header_frame, placeholder_text="Enter city (e.g. Dhaka)", width=480)
        self.search_entry.grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self.search_entry.bind("<Return>", lambda e: self.on_search())

        self.voice_btn = ctk.CTkButton(self.header_frame, text="🎤", width=40, height=32,
                                       command=self.voice_input if SPEECH_AVAILABLE else self.voice_notavail)
        self.voice_btn.grid(row=1, column=1, padx=(6, 8))

        self.search_btn = ctk.CTkButton(self.header_frame, text="Search", width=110, command=self.on_search)
        self.search_btn.grid(row=1, column=2, padx=6)

        hist_values = load_history() or ["No history"]
        self.history_var = ctk.StringVar(value=hist_values[0])
        self.dropdown = ctk.CTkOptionMenu(self.header_frame, values=hist_values,
                                          variable=self.history_var, command=self.on_history_select)
        self.dropdown.grid(row=1, column=3, padx=10, sticky="e")

        self.mode_btn = ctk.CTkButton(self.header_frame, text="Dark / Light", width=120, command=self.toggle_mode)
        self.mode_btn.grid(row=1, column=4, padx=10)

        self.status_label = ctk.CTkLabel(self.header_frame, text="Ready", font=ctk.CTkFont(size=11))
        self.status_label.grid(row=2, column=0, columnspan=5, pady=(6,4), sticky="w", padx=10)

        self.current_card = ctk.CTkFrame(self, corner_radius=12)
        self.current_card.pack(fill="x", padx=16, pady=(6,12))

        self.location_label = ctk.CTkLabel(self.current_card, text="City, Country",
                                           font=ctk.CTkFont(size=18, weight="bold"))
        self.location_label.pack(pady=(12,2))

        self.temp_label = ctk.CTkLabel(self.current_card, text="--°C",
                                       font=ctk.CTkFont(size=42, weight="bold"))
        self.temp_label.pack(pady=(4,8))

        self.cond_label = ctk.CTkLabel(self.current_card, text="Condition",
                                        font=ctk.CTkFont(size=16, weight="bold"))
        self.cond_label.pack(pady=(2,2))

        self.time_label = ctk.CTkLabel(self.current_card, text="", font=ctk.CTkFont(size=15))
        self.time_label.pack(pady=(2,2))

        self.sun_label = ctk.CTkLabel(self.current_card, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.sun_label.pack(pady=(6,12))

        self.hourly_title = ctk.CTkLabel(self, text="Next 24 Hours (2h intervals)",
                                         font=ctk.CTkFont(size=16, weight="bold"))
        self.hourly_title.pack(anchor="w", padx=24, pady=(4,6))

        self.hourly_frame = ctk.CTkFrame(self, corner_radius=12)
        self.hourly_frame.pack(fill="x", padx=16, pady=(0,12))
        self.hourly_frame.grid_columnconfigure(tuple(range(12)), weight=1)

        self.hourly_cards = []
        for i in range(12):
            card = ctk.CTkFrame(self.hourly_frame, corner_radius=10, fg_color=None)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            t_lbl = ctk.CTkLabel(card, text="--:--", font=ctk.CTkFont(size=13))
            t_lbl.pack(pady=(8,2))
            cond_line = ctk.CTkLabel(card, text=" ", font=ctk.CTkFont(size=12, weight="bold"))
            cond_line.pack()
            tp_lbl = ctk.CTkLabel(card, text="--°C", font=ctk.CTkFont(size=12, weight="bold"))
            tp_lbl.pack(pady=(6,8))
            self.hourly_cards.append((card, t_lbl, cond_line, tp_lbl))

        self.forecast_title = ctk.CTkLabel(self, text="7-Day Forecast",
                                           font=ctk.CTkFont(size=16, weight="bold"))
        self.forecast_title.pack(anchor="w", padx=24, pady=(6,6))

        self.forecast_frame = ctk.CTkFrame(self, corner_radius=12)
        self.forecast_frame.pack(fill="x", padx=16, pady=(0,16))
        self.forecast_frame.grid_columnconfigure(tuple(range(7)), weight=1)

        self.forecast_cards = []
        for i in range(7):
            card = ctk.CTkFrame(self.forecast_frame, corner_radius=10, fg_color=None)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            d_lbl = ctk.CTkLabel(card, text="Day", font=ctk.CTkFont(size=13))
            d_lbl.pack(pady=(8,2))
            cond_line = ctk.CTkLabel(card, text=" ", font=ctk.CTkFont(size=12, weight="bold"))
            cond_line.pack()
            tp_lbl = ctk.CTkLabel(card, text="--° / --°", font=ctk.CTkFont(size=12))
            tp_lbl.pack(pady=(6,10))
            self.forecast_cards.append((card, d_lbl, cond_line, tp_lbl))

        self.update_history_dropdown()

    def set_status(self, txt):
        self.status_label.configure(text=txt)

    def update_history_dropdown(self):
        hist = load_history()
        if not hist:
            self.dropdown.configure(values=["No history"])
            self.history_var.set("No history")
        else:
            self.dropdown.configure(values=hist)
            self.history_var.set(hist[0])

    def on_history_select(self, value):
        if value != "No history":
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, value)
            self.on_search()

    def toggle_mode(self):
        if self.dark_mode:
            ctk.set_appearance_mode("light")
            self.dark_mode = False
        else:
            ctk.set_appearance_mode("dark")
            self.dark_mode = True

    def voice_notavail(self):
        self.set_status("SpeechRecognition not installed")

    def voice_input(self):
        if not SPEECH_AVAILABLE:
            self.set_status("SpeechRecognition not installed")
            return

        def listen():
            r = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    self.set_status("Listening...")
                    audio = r.listen(source, timeout=5)
                    text = r.recognize_google(audio)
                    self.search_entry.delete(0, "end")
                    self.search_entry.insert(0, text)
                    self.set_status("Voice input done")
                    self.on_search()
            except Exception:
                self.set_status("Voice failed")

        threading.Thread(target=listen, daemon=True).start()

    def on_search(self, event=None):
        city = self.search_entry.get().strip()
        if not city:
            self.set_status("Enter a city name")
            return

        self.search_btn.configure(state="disabled")
        self.set_status("Searching...")
        threading.Thread(target=self.search_and_update, args=(city,), daemon=True).start()

    def search_and_update(self, city):
        try:
            geo = geocode_city(city)
            if not geo:
                self.after(0, lambda: self.set_status("City not found"))
                return

            lat = geo["latitude"]
            lon = geo["longitude"]
            timezone = geo.get("timezone", "UTC")
            display = geo["display_name"]

            self.after(0, lambda: self.set_status("Fetching weather..."))
            data = fetch_weather(lat, lon, timezone)
            if not data:
                self.after(0, lambda: self.set_status("Weather fetch error"))
                return

            save_to_history(city)
            self.after(0, self.update_history_dropdown)
            self.after(0, lambda: self.update_ui(data, display))
            self.after(0, lambda: self.set_status("Updated"))
        except Exception:
            traceback.print_exc()
            self.after(0, lambda: self.set_status("Failed"))
        finally:
            self.after(0, lambda: self.search_btn.configure(state="normal"))

    def update_ui(self, data, display_name):
        try:
            cw = data.get("current_weather", {})
            hourly = data.get("hourly", {})
            daily = data.get("daily", {})

            temp = cw.get("temperature", "--")
            code = cw.get("weathercode")
            emoji = WEATHER_ICON.get(code, "❓")
            condition_text = WEATHER_TEXT.get(code, "Unknown")

            self.location_label.configure(text=display_name)
            self.temp_label.configure(text=f"{temp}°C")
            self.cond_label.configure(text=f"{emoji}  {condition_text}")

            raw_time = cw.get("time", "")
            if raw_time:
                try:
                    dt = datetime.fromisoformat(raw_time)
                    self.time_label.configure(text=dt.strftime("%Y-%m-%d %H:%M"))
                except:
                    self.time_label.configure(text=raw_time.replace("T", " "))
            else:
                self.time_label.configure(text="")

            sr_list = daily.get("sunrise", [])
            ss_list = daily.get("sunset", [])
            sunrise = sr_list[0].split("T")[-1] if sr_list else ""
            sunset = ss_list[0].split("T")[-1] if ss_list else ""
            if sunrise or sunset:
                self.sun_label.configure(text=f"Sunrise: {sunrise} | Sunset: {sunset}")
            else:
                self.sun_label.configure(text="")

            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weathercode", [])

            for i in range(12):
                index = i * 2
                card, t_lbl, cond_line, tp_lbl = self.hourly_cards[i]
                if index < len(times):
                    t_txt = times[index].split("T")[-1]
                    t_lbl.configure(text=t_txt)
                    tp_lbl.configure(text=f"{temps[index]}°C" if index < len(temps) else "--°C")
                    ccode = codes[index] if index < len(codes) else None
                    emoji_h = WEATHER_ICON.get(ccode, "❓")
                    text_h = WEATHER_TEXT.get(ccode, "")
                    cond_line.configure(text=f"{emoji_h} {text_h}".strip())
                else:
                    t_lbl.configure(text="--:--")
                    cond_line.configure(text=" ")
                    tp_lbl.configure(text="--°C")

            d_times = daily.get("time", [])
            d_max = daily.get("temperature_2m_max", [])
            d_min = daily.get("temperature_2m_min", [])
            d_codes = daily.get("weathercode", [])

            for i in range(7):
                card, day_lbl, cond_line, tp_lbl = self.forecast_cards[i]
                if i < len(d_times):
                    day_lbl.configure(text=d_times[i])
                    max_txt = f"{d_max[i]}°" if i < len(d_max) else "--°"
                    min_txt = f"{d_min[i]}°" if i < len(d_min) else "--°"
                    tp_lbl.configure(text=f"{max_txt} / {min_txt}")
                    dcode = d_codes[i] if i < len(d_codes) else None
                    emoji_d = WEATHER_ICON.get(dcode, "❓")
                    text_d = WEATHER_TEXT.get(dcode, "")
                    cond_line.configure(text=f"{emoji_d} {text_d}".strip())
                else:
                    day_lbl.configure(text="Day")
                    cond_line.configure(text=" ")
                    tp_lbl.configure(text="--° / --°")
        except Exception:
            traceback.print_exc()
            self.set_status("UI update error")

if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()
