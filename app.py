from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import stripe
import config
from flask_cors import CORS
from pdf2image import convert_from_path
import PyPDF2
from docx import Document
from pptx import Presentation
import fitz  # PyMuPDF
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
from pymongo import MongoClient
import json
import time

load_dotenv()


app = Flask(__name__)


app.secret_key = os.getenv('SECRET_KEY')
bcrypt = Bcrypt(app)

# Set your Gemini API key
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)

CORS(app)  # Enable CORS
app.config['UPLOAD_FOLDER'] = 'uploads'

# Set up MongoDB
client = MongoClient(os.getenv('MONGO_URI'))
db = client.flashy
flashcards_collection = db.flashcards
users = db.users


# Static folder for storing generated images from pdf
if not os.path.exists('static'):
    os.makedirs('static')


def chunk_text_by_lines(paragraphs, lines_per_page=25):
    chunks = []
    current_chunk = []
    current_lines = 0
    for p in paragraphs:
        lines_in_p = p.count('\n') + 1
        if current_lines + lines_in_p > lines_per_page:
            chunks.append(current_chunk)
            current_chunk = []
            current_lines = 0
        current_chunk.append(p)
        current_lines += lines_in_p
    if current_chunk:
        chunks.append(current_chunk)
    return chunks



if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'pdf', 'pptx', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('home.html')

# Route for generated cards for free version
@app.route('/generated_cards_free')
def generated_cards_free():
    return render_template('generated_cards_free.html')

# Route for generated cards for premium version
@app.route('/generated_cards')
def generated_cards():
    return render_template('generated_cards.html')

# Route for viewing flashcard page
@app.route('/view_flashcards')
def view_flashcards():
    return render_template('view_flashcards.html')

# Upload for free version
@app.route('/upload_free_page')
def upload_free_page():
    return render_template('upload_free.html')

# Upload for premium users
@app.route('/upload_page')
def upload_page():
    if 'user_id' not in session:
        flash("Please log in to access your dashboard.")
        return redirect(url_for('login'))
    return render_template('upload.html', username=session['username'], plan=session['plan'])

# Route for fetching courses in database
@app.route('/courses')
def get_courses():
    username = request.args.get('username')  # Get the username from query parameters
    courses = flashcards_collection.distinct('course', {'username': username})
    return jsonify({'courses': courses})

# Route for retrieving flashcards from database
@app.route('/flashcards')
def get_flashcards():
    username = request.args.get('username')
    course = request.args.get('course', 'general')
    
    # Find the document based on username and course
    flashcards_data = flashcards_collection.find_one({'username': username, 'course': course})
    
    if flashcards_data:
        return jsonify({
            'flashcards': flashcards_data.get('flashcards', []),
            'quizzes': flashcards_data.get('quizzes', [])
        })
    return jsonify({'flashcards': [], 'quizzes': []})

# Register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "plan": "premium"
        }

        if users.find_one({"email": email}):
            flash("Email already registered!")
            return redirect(url_for('register'))

        if users.find_one({"username": username}):
            flash("Username already registered!")
            return redirect(url_for('register'))

        users.insert_one(user_data)
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))

    return render_template('register.html')


# Login User
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.find_one({"email": email})
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['plan'] = user['plan']
            flash("Login successful!")
            return redirect(url_for('upload_page'))
        else:
            flash("Invalid credentials!")
            return redirect(url_for('login'))

    return render_template('login.html')

# Logout User
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('home'))



# Upload for free version
@app.route('/preview_free_upload', methods=['GET', 'POST'])
def preview_free_upload_file():
    if request.method == 'POST':
        file = request.files['file']
        course = request.form.get('text', 'general').title()

        if file:
            file_ext = file.filename.split('.')[-1].lower()
            if file_ext == 'pdf':
                file.save('uploaded_doc.pdf')
                images = convert_from_path('uploaded_doc.pdf',500,poppler_path=r'C:\Program Files\poppler-24.07.0\Library\bin')
                image_paths = []
                for i, image in enumerate(images):
                    image_path = f'static/page_{i + 1}.png'
                    image.save(image_path, 'PNG')
                    image_paths.append(image_path)
                return render_template('preview_pdf_free.html', images=image_paths, file_ext=file_ext, course=course)
            elif file_ext == 'docx':
                file.save('uploaded_doc.docx')
                doc = Document('uploaded_doc.docx')
                paragraphs = [p.text for p in doc.paragraphs]
                pages = chunk_text_by_lines(paragraphs)
                return render_template('preview_text_free.html', pages=pages, file_ext=file_ext, course=course)
            elif file_ext == 'pptx':
                file.save('uploaded_presentation.pptx')
                ppt = Presentation('uploaded_presentation.pptx')
                slides = [slide.shapes.title.text if slide.shapes.title else '' for slide in ppt.slides]
                return render_template('preview_text_free.html', pages=[slides], file_ext=file_ext, course=course)
    return render_template('upload.html')



# Upload for premium users
@app.route('/preview_upload', methods=['GET', 'POST'])
def preview_upload_file():
    if request.method == 'POST':
        file = request.files['file']
        course = request.form.get('text', 'general').title()
        username = request.form.get('username')

        if file:
            file_ext = file.filename.split('.')[-1].lower()
            if file_ext == 'pdf':
                file.save('uploaded_doc.pdf')
                images = convert_from_path('uploaded_doc.pdf',500,poppler_path=r'C:\Program Files\poppler-24.07.0\Library\bin')
                image_paths = []
                for i, image in enumerate(images):
                    image_path = f'static/page_{i + 1}.png'
                    image.save(image_path, 'PNG')
                    image_paths.append(image_path)
                return render_template('preview_pdf.html', images=image_paths, file_ext=file_ext, course=course, username=username)
            elif file_ext == 'docx':
                file.save('uploaded_doc.docx')
                doc = Document('uploaded_doc.docx')
                paragraphs = [p.text for p in doc.paragraphs]
                pages = chunk_text_by_lines(paragraphs)
                return render_template('preview_text.html', pages=pages, file_ext=file_ext, course=course, username=username)
            elif file_ext == 'pptx':
                file.save('uploaded_presentation.pptx')
                ppt = Presentation('uploaded_presentation.pptx')
                slides = [slide.shapes.title.text if slide.shapes.title else '' for slide in ppt.slides]
                return render_template('preview_text.html', pages=[slides], file_ext=file_ext, course=course, username=username)
    return render_template('upload.html')



# Free flashcard generation
@app.route('/process_free', methods=['POST'])
def process_free_pages():
    selected_pages = request.form.getlist('pages')
    file_ext = request.form.get('file_ext')
    flashcard_number = request.form.get('flashcard-number')

    try:
        extracted_text = ''
        flashcards = ''
        
        if file_ext == 'pdf':
            reader = PyPDF2.PdfReader('uploaded_doc.pdf')
            for page_num in selected_pages:
                page = reader.pages[int(page_num) - 1]
                extracted_text += page.extract_text()
            # Delete images after processing
            for i in range(len(reader.pages)):
                image_path = f'static/page_{i + 1}.png'
                if os.path.exists(image_path):
                    os.remove(image_path)
            if os.path.exists('uploaded_doc.pdf'):
                os.remove('uploaded_doc.pdf')

        elif file_ext == 'docx':
            doc = Document('uploaded_doc.docx')
            paragraphs = [p.text for p in doc.paragraphs]
            pages = chunk_text_by_lines(paragraphs)
            for page_num in selected_pages:
                extracted_text += '\n'.join(pages[int(page_num) - 1])
            if os.path.exists('uploaded_doc.docx'):
                os.remove('uploaded_doc.docx')

        elif file_ext == 'pptx':
            ppt = Presentation('uploaded_presentation.pptx')
            slides = [slide.shapes.title.text if slide.shapes.title else '' for slide in ppt.slides]
            for page_num in selected_pages:
                extracted_text += slides[int(page_num) - 1] + '\n'
            if os.path.exists('uploaded_presentation.pptx'):
                os.remove('uploaded_presentation.pptx')

        # print(extracted_text)
        flashcards = generate_flashcards(extracted_text, flashcard_number)
        print(flashcards)

    except Exception as e:
        print(f"Error processing file: {e}")
        return render_template('generated_cards_free.html')

    return render_template('generated_cards_free.html', flashcards=flashcards )



# Generating cards for premium users
@app.route('/process', methods=['POST'])
def process_pages():
    selected_pages = request.form.getlist('pages')
    file_ext = request.form.get('file_ext')
    course = request.form.get('course', 'General')
    username = request.form.get('username')
    flashcard_number = request.form.get('flashcard-number')
    quiz = 'quiz' in request.form

    try:
        extracted_text = ''
        flashcards = []

        # Process the file according to the extension
        if file_ext == 'pdf':
            reader = PyPDF2.PdfReader('uploaded_doc.pdf')
            for page_num in selected_pages:
                page = reader.pages[int(page_num) - 1]
                extracted_text += page.extract_text()
            # Delete images after processing
            for i in range(len(reader.pages)):
                image_path = f'static/page_{i + 1}.png'
                if os.path.exists(image_path):
                    os.remove(image_path)
            if os.path.exists('uploaded_doc.pdf'):
                os.remove('uploaded_doc.pdf')

        elif file_ext == 'docx':
            doc = Document('uploaded_doc.docx')
            paragraphs = [p.text for p in doc.paragraphs]
            pages = chunk_text_by_lines(paragraphs)
            for page_num in selected_pages:
                extracted_text += '\n'.join(pages[int(page_num) - 1])
            if os.path.exists('uploaded_doc.docx'):
                os.remove('uploaded_doc.docx')

        elif file_ext == 'pptx':
            ppt = Presentation('uploaded_presentation.pptx')
            slides = [slide.shapes.title.text if slide.shapes.title else '' for slide in ppt.slides]
            for page_num in selected_pages:
                extracted_text += slides[int(page_num) - 1] + '\n'
            if os.path.exists('uploaded_presentation.pptx'):
                os.remove('uploaded_presentation.pptx')

        # Generate flashcards
        flashcards = generate_flashcards(extracted_text, flashcard_number)
        print(flashcards)

        # Store or update the flashcards in MongoDB
        flashcards_collection.update_one(
            {'username': username, 'course': course},
            {'$addToSet': {'flashcards': {'$each': flashcards}}},
            upsert=True
        )

        quiz_cards = []
        if quiz:
            quiz_number = 5
            quiz_cards = generate_quiz(extracted_text, quiz_number)
            print(quiz_cards)

            # Store or update the quiz cards in MongoDB
            flashcards_collection.update_one(
                {'username': username, 'course': course},
                {'$addToSet': {'quizzes': {'$each': quiz_cards}}},
                upsert=True
            )

        return render_template('generated_cards.html', file_type=file_ext, flashcards=flashcards, quiz_cards=quiz_cards)

    except Exception as e:
        # Handle any errors that occur during processing
        return str(e)




# Flashcard generation with gemini
def generate_flashcards(text, num_flashcards, retries=3):
    prompt = f"Create {num_flashcards} flashcards from the following text:\n\n{text}\n\n Return answers in json format as an array of objects with 'front' and 'back' keys. Everything should be inline, no backslash n"

    for attempt in range(retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            print(response)
            
            if response and response.candidates:
                flashcards_text = response.candidates[0].content.parts[0].text
                
                # Find the start of the JSON array
                json_start = flashcards_text.find("[")
                if json_start != -1:
                    json_text = flashcards_text[json_start:]
                    try:
                        flashcards = json.loads(json_text)
                        return flashcards
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error on attempt {attempt + 1}: {e}")
                else:
                    print(f"No JSON array found in the response on attempt {attempt + 1}.")
            else:
                print(f"Error generating flashcards on attempt {attempt + 1}.")
        
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
        
        time.sleep(1)  # Optional: wait 1 second before retrying

    return "Error generating flashcards after multiple attempts."


# Quiz Generation with gemini
def generate_quiz(text, num_quiz, retries=3):
    prompt = f"Create {num_quiz} multiple-choice questions with answers from the following text:\n\n{text}\n\nReturn answers in JSON format as an array of objects with 'question', 'options' (an array of four possible answers), and 'answer' keys. Everything should be inline, no backslash n and no backslash either."

    for attempt in range(retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(prompt)
            # print(response)
            
            if response and response.candidates:
                # Extract the text from the response
                quiz_text = response.candidates[0].content.parts[0].text
                
                # Find the start of the JSON array
                json_start = quiz_text.find("[")
                if json_start != -1:
                    json_text = quiz_text[json_start:]
                    try:
                        quiz = json.loads(json_text)
                        return quiz
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error on attempt {attempt + 1}: {e}")
                else:
                    print(f"No JSON array found in the response on attempt {attempt + 1}.")
            else:
                print(f"Error generating flashcards on attempt {attempt + 1}.")
        
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
        
        time.sleep(1)  # Optional: wait 1 second before retrying

    return "Error generating flashcards after multiple attempts."



if __name__ == '__main__':
    app.run(debug=True)
