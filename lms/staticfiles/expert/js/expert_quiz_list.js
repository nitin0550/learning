// Example quiz data structure (replace with actual data retrieval)
const quizzes = [
    { id: 1, title: "Sample Quiz 1", description: "A basic quiz on general knowledge." },
    { id: 2, title: "Math Quiz", description: "A quiz to test your math skills." },
    { id: 3, title: "Science Quiz", description: "An introductory science quiz." }
];

// Function to load quizzes into the quiz list
function loadQuizzes() {
    const quizList = document.getElementById('quiz-list');
    quizList.innerHTML = ''; // Clear existing content

    if (quizzes.length === 0) {
        quizList.innerHTML = '<p>No quizzes available. Please create one!</p>';
    } else {
        quizzes.forEach(quiz => {
            const quizDiv = document.createElement('div');
            quizDiv.className = 'quiz-item';

            quizDiv.innerHTML = `
                <h3>${quiz.title}</h3>
                <p>${quiz.description}</p>
                <button onclick="editQuiz(${quiz.id})" class="action-button edit-button">Edit</button>
            `;

            quizList.appendChild(quizDiv);
        });
    }
}

// Function to handle quiz creation
document.getElementById('create-quiz').addEventListener('click', function() {
    window.location.href = 'create_quiz'; // Redirect to the quiz creation page
});

// Function to handle editing a quiz
function editQuiz(quizId) {
    alert(`Redirecting to edit Quiz ID: ${quizId}`);
    // Here you would redirect to the quiz editing page with the quiz ID
    // window.location.href = `edit-quiz.html?id=${quizId}`;
}

// Load quizzes when the page is loaded
window.onload = loadQuizzes;
