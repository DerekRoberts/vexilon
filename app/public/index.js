/* app/public/index.js */

(function() {
    console.log("Vexilon Forensic UI Initialized");


    /**
     * Interaction Logic: Enter-to-Submit
     * (Mandated by UI Standards Section 2.3)
     */
    function setupEnterToSubmit() {
        const chatInput = document.querySelector('textarea');
        if (!chatInput || chatInput.dataset.listenerAttached) return;

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const sendBtn = document.querySelector('button[aria-label="Send message"]') || 
                                document.querySelector('button.send-button');
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                }
            }
        });
        
        chatInput.dataset.listenerAttached = "true";
    }

    function hideReadmeDrawerTitle() {
        document.querySelectorAll('h2').forEach(el => {
            if (el.textContent.trim() === 'Readme') el.style.display = 'none';
        });
    }

    let buildSha = "unknown";

    // Fetch version info dynamically from endpoint
    fetch('/api/version')
        .then(res => res.json())
        .then(data => {
            if (data.version === "Dev mode") {
                buildSha = "Dev mode";
            } else {
                const shaShort = data.sha ? data.sha.substring(0, 7) : "";
                buildSha = `${data.version}${shaShort ? ` (${shaShort})` : ""}`;
            }
            replaceBuildSha();
        })
        .catch(err => console.error("Error fetching version:", err));

    function replaceBuildSha() {
        document.querySelectorAll('code, span, p, li, a').forEach(el => {
            if (el.textContent.includes('{{BUILD_SHA}}')) {
                el.innerHTML = el.innerHTML.replace('{{BUILD_SHA}}', buildSha);
            }
        });
    }
    function setupFileAutoSubmit() {
        if (window.fileAutoSubmitObserverAttached) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1 && node.closest) {
                            // Check if the added node is inside the chat input container
                            // Chainlit mounts file chips inside the form/input area when uploading
                            const isInputArea = node.closest('#chat-input') || node.closest('form') || node.closest('.MuiFormControl-root');
                            
                            if (isInputArea) {
                                const text = node.textContent?.toLowerCase() || '';
                                if (text.includes('.md') || text.includes('.json')) {
                                    // Wait for React to unlock the Send button state
                                    setTimeout(() => {
                                        const sendBtn = document.getElementById('send-button') || 
                                                        document.querySelector('button[aria-label="Send message"]') ||
                                                        document.querySelector('button.send-button');
                                        if (sendBtn && !sendBtn.disabled) {
                                            sendBtn.click();
                                        }
                                    }, 300);
                                }
                            }
                        }
                    });
                }
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
        window.fileAutoSubmitObserverAttached = true;
    }

    // Run periodically to catch re-renders
    setInterval(() => {
        setupEnterToSubmit();
        hideReadmeDrawerTitle();
        replaceBuildSha();
        setupFileAutoSubmit();
    }, 100);

    setupEnterToSubmit();
    hideReadmeDrawerTitle();
    replaceBuildSha();
})();
