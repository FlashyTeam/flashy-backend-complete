document.getElementById('uploadButton').addEventListener('click', (event) => {
    event.preventDefault(); // Prevent the default form submission

    const fileInput = document.getElementById('fileInput');
    const message = document.getElementById('message');
    const flashcardsDiv = document.getElementById('flashcards');

    if (fileInput.files.length === 0) {
        message.textContent = 'Please select a file.';
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            message.textContent = `Error: ${data.error}`;
        } else {
            message.textContent = `File uploaded successfully as ${data.type}`;
            flashcardsDiv.innerHTML = ''; // Clear previous flashcards

            data.flashcards.forEach(card => {
                const cardElement = document.createElement('div');
                cardElement.textContent = card;
                cardElement.style.border = '1px solid #000';
                cardElement.style.padding = '10px';
                cardElement.style.margin = '10px 0';
                flashcardsDiv.appendChild(cardElement);
            });
        }
    })
    .catch(error => {
        message.textContent = 'An error occurred during file upload.';
    });
});