/* app/public/index.js */

function injectPersonaSelector() {
    const header = document.querySelector('.header');
    if (!header || document.querySelector('#persona-selector-container')) return;

    const container = document.createElement('div');
    container.id = 'persona-selector-container';
    
    const label = document.createElement('span');
    label.innerText = 'Mode: ';
    label.style.fontSize = '0.75rem';
    label.style.marginRight = '0.5rem';
    label.style.opacity = '0.7';

    const select = document.createElement('select');
    select.id = 'persona-selector';
    
    ['Lookup', 'Grieve', 'Audit', 'Manage'].forEach(mode => {
        const option = document.createElement('option');
        option.value = mode;
        option.text = mode;
        select.appendChild(option);
    });

    select.addEventListener('change', (e) => {
        const newMode = e.target.value;
        syncWithChainlitSettings(newMode);
    });

    container.appendChild(label);
    container.appendChild(select);
    
    // Insert after the title
    const title = header.querySelector('.title') || header.firstChild;
    if (title && title.nextSibling) {
        header.insertBefore(container, title.nextSibling);
    } else {
        header.appendChild(container);
    }
}

function syncWithChainlitSettings(mode) {
    // 1. Open settings
    const gearIcon = document.querySelector('#chat-settings-open-modal');
    if (!gearIcon) {
        console.error('Settings icon not found');
        return;
    }
    gearIcon.click();

    // 2. Wait for modal and find Persona select
    let attempts = 0;
    const findAndChange = setInterval(() => {
        const modalSelect = document.querySelector('#Persona'); // ID from ChatSettings
        if (modalSelect) {
            modalSelect.value = mode;
            modalSelect.dispatchEvent(new Event('change', { bubbles: true }));
            
            // 3. Close modal (click backdrop or the gear again)
            setTimeout(() => {
                const backdrop = document.querySelector('.MuiBackdrop-root');
                if (backdrop) backdrop.click();
                else {
                   const closeBtn = document.querySelector('button[aria-label="close"]');
                   if (closeBtn) closeBtn.click();
                   else gearIcon.click();
                }
            }, 500);
            
            clearInterval(findAndChange);
        }
        if (++attempts > 50) clearInterval(findAndChange);
    }, 100);
}

// Observe DOM changes to catch the header rendering
const observer = new MutationObserver((mutations) => {
    injectPersonaSelector();
});

observer.observe(document.body, { childList: true, subtree: true });
