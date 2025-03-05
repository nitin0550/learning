let currentChat = '';
let currentAvatar = '';
let currentDropdown = null; // Track the currently opened dropdown

function openChat(contact) {
    currentChat = contact;
    currentAvatar = 'https://via.placeholder.com/36'; // Set the avatar for the current chat
    document.getElementById('chatAvatar').src = currentAvatar; // Set avatar in header
    document.getElementById('chatHeader').innerText = `${contact}`;
    document.getElementById('messageList').innerHTML = ''; // Clear previous messages
    document.getElementById('contactsList').style.display = 'none'; // Hide contacts
    document.getElementById('chatArea').style.display = 'flex'; // Show chat area
}

function closeChat() {
    return window.location.replace(".")
}

function closeChatArea() {
    document.getElementById('contactsList').style.display = 'block'; // Show contacts
    document.getElementById('chatArea').style.display = 'none'; // Hide chat area
    currentDropdown = null; // Reset currently opened dropdown
}

function toggleDropdown(event, dropdownId) {
    event.stopPropagation(); // Prevent opening chat
    const dropdown = document.getElementById(dropdownId);

    // Close the previously opened dropdown if it's different
    if (currentDropdown && currentDropdown !== dropdown) {
        currentDropdown.style.display = 'none';
    }

    // Toggle current dropdown
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
    currentDropdown = dropdown.style.display === 'block' ? dropdown : null;
}

function deleteContact(event, contactName) {
    event.stopPropagation(); // Prevent opening chat
    if (confirm(`Are you sure you want to delete ${contactName}?`)) {
        const contactCard = document.getElementById(`contact${contactName.replace(" ", "")}`);
        contactCard.remove(); // Remove the contact card
    }
}

function viewProfile(event, contactName) {
    event.stopPropagation(); // Prevent opening chat
    alert(`Viewing profile of ${contactName}`); // Replace with actual profile view logic
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const messageText = input.value;

    if (messageText && currentChat) {
        const messageList = document.getElementById('messageList');
        const messageItem = document.createElement('div');
        messageItem.classList.add('message', 'sent');
        messageItem.innerHTML = `
            <div class="message-content">${messageText}</div>
        `;
        messageList.appendChild(messageItem);
        input.value = '';

        // Scroll to the bottom of the messages
        messageList.scrollTop = messageList.scrollHeight;

        // Simulate a response after a short delay
        setTimeout(() => {
            receiveMessage(`This is a response from ${currentChat}.`);
        }, 1000);
    } else {
        alert('Please type a message or select a contact.');
    }
}

function receiveMessage(text) {
    const messageList = document.getElementById('messageList');
    const messageItem = document.createElement('div');
    messageItem.classList.add('message', 'received');
    messageItem.innerHTML = `
        <div class="message-content">${text}</div>
    `;
    messageList.appendChild(messageItem);

    // Scroll to the bottom of the messages
    messageList.scrollTop = messageList.scrollHeight;
}

// Close dropdown if clicking outside of it
window.onclick = function(event) {
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        dropdown.style.display = 'none';
    });
    currentDropdown = null; // Reset currently opened dropdown
};