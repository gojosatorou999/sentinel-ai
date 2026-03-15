import os
import csv
from datetime import datetime
import pytz
from flask import Flask, request, render_template, redirect, url_for, session, flash
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)
app.secret_key = os.urandom(24) # Required for session management

# --- CONFIGURATION ---
TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
ADMIN_USER = os.environ.get('ADMIN_USERNAME')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD')

# Initialize Twilio client only if credentials are present
client = None
if TWILIO_SID and TWILIO_TOKEN:
    client = Client(TWILIO_SID, TWILIO_TOKEN)

# In-memory storage for ongoing calls and full report history for the UI
call_data = {}
all_reports = []
CSV_FILE = 'reports.csv'

# Load existing reports from CSV into memory on startup
if os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Reconstruct the dictionary format expected by the template
            report = {
                'timestamp': row['Timestamp'],
                'phone': row['Phone'],
                'type': row['Hazard Type'],
                'location': row['Location'],
                'severity': row['Severity'],
                'desc': row['Description']
            }
            all_reports.insert(0, report)

def get_timestamp():
    """Returns current timestamp in IST."""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S %Z')

def save_report_to_csv(data):
    """Saves report data to CSV file."""
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            data['timestamp'],
            data['phone'],
            data.get('type', 'N/A'),
            data.get('location', 'N/A'),
            data.get('severity', 'N/A'),
            data.get('desc', 'N/A')
        ])

# --- PUBLIC ROUTES ---

@app.route('/')
def index():
    """Renders the main calling page."""
    return render_template('index.html')

@app.route('/initiate_call', methods=['POST'])
def initiate_call():
    """Initiates the Twilio call."""
    user_number = request.form.get('phone_number')
    if not client:
        return {"status": "error", "message": "Twilio credentials not configured."}
    try:
        base_url = request.host_url.rstrip('/')
        # Cast to str to satisfy LSP since we check client existence above
        call = client.calls.create(
            to=str(user_number),
            from_=str(TWILIO_NUMBER),
            url=f"{base_url}/voice/welcome"
        )
        # Initialize call data with phone number
        call_data[call.sid] = {'phone': user_number, 'conversation': []}
        return {"status": "success", "message": "Call initiated! Help is on the way."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- ADMIN ROUTES ---

@app.route('/admin_login')
def admin_login():
    """Renders the admin login page."""
    return render_template('admin_login.html')

@app.route('/login', methods=['POST'])
def login():
    """Handles admin login authentication."""
    username = request.form.get('username')
    password = request.form.get('password')
    if username == ADMIN_USER and password == ADMIN_PASS:
        session['logged_in'] = True
        return redirect(url_for('reports'))
    else:
        flash('Invalid Username or Password')
        return redirect(url_for('admin_login'))

@app.route('/reports')
def reports():
    """Renders the reports page (secured)."""
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('reports.html', reports=all_reports)

@app.route('/logout')
def logout():
    """Logs out the admin."""
    session.pop('logged_in', None)
    return redirect(url_for('index'))

# --- VOICE LOGIC (IVR) ---

def log_conversation(call_sid, actor, message):
    """Helper to log the conversation."""
    if call_sid in call_data:
        call_data[call_sid]['conversation'].append(f"{actor}: {message}")

@app.route('/voice/welcome', methods=['GET', 'POST'])
def welcome():
    resp = VoiceResponse()
    call_sid = request.values.get('CallSid')

    gather = Gather(input='speech', action='/voice/handle_welcome', timeout=4)
    gather.say("Welcome to the Coastal Alert Reporting System. Are you calling to report a hazard? Please say Yes or No.")
    resp.append(gather)

    resp.say("I didn't hear you. Are you reporting a hazard? Say Yes or No.")
    resp.redirect('/voice/welcome')

    log_conversation(call_sid, "Bot", "Welcome... report a hazard?")
    return str(resp)

@app.route('/voice/handle_welcome', methods=['POST'])
def handle_welcome():
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '').lower()
    log_conversation(call_sid, "User", speech)

    resp = VoiceResponse()
    if any(word in speech for word in ['yes', 'yeah', 'sure']):
        resp.redirect('/voice/ask_hazard_type')
    elif 'no' in speech:
        resp.say("Thank you for checking in. Goodbye.")
        resp.hangup()
    else:
        resp.say("I didn't catch that. Please say Yes to report, or No to exit.")
        resp.redirect('/voice/welcome')
    return str(resp)

@app.route('/voice/ask_hazard_type', methods=['GET', 'POST'])
def ask_hazard_type():
    resp = VoiceResponse()
    gather = Gather(input='speech', action='/voice/handle_hazard_type', timeout=5)
    gather.say("What type of hazard is it? You can say Storms, Sludge, Abnormal Tides, or Others.")
    resp.append(gather)

    resp.say("Sorry, I am listening. Is it a Storm, Sludge, or something else?")
    resp.redirect('/voice/ask_hazard_type')
    return str(resp)

@app.route('/voice/handle_hazard_type', methods=['POST'])
def handle_hazard_type():
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '')
    if call_sid in call_data:
        call_data[call_sid]['type'] = speech
    log_conversation(call_sid, "User", speech)

    resp = VoiceResponse()
    resp.redirect('/voice/ask_description')
    return str(resp)

# ... (Similar handlers for description, location, severity) ...
# For brevity, I will combine them into a generic handler pattern below

@app.route('/voice/ask_<field>', methods=['GET', 'POST'])
def ask_field(field):
    prompts = {
        'description': "Please briefly describe the hazard. What is happening?",
        'location': "Where is this located? For example, Vizag Beach or Charminar.",
        'severity': "How severe is it? Extreme, Moderate, or Light?"
    }
    resp = VoiceResponse()
    gather = Gather(input='speech', action=f'/voice/handle_{field}', timeout=6)
    gather.say(prompts[field])
    resp.append(gather)
    resp.redirect(f'/voice/ask_{field}')
    return str(resp)

@app.route('/voice/handle_<field>', methods=['POST'])
def handle_field(field):
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '')

    field_map = {'description': 'desc', 'location': 'location', 'severity': 'severity'}
    data_key = field_map[field]

    if call_sid in call_data:
        call_data[call_sid][data_key] = speech
    log_conversation(call_sid, "User", speech)

    next_step = {
        'description': '/voice/ask_location',
        'location': '/voice/ask_severity',
        'severity': '/voice/confirm_report'
    }
    resp = VoiceResponse()
    resp.redirect(next_step[field])
    return str(resp)


@app.route('/voice/confirm_report', methods=['GET', 'POST'])
def confirm_report():
    call_sid = request.values.get('CallSid')
    data = call_data.get(call_sid, {})
    summary = f"I have a report for {data.get('type')} at {data.get('location')}, severity is {data.get('severity')}."

    resp = VoiceResponse()
    gather = Gather(input='speech', action='/voice/process_confirmation', timeout=5)
    gather.say(f"{summary} Say Yes to submit, or No to start over.")
    resp.append(gather)

    log_conversation(call_sid, "Bot", f"Confirming: {summary}")
    resp.redirect('/voice/confirm_report')
    return str(resp)

@app.route('/voice/process_confirmation', methods=['POST'])
def process_confirmation():
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '').lower()
    resp = VoiceResponse()

    if any(word in speech for word in ['yes', 'correct', 'submit']):
        resp.say("Your report has been submitted. Stay safe.")
        resp.hangup()

        # --- SAVE REPORT DATA ---
        if call_sid in call_data:
            final_data = call_data[call_sid]
            final_data['timestamp'] = get_timestamp()

            # 1. Save to CSV (without conversation)
            save_report_to_csv(final_data)

            # 2. Save to in-memory list for UI (with conversation)
            # Convert list to string for easier display
            final_data['conversation_log'] = " | ".join(final_data['conversation'])
            all_reports.insert(0, final_data) # Add to beginning of list

            del call_data[call_sid] # Clean up temp data

    else:
        resp.say("Let's try again from the beginning.")
        resp.redirect('/voice/welcome')

    return str(resp)

@app.route('/reports/download')
def download_reports():
    """Allows viewing the reports as a direct CSV stream."""
    try:
        with open(CSV_FILE, 'r') as f:
            return f.read(), 200, {
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache'
            }
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    # Use environment variable for port or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 to make it accessible outside the container
    app.run(host='0.0.0.0', port=port)