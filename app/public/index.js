/* app/public/index.js */

(function() {
    console.log("Vexilon Forensic UI Initialized");

    /**
     * KB Sidebar: parse chainlit.md markdown table and render as fixed sidebar
     */
    function buildKbSidebar() {
        if (document.getElementById('kb-sidebar')) return;

        fetch('/project/settings')
            .then(r => r.json())
            .then(data => {
                const md = data.markdown || '';

                // Extract the table rows from the markdown
                const lines = md.split('\n');
                let rows = [];
                let inTable = false;
                lines.forEach(line => {
                    if (line.startsWith('|') && !line.startsWith('| :')) {
                        inTable = true;
                        const cells = line.split('|').slice(1, -1).map(c => c.trim());
                        if (cells.length >= 3) rows.push(cells);
                    } else if (inTable && !line.startsWith('|')) {
                        inTable = false;
                    }
                });

                if (rows.length < 2) return; // header + at least one row
                const [header, ...dataRows] = rows;

                let tableHtml = `<table><thead><tr>${header.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>`;
                dataRows.forEach(cells => {
                    tableHtml += '<tr>' + cells.map(c => {
                        // convert [text](url) to <a>
                        return '<td>' + c.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>') + '</td>';
                    }).join('') + '</tr>';
                });
                tableHtml += '</tbody></table>';

                const sidebar = document.createElement('div');
                sidebar.id = 'kb-sidebar';
                sidebar.innerHTML = `<h2>Knowledge Base</h2>${tableHtml}`;
                document.body.appendChild(sidebar);
            })
            .catch(() => {}); // sidebar is cosmetic — fail silently
    }

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

    /**
     * Rebranding: Rename 'Readme' to 'Knowledge Base'
     */
    function renameReadme() {
        const elements = document.querySelectorAll('button, a, span, p');
        elements.forEach(el => {
            if (el.textContent.trim() === 'Readme') {
                el.textContent = 'Knowledge Base';
            }
        });
    }

    // Run periodically to catch re-renders
    setInterval(() => {
        setupEnterToSubmit();
        renameReadme();
    }, 1000);

    setupEnterToSubmit();
    renameReadme();
    buildKbSidebar();
})();
