from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
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

# Set your Gemini API key
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['UPLOAD_FOLDER'] = 'uploads'

# Set up MongoDB
client = MongoClient(os.getenv('MONGO_URI'))  # Replace with your MongoDB connection string
db = client.flashy  # Database name
flashcards_collection = db.flashcards  # Collection name


# Ensure the static folder exists for saving images
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
    return render_template('upload.html')

@app.route('/generated_cards')
def generated_cards():
    return render_template('generated_cards.html')

@app.route('/view_flashcards')
def view_flashcards():
    return render_template('view_flashcards.html')

@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/courses')
def get_courses():
    courses = flashcards_collection.distinct('course')
    return jsonify({'courses': courses})

@app.route('/flashcards')
def get_flashcards():
    course = request.args.get('course', 'general')
    flashcards = flashcards_collection.find_one({'course': course})
    if flashcards:
        return jsonify({'flashcards': flashcards['flashcards']})
    return jsonify({'flashcards': []})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    course = request.form.get('course', 'general').title()  # Default to 'general' if no course is specified
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_type = file.filename.rsplit('.', 1)[1].lower()
        
        try:
            flashcards = ''
            if file_type == 'pdf':
                flashcards = extract_text_from_pdf(file_path)
            elif file_type == 'pptx':
                flashcards = extract_text_from_pptx(file_path)
            elif file_type == 'docx':
                flashcards = extract_text_from_docx(file_path)
            else:
                flashcards = 'Unsupported file type'
            
            os.remove(file_path)
            
            # Store or update the flashcards in MongoDB
            flashcards_collection.update_one(
                {'course': course},
                {'$addToSet': {'flashcards': {'$each': flashcards}}},
                upsert=True
            )
            
            return jsonify({'type': file_type, 'flashcards': flashcards})
        
        except Exception as e:
            print(f"Error processing file: {e}")
            return jsonify({'error': 'Error processing file'})
    
    return jsonify({'error': 'File type not allowed'})


@app.route('/preview_upload', methods=['GET', 'POST'])
def preview_upload_file():
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
                return render_template('preview_pdf.html', images=image_paths, file_ext=file_ext, course=course)
            elif file_ext == 'docx':
                file.save('uploaded_doc.docx')
                doc = Document('uploaded_doc.docx')
                paragraphs = [p.text for p in doc.paragraphs]
                pages = chunk_text_by_lines(paragraphs)
                return render_template('preview_text.html', pages=pages, file_ext=file_ext, course=course)
            elif file_ext == 'pptx':
                file.save('uploaded_presentation.pptx')
                ppt = Presentation('uploaded_presentation.pptx')
                slides = [slide.shapes.title.text if slide.shapes.title else '' for slide in ppt.slides]
                return render_template('preview_text.html', pages=[slides], file_ext=file_ext, course=course)
    return render_template('upload.html')


@app.route('/process', methods=['POST'])
def process_pages():
    selected_pages = request.form.getlist('pages')
    file_ext = request.form.get('file_ext')
    course = request.form.get('course', 'General')

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

        print(extracted_text)
        flashcards = generate_flashcards(extracted_text, 6)
        print(flashcards)


        # Store or update the flashcards in MongoDB
        flashcards_collection.update_one(
            {'course': course},
            {'$addToSet': {'flashcards': {'$each': flashcards}}},
            upsert=True
        )

    except Exception as e:
        print(f"Error processing file: {e}")
        return render_template('generated_cards.html')

    return render_template('generated_cards.html', file_type=file_ext, flashcards=flashcards )






def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        extracted_text = '\n'.join(text)
        flashcards = generate_flashcards(extracted_text, 8)
        print(f"Extracted text from DOCX: {extracted_text}")
        print(f"Generated flashcards: {flashcards}")
        return flashcards
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return "Error extracting text from DOCX"

def extract_text_from_pptx(pptx_path):
    try:
        prs = Presentation(pptx_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        extracted_text = '\n'.join(text)
        flashcards = generate_flashcards(extracted_text, 8)
        print(f"Extracted text from PPTX: {extracted_text}")
        print(f"Generated flashcards: {flashcards}")
        return flashcards
    except Exception as e:
        print(f"Error extracting text from PPTX: {e}")
        return "Error extracting text from PPTX"

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text.append(page.get_text())
        extracted_text = '\n'.join(text)
        flashcards = generate_flashcards(extracted_text, 8)
        print(f"Extracted text from PDF: {extracted_text}")
        print(f"Generated flashcards: {flashcards}")
        return flashcards
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return "Error extracting text from PDF"




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


if __name__ == '__main__':
    app.run(debug=True)
