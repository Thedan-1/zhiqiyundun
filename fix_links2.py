import os

def fix_links():
    files_to_fix = ['static/js/script.js', 'static/js/history_panel.js']
    for file in files_to_fix:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Replace all occurrences
            text = text.replace(
                '<a href="/report/${record.id}" class="case-link">查看报告</a>',
                '<a href="/report/${record.id}" target="_blank" class="case-link" onclick="event.stopPropagation();">查看报告</a>'
            )
            
            with open(file, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Fixed {file}")

fix_links()
