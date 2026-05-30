def run():
    path = 'templates/smart_search/q1_qiyexinxihecha.html'
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    script_tag = '<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>'
    if script_tag not in text:
        text = text.replace('{% block center_content %}', '{% block center_content %}\\n' + script_tag)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    
run()
