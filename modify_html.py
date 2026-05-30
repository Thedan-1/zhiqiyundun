import os
def insert_graph_link(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    inject_str = '<div style="text-align: right; margin-bottom: 20px;"><a href="{{ url_for(\'q4_knowledge_graph\') }}" target="_blank" class="btn btn-primary" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;"><i class="fas fa-project-diagram"></i> 在多维视图中探索完整图谱</a></div>'
    
    if '<div class="qichacha-container">' in text and 'project-diagram' not in text:
        text = text.replace('<div class="qichacha-container">', '<div class="qichacha-container">\n        ' + inject_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'Done for {filepath}')

insert_graph_link('templates/smart_search/q1_qiyexinxihecha.html')
insert_graph_link('templates/smart_search/q1_gongshangxinxi.html')
insert_graph_link('templates/smart_search/q1_mohusousuo.html')
