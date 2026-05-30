import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add route
new_route = """@app.route('/smart_search/q4_knowledge_graph', endpoint='q4_knowledge_graph')
@login_required
@permission_required('q4_knowledge_graph')
def q4_knowledge_graph():
    return render_template('smart_search/q4_knowledge_graph.html')

"""
# Find a place to insert the route, right before @app.route('/smart_search/q1_qiyexinxihecha'
if 'q4_knowledge_graph' not in content:
    content = content.replace("@app.route('/smart_search/q1_qiyexinxihecha'", new_route + "@app.route('/smart_search/q1_qiyexinxihecha'")

# 2. Add permission to permissions_data
p_data = "{'name': 'q4_knowledge_graph', 'description': '企业关系图谱'},"
if 'q4_knowledge_graph' not in content.split('permissions_data = [')[1][:1000]:
    content = content.replace("{'name': 'q1_qiyexinxihecha',", p_data + "\n            {'name': 'q1_qiyexinxihecha',")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("app.py patched!")