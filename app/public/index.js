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

    /**
     * Toolbar: Save Session Button
     * Injects a save button adjacent to the paperclip (attach) icon.
     * On click, submits the internal sentinel __VEXILON_SAVE__ via the
     * React-compatible native value setter pattern.
     */
    function setupSaveButton() {
        if (document.getElementById('vexilon-save-btn')) return;

        // Chainlit renders the attach button with aria-label containing 'ttach'
        const attachBtn = document.querySelector('button[aria-label*="ttach"]');
        if (!attachBtn) return;

        const toolbar = attachBtn.parentElement;
        if (!toolbar) return;

        const btn = document.createElement('button');
        btn.id = 'vexilon-save-btn';
        btn.title = 'Save Session';
        btn.type = 'button';
        btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>';
        btn.style.cssText = 'background:none;border:none;cursor:pointer;padding:4px;display:flex;align-items:center;color:inherit;opacity:0.7;';
        btn.addEventListener('mouseenter', () => btn.style.opacity = '1');
        btn.addEventListener('mouseleave', () => btn.style.opacity = '0.7');

        btn.addEventListener('click', () => {
            const textarea = document.querySelector('textarea');
            const sendBtn = document.querySelector('button[aria-label="Send message"]') ||
                            document.querySelector('button.send-button');
            if (!textarea || !sendBtn) return;

            // React-compatible programmatic value setter
            const nativeSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            nativeSetter.call(textarea, '__VEXILON_SAVE__');
            textarea.dispatchEvent(new Event('input', { bubbles: true }));

            // Small delay for React to process the state update
            setTimeout(() => {
                if (!sendBtn.disabled) sendBtn.click();
            }, 50);
        });

        // Insert before the attach button so it sits to its left
        toolbar.insertBefore(btn, attachBtn);
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
    // Run periodically to catch re-renders
    setInterval(() => {
        setupEnterToSubmit();
        hideReadmeDrawerTitle();
        replaceBuildSha();
        setupSaveButton();
    }, 100);

    setupEnterToSubmit();
    hideReadmeDrawerTitle();
    replaceBuildSha();
})();
