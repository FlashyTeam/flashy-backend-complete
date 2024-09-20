# Flashy - Automated Flashcard Generator (Backend)

Flashy is an innovative web application that automatically generates flashcards and quizzes from uploaded documents. This repository contains the backend code for the Flashy project.

## Features

- Document upload and processing (PDF, DOCX, PPTX)
- Automatic flashcard generation using Google's Generative AI (Gemini)
- Quiz generation for premium users
- User authentication and authorization
- MongoDB integration for data persistence
- Support for both free and premium user tiers

## Technologies Used

- Flask: Web framework
- PyMongo: MongoDB driver for Python
- Google Generative AI: For flashcard and quiz generation
- PyPDF2, python-docx, python-pptx: For document parsing
- Flask-Bcrypt: For password hashing
- Stripe: For payment processing (integration ready)
- CORS: For cross-origin resource sharing

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/FlashyTeam/flashy-backend-complete.git
   cd flashy-backend-complete
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add the following:
   ```
   SECRET_KEY=your_secret_key
   API_KEY=your_google_generative_ai_api_key
   MONGO_URI=your_mongodb_connection_string
   ```

4. Run the application:
   ```
   python app.py
   ```

## API Endpoints

- `/register`: User registration
- `/login`: User login
- `/logout`: User logout
- `/upload_page`: Page for document upload (premium users)
- `/upload_free_page`: Page for document upload (free users)
- `/preview_upload`: Preview uploaded document (premium users)
- `/preview_free_upload`: Preview uploaded document (free users)
- `/process`: Generate flashcards and quizzes (premium users)
- `/process_free`: Generate flashcards (free users)
- `/flashcards`: Retrieve flashcards for a user and course
- `/courses`: Retrieve courses for a user
- `/userAccount`: Retrieve user account details

## Contributing

Contributions to Flashy are welcome! Please fork the repository and submit a pull request with your changes.

## Contact

For any queries or support, please contact frimpongprince2000@gmail.com(mailto:frimpongprince2000@gmail.com).
