function toggleSearch() {
    const searchContainer = document.querySelector('.search-container');
    searchContainer.classList.toggle('active');

    const searchInput = document.getElementById('search');
    if (searchContainer.classList.contains('active')) {
        searchInput.focus(); // Focus on the search input when it becomes visible
    }
}

function performSearch() {
    const query = document.getElementById('search').value;
    console.log("Searching for:", query);
    // Here you would ideally filter or update the results based on the query
}

// Example functions for add actions
function viewCourse() {
    window.location.href = "./my_courses";
}
function addCourse() {
    window.location.href = "./upload_course";
}

function Assignment() {
    window.location.href = "./assignment";
}

function viewQuiz() {
    window.location.href = "./quiz_list";
}
function addQuiz() {
    window.location.href = "./create_quiz";
}
