// Example quiz data structure (replace with actual data retrieval)
const quizData = {
    title: "Sample Quiz",
    questions: [
        {
            text: "Is the sky blue?",
            type: "true-false",
            correctAnswer: "true"
        },
        {
            text: "Which of the following is a programming language?",
            type: "multiple-choice",
            options: [
                "Python",
                "Banana",
                "Sky",
                "Earth"
            ],
            correctAnswer: "Python"
        },
        {
            text: "Explain the theory of relativity.",
            type: "short-answer",
            correctAnswer: "The theory of relativity explains how time and space are linked for objects that are moving at a constant speed."
        }
    ]
};

// Load quiz title
document.getElementById('quiz-title').textContent = quizData.title;

// Function to load questions into the quiz form
function loadQuestions() {
    const questionContainer = document.getElementById('question-container');

    quizData.questions.forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question';

        questionDiv.innerHTML = `<label>${index + 1}. ${question.text}</label>`;

        if (question.type === 'true-false') {
            questionDiv.innerHTML += `
                <label><input type="radio" name="question-${index}" value="true"> True</label>
                <label><input type="radio" name="question-${index}" value="false"> False</label>
            `;
        } else if (question.type === 'multiple-choice') {
            question.options.forEach(option => {
                questionDiv.innerHTML += `
                    <label><input type="radio" name="question-${index}" value="${option}"> ${option}</label>
                `;
            });
        } else if (question.type === 'short-answer') {
            questionDiv.innerHTML += `<input type="text" name="question-${index}" placeholder="Your answer here">`;
        }

        questionContainer.appendChild(questionDiv);
    });
}

// Handle quiz submission
document.getElementById('quiz-form').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent form submission

    let score = 0;

    quizData.questions.forEach((question, index) => {
        const userAnswer = document.querySelector(`input[name="question-${index}"]:checked`)?.value || 
                           document.querySelector(`input[name="question-${index}"]`)?.value;

        if (userAnswer && userAnswer.toLowerCase() === question.correctAnswer.toLowerCase()) {
            score++;
        }
    });

    const resultMessage = document.getElementById('result-message');
    resultMessage.textContent = `You scored ${score} out of ${quizData.questions.length}`;
});

// Load questions when the page is loaded
window.onload = loadQuestions;
