import ast
import hashlib
import os
from io import BytesIO

import psycopg2
from dotenv import load_dotenv
from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app import app
from reader import (
    ms_to_time,
    read_card,
    read_txt,
    time_to_ms,
    upload_times,
    write_card,
)

ALLOWED_EXTENSIONS = {'bin', 'crd'}
app.jinja_env.globals.update(len=len)
app.jinja_env.globals.update(str=str)
app.jinja_env.globals.update(int=int)
app.config['SECRET_KEY'] = 'super cool secret key'

load_dotenv()

def fix_underscore(value):
    return value.replace(" ", "_")
app.jinja_env.globals.update(replace=fix_underscore)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_file(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '' or not file.filename:
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            file_content = file.read()
            header = b'\x03\x36\x00\x01'
            if file_content[:4] != header:
                return redirect(request.url)
            hashed_filename = hashlib.sha256(file_content).hexdigest() + '.bin'
            session[hashed_filename] = file_content
            return redirect(url_for('edit_file', name=hashed_filename))
    return render_template('index.html')

@app.route('/card/<name>')
def edit_file(name):
    file_content = session[name]
    card = read_card(BytesIO(file_content))
    static_data = []
    static_data.append(read_txt('app/static/prefectures.txt'))
    static_data.append(read_txt('app/static/avatar_gender.txt'))
    static_data.append(read_txt('app/static/bgm_volume.txt'))
    static_data.append(read_txt('app/static/make.txt'))
    static_data.append(read_txt('app/static/car_prefectures.txt'))
    static_data.append(read_txt('app/static/car_hirigana.txt'))
    static_data.append(read_txt('app/static/courses.txt'))
    static_data.append(read_txt('app/static/cup.txt'))
    static_data.append(read_txt('app/static/tachometer.txt'))
    static_data.append(read_txt('app/static/aura.txt'))
    static_data.append(read_txt('app/static/class.txt'))
    static_data.append(read_txt('app/static/titles.txt'))
    allcars = {"Toyota": ["TRUENO GT-APEX (AE86)", "LEVIN GT-APEX (AE86)", "LEVIN SR (AE85)", "86 GT (ZN6)", "ALTEZZA RS200 (SXE10)", "MR-S (ZZW30)", "MR2 G-Limited (SW20)", "SUPRA RZ (JZA80)", "PRIUS (ZVW30)", "SPRINTER TRUENO 2door GT-APEX (AE86)", "CELICA GT-FOUR (ST205)"],
      "Nissan": ["SKYLINE GT-R (BNR32)", "SKYLINE GT-R (BNR34)", "SILVIA K's (S13)", "Silvia Q's (S14)", "Silvia spec-R (S15)", "180SX TYPE II (RPS13)", "FAIRLADY Z (Z33)", "GT-R NISMO (R35)", "GT-R (R35)", "SKYLINE 25GT TURBO (ER34)"],
      "Honda": ["Civic SiR・II (EG6)", "CIVIC TYPE R (EK9)", "INTEGRA TYPE R (DC2)", "S2000 (AP1)", "NSX (NA1)"],
      "Mazda": ["RX-7 ∞III (FC3S)", "RX-7 Type R (FD3S)", "RX-7 Type RS (FD3S)", "RX-8 Type S (SE3P)", "ROADSTER (NA6CE)", "ROADSTER RS (NB8C)"],
      "Subaru": ["IMPREZA STi Ver.V (GC8)", "IMPREZA STi (GDBA)", "IMPREZA STI (GDBF)", "BRZ S (ZC6)"],
      "Mitsubishi": ["LANCER Evolution III (CE9A)", "LANCER EVOLUTION IV (CN9A)", "LANCER Evolution VII (CT9A)", "LANCER Evolution IX (CT9A)", "LANCER EVOLUTION X (CZ4A)", "LANCER GSR EVOLUTION VI T.M.EDITION (CP9A)", "LANCER RS EVOLUTION V (CP9A)"],
      "Suzuki": ["Cappuccino (EA11R)"],
      "Initial D": ["SILEIGHTY", "TRUENO 2door GT-APEX (AE86)"],
      "Complete": ["G-FORCE SUPRA (JZA80-kai)", "MONSTER CIVIC R (EK9)", "S2000 GT1 (AP1)", "RE Amemiya Genki-7 (FD3S)", "NSX-R GT (NA2)", "ROADSTER C-SPEC (NA8C Kai)"]
      }
    return render_template('card.html', title='Home', card=card, name=name, data=static_data, allcars=allcars)

@app.route('/download/<name>', methods=["GET", "POST"])
def download(name):
    file_content = session[name]
    card = read_card(BytesIO(file_content))
    for key in card:
        form_value = request.form.get(f"key_{key}")
        if form_value is not None:
            card[key] = form_value
    new_data = BytesIO(session[name])
    user_id = card["User ID"]
    times = card["Courses"]
    username = card["Driver Name"]
    if card["Upload Scores"]:
        new_user_id = upload_times(user_id, username, times)
    else:
        new_user_id = user_id
    write_card(new_data, card, new_user_id)
    new_data.seek(0)
    response = send_file(new_data, as_attachment=True, download_name='SBZZ_card.bin')
    return response

@app.route('/leaderboard')
def view_leaderboard():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    cursor.execute('SELECT username, times FROM leaderboard')
    leaderboard = dict()
    all_data = cursor.fetchall()
    for username, times in all_data:
        times_dict = ast.literal_eval(times)
        for course in times_dict:
            if course not in leaderboard:
                leaderboard[course] = []
            current_time = time_to_ms(times_dict[course]['Time'])
            if current_time == 0:
                continue
            if len(leaderboard[course]) < 10:
                leaderboard[course].append({'Username': username, 'Time': current_time,
                                            'Car Make': times_dict[course]['Car Make'],
                                            'Car Model': times_dict[course]['Car Model']})
            else:
                leaderboard[course].sort(key=lambda x: x['Time'])
                if current_time < leaderboard[course][-1]['Time']:
                    leaderboard[course][-1] = {'Username': username, 'Time': current_time,
                                                'Car Make': times_dict[course]['Car Make'],
                                                'Car Model': times_dict[course]['Car Model']}
            leaderboard[course].sort(key=lambda x: x['Time'])
            leaderboard[course] = leaderboard[course][:10]
    for course in leaderboard:
        for i in range(len(leaderboard[course])):
            leaderboard[course][i]["Time"] = ms_to_time(leaderboard[course][i]["Time"])
    conn.close()
    return render_template('leaderboard.html', title='Leaderboard', leaderboard=leaderboard)
