// Insight Collective - Main JS

document.addEventListener('DOMContentLoaded', function () {
    console.log('Insight Collective application initialized.');

    // Add scroll effect to navbar
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('navbar-scrolled', 'shadow');
            navbar.style.padding = '0.5rem 0';
        } else {
            navbar.classList.remove('navbar-scrolled', 'shadow');
            navbar.style.padding = '1rem 0';
        }
    });

    // Form validation (if applicable)
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Handle smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // AI Widget Logic
    const aiFloatingBtn = document.getElementById('aiFloatingBtn');
    const aiChatWindow = document.getElementById('aiChatWindow');
    const closeAiChat = document.getElementById('closeAiChat');
    const sendAiBtn = document.getElementById('sendAiBtn');
    const aiInput = document.getElementById('aiInput');
    const aiChatBody = document.getElementById('aiChatBody');

    if (aiFloatingBtn && aiChatWindow) {
        aiFloatingBtn.addEventListener('click', () => {
            aiChatWindow.classList.toggle('d-none');
            if (!aiChatWindow.classList.contains('d-none')) {
                aiInput.focus();
            }
        });

        closeAiChat.addEventListener('click', () => {
            aiChatWindow.classList.add('d-none');
        });

        const handleSendMsg = async () => {
            const text = aiInput.value.trim();
            if (text) {
                // Add user message
                const userMsg = document.createElement('div');
                userMsg.className = 'ai-message ai-sent';
                userMsg.textContent = text;
                aiChatBody.appendChild(userMsg);

                aiInput.value = '';
                aiChatBody.scrollTop = aiChatBody.scrollHeight;

                // Add loading indicator
                const loadingMsg = document.createElement('div');
                loadingMsg.className = 'ai-message ai-received';
                loadingMsg.innerHTML = '<span class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></span> Thinking...';
                aiChatBody.appendChild(loadingMsg);
                aiChatBody.scrollTop = aiChatBody.scrollHeight;

                try {
                    // Fetch real AI response
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ message: text })
                    });

                    const data = await response.json();

                    // Remove loading indicator
                    aiChatBody.removeChild(loadingMsg);

                    // Add AI response
                    const aiMsg = document.createElement('div');
                    aiMsg.className = 'ai-message ai-received';
                    if (response.ok) {
                        // Using innerHTML to render simple markdown if needed, but textContent handles raw text safely
                        aiMsg.textContent = data.response;
                    } else {
                        aiMsg.textContent = data.error || "Sorry, I encountered an error connecting to the intelligence network.";
                        aiMsg.classList.add('text-danger');
                    }
                    aiChatBody.appendChild(aiMsg);

                } catch (error) {
                    console.error("AI Chat Error:", error);
                    aiChatBody.removeChild(loadingMsg);
                    const aiMsg = document.createElement('div');
                    aiMsg.className = 'ai-message ai-received text-danger';
                    aiMsg.textContent = "Network error while reaching Insight AI.";
                    aiChatBody.appendChild(aiMsg);
                }

                aiChatBody.scrollTop = aiChatBody.scrollHeight;
            }
        };

        sendAiBtn.addEventListener('click', handleSendMsg);
        aiInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSendMsg();
            }
        });
    }
});
