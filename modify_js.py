import re

def update_qichacha():
    with open('static/js/qichacha.js', 'r', encoding='utf-8') as f:
        text = f.read()

    # 1. Add knowledgeGraphCard to elements
    if 'knowledgeGraphCard' not in text:
        text = text.replace(
            "const qccSuggestionsCard = document.getElementById('qccSuggestionsCard');",
            "const qccSuggestionsCard = document.getElementById('qccSuggestionsCard');\n    const knowledgeGraphCard = document.getElementById('knowledgeGraphCard');"
        )
        
        text = text.replace(
            "if (qccSuggestionsCard) qccSuggestionsCard.style.display = 'block';",
            "if (qccSuggestionsCard) qccSuggestionsCard.style.display = 'block';\n    if (knowledgeGraphCard) knowledgeGraphCard.style.display = 'block';\n    if (typeof window.renderGraph === 'function') window.renderGraph(searchKey);"
        )

    with open('static/js/qichacha.js', 'w', encoding='utf-8') as f:
        f.write(text)

update_qichacha()
print("Updated qichacha.js")
