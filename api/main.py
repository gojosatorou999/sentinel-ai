import os
import csv
from datetime import datetime
import pytz
from flask import Flask, request, render_template, redirect, url_for, session, flash
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather

app = Flask(__name__)
app.secret_key = os.urandom(24)

TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
ADMIN_USER = os.environ.get('ADMIN_USERNAME')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD')

client = None
if TWILIO_SID and TWILIO_TOKEN:
    client = Client(TWILIO_SID, TWILIO_TOKEN)

call_data = {}
all_reports = []
CSV_FILE = 'reports.csv'

if os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            report = {
                'timestamp': row['Timestamp'],
                'phone': row['Phone'],
                'type': row['Hazard Type'],
                'location': row['Location'],
                'severity': row['Severity'],
                'desc': row['Description']
            }
            all_reports.insert(0, report)
else:
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Phone', 'Hazard Type', 'Location', 'Severity', 'Description'])

# --- LANGUAGE CONFIG ---

LANG_CODE = {
    'en': 'en-IN',
    'hi': 'hi-IN',
    'te': 'te-IN'
}

# All prompts in English, Hindi (Devanagari), Telugu (Telugu script)
PROMPTS = {
    'en': {
        'welcome': "Welcome to the Coastal Alert Reporting System. Are you calling to report a hazard? Please say Yes or No.",
        'no_input_welcome': "I didn't hear you. Say Yes to report a hazard, or No to exit.",
        'not_reporting': "Thank you for checking in. Goodbye.",
        'unclear': "Please say Yes to report, or No to exit.",
        'ask_type': "What type of hazard is it? You can say Storms, Sludge, Abnormal Tides, or Others.",
        'no_input_type': "Please say Storms, Sludge, Abnormal Tides, or Others.",
        'ask_description': "Please briefly describe the hazard. What is happening?",
        'no_input_description': "Please describe the hazard.",
        'ask_location': "Where is this located? For example, Vizag Beach or Charminar.",
        'no_input_location': "Please tell me the location of the hazard.",
        'ask_severity': "How severe is it? Say Extreme, Moderate, or Light.",
        'no_input_severity': "Please say Extreme, Moderate, or Light.",
        'confirm': "Report summary: {hazard_type} at {location}, severity is {severity}. Say Yes to submit, or No to start over.",
        'submitted': "Your report has been submitted. Stay safe.",
        'start_over': "Let's try again from the beginning.",
        'no_input_lang': "Please say English, Telugu, or Hindi."
    },
    'hi': {
        'welcome': "क्या आप कोई खतरा रिपोर्ट करने के लिए कॉल कर रहे हैं? कृपया हाँ या नहीं कहें।",
        'no_input_welcome': "मुझे आपकी आवाज़ सुनाई नहीं दी। खतरा रिपोर्ट करने के लिए हाँ कहें, या बाहर जाने के लिए नहीं कहें।",
        'not_reporting': "संपर्क करने के लिए धन्यवाद। अलविदा।",
        'unclear': "कृपया रिपोर्ट करने के लिए हाँ कहें, या बाहर जाने के लिए नहीं कहें।",
        'ask_type': "यह किस प्रकार का खतरा है? आप तूफ़ान, कीचड़, असामान्य ज्वार, या अन्य कह सकते हैं।",
        'no_input_type': "कृपया तूफ़ान, कीचड़, असामान्य ज्वार, या अन्य कहें।",
        'ask_description': "कृपया खतरे का संक्षेप में वर्णन करें। क्या हो रहा है?",
        'no_input_description': "कृपया खतरे का वर्णन करें।",
        'ask_location': "यह कहाँ स्थित है? उदाहरण के लिए, विज़ाग बीच या चारमीनार।",
        'no_input_location': "कृपया खतरे की जगह बताएं।",
        'ask_severity': "यह कितना गंभीर है? अत्यंत, मध्यम, या हल्का कहें।",
        'no_input_severity': "कृपया अत्यंत, मध्यम, या हल्का कहें।",
        'confirm': "रिपोर्ट सारांश: {location} में {hazard_type}, गंभीरता {severity} है। जमा करने के लिए हाँ कहें, या फिर से शुरू करने के लिए नहीं कहें।",
        'submitted': "आपकी रिपोर्ट जमा हो गई है। सुरक्षित रहें।",
        'start_over': "चलिए शुरू से फिर कोशिश करते हैं।",
        'no_input_lang': "कृपया English, Telugu, या Hindi कहें।"
    },
    'te': {
        'welcome': "మీరు ప్రమాదాన్ని నివేదించడానికి కాల్ చేస్తున్నారా? దయచేసి అవును లేదా కాదు అని చెప్పండి.",
        'no_input_welcome': "మీరు చెప్పింది వినలేదు. ప్రమాదాన్ని నివేదించడానికి అవును అనండి, లేదా బయటకు వెళ్ళడానికి కాదు అనండి.",
        'not_reporting': "సంప్రదించినందుకు ధన్యవాదాలు. వీడ్కోలు.",
        'unclear': "దయచేసి నివేదించడానికి అవును అనండి, లేదా బయటకు వెళ్ళడానికి కాదు అనండి.",
        'ask_type': "ఇది ఏ రకమైన ప్రమాదం? మీరు తుఫాను, బురద, అసాధారణ అలలు, లేదా ఇతర అని చెప్పవచ్చు.",
        'no_input_type': "దయచేసి తుఫాను, బురద, అసాధారణ అలలు, లేదా ఇతర అని చెప్పండి.",
        'ask_description': "దయచేసి ప్రమాదాన్ని క్లుప్తంగా వివరించండి. ఏం జరుగుతోంది?",
        'no_input_description': "దయచేసి ప్రమాదాన్ని వివరించండి.",
        'ask_location': "ఇది ఎక్కడ ఉంది? ఉదాహరణకు, విజాగ్ బీచ్ లేదా చార్మినార్.",
        'no_input_location': "దయచేసి ప్రమాదం జరిగిన స్థలాన్ని చెప్పండి.",
        'ask_severity': "ఇది ఎంత తీవ్రంగా ఉంది? అత్యంత తీవ్రమైనది, మధ్యస్థం, లేదా తేలికపాటి అని చెప్పండి.",
        'no_input_severity': "దయచేసి అత్యంత తీవ్రమైనది, మధ్యస్థం, లేదా తేలికపాటి అని చెప్పండి.",
        'confirm': "నివేదిక సారాంశం: {location} లో {hazard_type}, తీవ్రత {severity}. సమర్పించడానికి అవును అనండి, లేదా మళ్ళీ ప్రారంభించడానికి కాదు అనండి.",
        'submitted': "మీ నివేదిక సమర్పించబడింది. సురక్షితంగా ఉండండి.",
        'start_over': "మళ్ళీ మొదటి నుండి ప్రయత్నిద్దాం.",
        'no_input_lang': "దయచేసి English, Telugu, లేదా Hindi అనండి."
    }
}

YES_WORDS = ['yes', 'yeah', 'sure', 'correct', 'submit', 'ok', 'okay',
             'haan', 'ha', 'ji haan', 'haa',
             'avunu', 'avu', 'avun',
             'हाँ', 'हां', 'అవును']

NO_WORDS = ['no', 'nope', 'nahi', 'nahin', 'na',
            'kaadu', 'ledu', 'वद्दु',
            'నహీ', 'నో',
            'नहीं', 'కాదు']

def get_lang(call_sid):
    return call_data.get(call_sid, {}).get('lang', 'en')

def get_prompt(call_sid, key, **kwargs):
    lang = get_lang(call_sid)
    prompt = PROMPTS[lang][key]
    if kwargs:
        prompt = prompt.format(**kwargs)
    return prompt

def get_lang_code(call_sid):
    return LANG_CODE[get_lang(call_sid)]

def get_timestamp():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S %Z')

def save_report_to_csv(data):
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

def log_conversation(call_sid, actor, message):
    if call_sid in call_data:
        call_data[call_sid]['conversation'].append(f"{actor}: {message}")

# --- PUBLIC ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/initiate_call', methods=['POST'])
def initiate_call():
    user_number = request.form.get('phone_number')
    if not client:
        return {"status": "error", "message": "Twilio credentials not configured."}
    try:
        base_url = request.host_url.rstrip('/')
        call = client.calls.create(
            to=str(user_number),
            from_=str(TWILIO_NUMBER),
            url=f"{base_url}/voice/select_language"
        )
        call_data[call.sid] = {'phone': user_number, 'conversation': [], 'lang': 'en'}
        return {"status": "success", "message": "Call initiated! Help is on the way."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- ADMIN ROUTES ---

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/login', methods=['POST'])
def login():
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
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('reports.html', reports=all_reports)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/reports/download')
def download_reports():
    try:
        with open(CSV_FILE, 'r') as f:
            return f.read(), 200, {
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache'
            }
    except Exception as e:
        return str(e), 500

# --- VOICE LOGIC ---

@app.route('/voice/select_language', methods=['GET', 'POST'])
def select_language():
    resp = VoiceResponse()
    # Barge-in enabled: <Say> inside <Gather> allows caller to interrupt at any time
    gather = Gather(input='speech', action='/voice/handle_language', timeout=5, speechTimeout='auto')
    gather.say("For English, please say English.", language='en-IN')
    gather.say("తెలుగు కోసం, తెలుగు అనండి.", language='te-IN')
    gather.say("हिंदी के लिए, हिंदी बोलिए।", language='hi-IN')
    resp.append(gather)
    resp.say("Please say English, Telugu, or Hindi.", language='en-IN')
    resp.redirect('/voice/select_language')
    return str(resp)

@app.route('/voice/handle_language', methods=['POST'])
def handle_language():
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '').lower().strip()

    lang = 'en'
    if any(w in speech for w in ['telugu', 'తెలుగు', 'telgu', 'tel']):
        lang = 'te'
    elif any(w in speech for w in ['hindi', 'हिंदी', 'hind', 'hindi']):
        lang = 'hi'
    elif any(w in speech for w in ['english', 'inglish', 'eng', 'ingli']):
        lang = 'en'

    if call_sid not in call_data:
        call_data[call_sid] = {'phone': 'unknown', 'conversation': []}
    call_data[call_sid]['lang'] = lang

    resp = VoiceResponse()
    resp.redirect('/voice/welcome')
    return str(resp)

@app.route('/voice/welcome', methods=['GET', 'POST'])
def welcome():
    resp = VoiceResponse()
    call_sid = request.values.get('CallSid')
    lc = get_lang_code(call_sid)

    gather = Gather(input='speech', action='/voice/handle_welcome', timeout=3, speechTimeout='auto')
    gather.say(get_prompt(call_sid, 'welcome'), language=lc)
    resp.append(gather)

    resp.say(get_prompt(call_sid, 'no_input_welcome'), language=lc)
    resp.redirect('/voice/welcome')
    log_conversation(call_sid, "Bot", "Asked if reporting a hazard")
    return str(resp)

@app.route('/voice/handle_welcome', methods=['POST'])
def handle_welcome():
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '').lower()
    log_conversation(call_sid, "User", speech)
    lc = get_lang_code(call_sid)

    resp = VoiceResponse()
    if any(w in speech for w in YES_WORDS):
        resp.redirect('/voice/ask_hazard_type')
    elif any(w in speech for w in NO_WORDS):
        resp.say(get_prompt(call_sid, 'not_reporting'), language=lc)
        resp.hangup()
    else:
        resp.say(get_prompt(call_sid, 'unclear'), language=lc)
        resp.redirect('/voice/welcome')
    return str(resp)

@app.route('/voice/ask_hazard_type', methods=['GET', 'POST'])
def ask_hazard_type():
    resp = VoiceResponse()
    call_sid = request.values.get('CallSid')
    lc = get_lang_code(call_sid)

    gather = Gather(input='speech', action='/voice/handle_hazard_type', timeout=3, speechTimeout='auto')
    gather.say(get_prompt(call_sid, 'ask_type'), language=lc)
    resp.append(gather)

    resp.say(get_prompt(call_sid, 'no_input_type'), language=lc)
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
    resp.redirect('/voice/ask_field/description')
    return str(resp)

FIELD_CONFIG = {
    'description': {
        'ask_key': 'ask_description',
        'no_input_key': 'no_input_description',
        'store_key': 'desc',
        'next': '/voice/ask_field/location'
    },
    'location': {
        'ask_key': 'ask_location',
        'no_input_key': 'no_input_location',
        'store_key': 'location',
        'next': '/voice/ask_field/severity'
    },
    'severity': {
        'ask_key': 'ask_severity',
        'no_input_key': 'no_input_severity',
        'store_key': 'severity',
        'next': '/voice/confirm_report'
    }
}

@app.route('/voice/ask_field/<field>', methods=['GET', 'POST'])
def ask_field(field):
    resp = VoiceResponse()
    call_sid = request.values.get('CallSid')
    lc = get_lang_code(call_sid)
    cfg = FIELD_CONFIG.get(field, FIELD_CONFIG['description'])

    gather = Gather(input='speech', action=f'/voice/handle_field/{field}', timeout=3, speechTimeout='auto')
    gather.say(get_prompt(call_sid, cfg['ask_key']), language=lc)
    resp.append(gather)

    resp.say(get_prompt(call_sid, cfg['no_input_key']), language=lc)
    resp.redirect(f'/voice/ask_field/{field}')
    return str(resp)

@app.route('/voice/handle_field/<field>', methods=['POST'])
def handle_field(field):
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '')
    cfg = FIELD_CONFIG.get(field, FIELD_CONFIG['description'])

    if call_sid in call_data:
        call_data[call_sid][cfg['store_key']] = speech
    log_conversation(call_sid, "User", speech)

    resp = VoiceResponse()
    resp.redirect(cfg['next'])
    return str(resp)

@app.route('/voice/confirm_report', methods=['GET', 'POST'])
def confirm_report():
    call_sid = request.values.get('CallSid')
    data = call_data.get(call_sid, {})
    lc = get_lang_code(call_sid)

    summary = get_prompt(call_sid, 'confirm',
        hazard_type=data.get('type', ''),
        location=data.get('location', ''),
        severity=data.get('severity', '')
    )

    resp = VoiceResponse()
    gather = Gather(input='speech', action='/voice/process_confirmation', timeout=3, speechTimeout='auto')
    gather.say(summary, language=lc)
    resp.append(gather)

    log_conversation(call_sid, "Bot", "Confirming report")
    resp.redirect('/voice/confirm_report')
    return str(resp)

@app.route('/voice/process_confirmation', methods=['POST'])
def process_confirmation():
    call_sid = request.values.get('CallSid')
    speech = request.values.get('SpeechResult', '').lower()
    lc = get_lang_code(call_sid)
    resp = VoiceResponse()

    if any(w in speech for w in YES_WORDS):
        resp.say(get_prompt(call_sid, 'submitted'), language=lc)
        resp.hangup()

        if call_sid in call_data:
            final_data = call_data[call_sid]
            final_data['timestamp'] = get_timestamp()
            save_report_to_csv(final_data)
            final_data['conversation_log'] = " | ".join(final_data['conversation'])
            all_reports.insert(0, final_data)
            del call_data[call_sid]
    else:
        resp.say(get_prompt(call_sid, 'start_over'), language=lc)
        resp.redirect('/voice/welcome')

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
