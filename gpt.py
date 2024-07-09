import openai
import time

load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('GPT_API_KEY')

def generate_flashcards(text, num_flashcards):
    prompt = f"Create {num_flashcards} flashcards from the following text:\n\n{text}\n\nFlashcards:"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            n=1,
            stop=None,
            temperature=0.7,
        )

        flashcards = response.choices[0].message['content'].strip()
        print(flashcards)
    except openai.error.RateLimitError:
        print("Rate limit exceeded. Please check your OpenAI plan and billing details.")
        # Optionally, you can wait for some time and retry
        time.sleep(60)  # wait for 1 minute before retrying
        generate_flashcards(text, num_flashcards)

# Example usage
text = """
Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll. Photosynthesis in plants generally involves the green pigment chlorophyll and generates oxygen as a by-product. The process can be broken down into two stages: the light-dependent reactions and the Calvin cycle. During the light-dependent reactions, energy from light is used to split water molecules, releasing oxygen and transferring energy to ATP and NADPH. In the Calvin cycle, ATP and NADPH are used to convert carbon dioxide into glucose.
"""
num_flashcards = 5

generate_flashcards(text, num_flashcards)
