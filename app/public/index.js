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
                        if (node.nodeType === 1) {
                            // Look for the chip text
                            const text = node.textContent?.toLowerCase() || '';
                            if (text.includes('.md') || text.includes('.json')) {
                                
                                // Ensure it's down in the chat input area, not a message from the bot
                                const isInputArea = node.closest && (
                                    node.closest('#chat-input') || 
                                    node.closest('form') || 
                                    node.closest('[id*="chat-input"]') ||
                                    // Fallback: check if the node is in the bottom half of the screen
                                    (node.getBoundingClientRect && node.getBoundingClientRect().top > window.innerHeight / 2)
                                );

                                if (isInputArea) {
                                    // File uploads take time. Poll for the send button to become enabled.
                                    let attempts = 0;
                                    const clickInterval = setInterval(() => {
                                        attempts++;
                                        const sendBtn = document.getElementById('send-button') || 
                                                        document.querySelector('button[aria-label="Send message"]') ||
                                                        document.querySelector('button.send-button');
                                        
                                        if (sendBtn && !sendBtn.disabled) {
                                            sendBtn.click();
                                            clearInterval(clickInterval);
                                        } else if (attempts > 50) {
                                            // Give up after 5 seconds to prevent memory leaks
                                            clearInterval(clickInterval);
                                        }
                                    }, 100);
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
