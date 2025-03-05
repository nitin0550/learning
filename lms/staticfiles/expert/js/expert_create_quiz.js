document.getElementById('add-question').addEventListener('click', function() {
    if (questionCount >= maxQuestions) {
        alert('You can only add up to 100 questions.');
        return;
    }

    questionCount++;
    const container = document.getElementById('questions-container');
    const questionDiv = document.createElement('div');
    questionDiv.setAttribute('id', `question_${questionCount}`);
    questionDiv.innerHTML = `
        <h4>Question ${questionCount}</h4>
        <label>Question Text:</label>
        <input type="text" name="question_text_${questionCount}" required>
        <label>Question Type:</label>
        <select name="question_type_${questionCount}" onchange="toggleQuestionType(${questionCount}, this.value)">
            <option value="">Select Question Type</option>
            <option value="MCQ">Multiple Choice</option>
            <option value="TF">True/False</option>
            <option value="SA">Short Answer</option>
        </select>
        <div id="options_${questionCount}" style="display: none;">
            <label>Option 1:</label>
            <input type="text" name="option_${questionCount}_1">
            <input type="radio" name="correct_option_${questionCount}" value="1">
            <label>Option 2:</label>
            <input type="text" name="option_${questionCount}_2">
            <input type="radio" name="correct_option_${questionCount}" value="2">
            <label>Option 3:</label>
            <input type="text" name="option_${questionCount}_3">
            <input type="radio" name="correct_option_${questionCount}" value="3">
            <label>Option 4:</label>
            <input type="text" name="option_${questionCount}_4">
            <input type="radio" name="correct_option_${questionCount}" value="4">
        </div>
        <div id="tf_${questionCount}" style="display: none;">
            <label>Option 1:</label>
            <input type="text" name="option_${questionCount}_1" value="True" readonly>
            <input type="radio" name="correct_option_${questionCount}" value="1">
            <label>Option 2:</label>
            <input type="text" name="option_${questionCount}_2" value="False" readonly>
            <input type="radio" name="correct_option_${questionCount}" value="2">
        </div>
        <div id="sa_${questionCount}" style="display: none;">
            <label>Correct Answer:</label>
            <input type="text" name="correct_answer_${questionCount}">
        </div>
    `;
    container.appendChild(questionDiv);
});

function toggleQuestionType(questionNumber, type) {
    document.getElementById(`options_${questionNumber}`).style.display = (type === 'MCQ') ? 'block' : 'none';
    document.getElementById(`tf_${questionNumber}`).style.display = (type === 'TF') ? 'block' : 'none';
    document.getElementById(`sa_${questionNumber}`).style.display = (type === 'SA') ? 'block' : 'none';
}