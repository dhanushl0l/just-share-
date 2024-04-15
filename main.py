from flask import Flask, render_template, request, send_from_directory
import random
import string
import json
import os
from datetime import datetime, timedelta
import glob


app = Flask(__name__)

# Dictionary to store the message, username, and pin
shared_data = {}

# Define the path to the database folder
DATABASE_FOLDER = os.path.join(os.path.dirname(__file__), 'database')

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/send', methods=['GET', 'POST'])
def send():
    if request.method == 'POST':
        message = request.form['message']
        if not message:
            return render_template('index.html', error="Message cannot be empty")

        shared_data['message'] = message
        # Generate a unique username
        while True:
            username = ''.join(random.choices(string.ascii_lowercase, k=4))
            if not username_exists(username):
                break
        shared_data['username'] = username
        
        shared_data['pin'] = ''.join(random.choices(string.digits, k=4))

        # Create the database folder if it doesn't exist
        if not os.path.exists(DATABASE_FOLDER):
            os.makedirs(DATABASE_FOLDER)
        
        # Delete old files and files beyond the limit
        delete_old_files()
        
        # Save data to a JSON file in the database folder
        filename = os.path.join(DATABASE_FOLDER, shared_data['username'] + '.json')
        with open(filename, 'w') as file:
            json.dump(shared_data, file)

        # Return a new HTML template for displaying the results
        return render_template('index.html', username=shared_data['username'], pin=shared_data['pin'])

    return render_template('index.html')

def delete_old_files():
    # Delete files older than 24 hours
    files = glob.glob(os.path.join(DATABASE_FOLDER, '*.json'))
    for file in files:
        creation_time = datetime.fromtimestamp(os.path.getctime(file))
        if datetime.now() - creation_time > timedelta(hours=24):
            os.remove(file)
    
    # Delete oldest files if the total number exceeds 1000
    files = sorted(glob.glob(os.path.join(DATABASE_FOLDER, '*.json')), key=os.path.getctime)
    while len(files) > 1000:
        os.remove(files.pop(0))

def username_exists(username):
    # Check if the username exists in the database
    files = glob.glob(os.path.join(DATABASE_FOLDER, '*.json'))
    for file in files:
        with open(file) as f:
            data = json.load(f)
            if data.get('username') == username:
                return True
    return False


@app.route('/receive', methods=['GET', 'POST'])
def receive():
    if request.method == 'POST':
        username = request.form['username']
        pin = request.form['pin']
        filename = os.path.join(DATABASE_FOLDER, username + '.json')

        if os.path.exists(filename):
            with open(filename, 'r') as file:
                data = json.load(file)
                if data['pin'] == pin:
                    message = data.get('message', 'No message shared yet')
                    message = message.replace('\r\n', '‎ ')
                    return render_template('index.html', message=message)
                else:
                    return render_template('index.html', error="Incorrect pin")
        else:
            return render_template('index.html', error="Username not found")
    return render_template('index.html')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Route to serve the HTML form for uploading files
@app.route('/files/')
def files():
    return render_template("index-files.html")

# Route to handle file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files['file']
    
    # Check file size
    file_size = len(uploaded_file.read())
    if file_size > 11 * 1024 * 1024:  # 11MB in bytes
        return "File size exceeds 11MB. Please upload a smaller file."
    
    # Reset file cursor to the beginning
    uploaded_file.seek(0)
    
    # Generate random 4-letter folder name
    folder_name = ''.join(random.choices(string.ascii_lowercase, k=4))
    
    # Save the file inside the folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, uploaded_file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    uploaded_file.save(file_path)
    
    # Generate random 4-digit PIN
    pin = ''.join(random.choices(string.digits, k=4))
    
    # Store folder name and PIN in dictionary
    folder_pin_mapping = { 'folder_name': folder_name, 'pin': pin }
    
    # Store folder name and PIN mapping in JSON file
    with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, folder_name + '.json'), 'w') as f:
        json.dump(folder_pin_mapping, f)
    
    return """
    <h1>File Uploaded Successfully!</h1>
    <p>Folder Name: {folder_name}</p>
    <p>PIN: {pin}</p>
    """.format(folder_name=folder_name, pin=pin)

@app.route('/download', methods=['GET'])
def download_file():
    pin = request.args.get('pin')
    folder_name = request.args.get('folder_name')
    
    if folder_name is None or pin is None:
        return 'Invalid request!'
    
    # Load the JSON file
    with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, folder_name + '.json'), 'r') as f:
        folder_pin_mapping = json.load(f)
    
    # Check if PIN and folder name match
    if folder_pin_mapping['pin'] == pin and folder_pin_mapping['folder_name'] == folder_name:
        files_in_folder = os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], folder_name))
        if len(files_in_folder) > 0:
            file_to_download = files_in_folder[0]
            return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder_name), file_to_download, as_attachment=True)
        else:
            return 'No files found in the folder!'
    else:
        return 'Invalid PIN or folder name!'



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 
