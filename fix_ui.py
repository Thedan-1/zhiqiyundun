# -*- coding: utf-8 -*-
with open('D:/jingsai/2025中国高校计算机大赛/AIGC创新赛决赛/智企云盾/templates/admin/audit_logs.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add ECharts before the table
echart_html = '''
    <div class="card" style="margin-bottom: 20px;">
        <div class="panel-title">
            <i class="fas fa-chart-line"></i> 访问与操作统计
        </div>
        <div class="card-content">
            <div id="auditChart" style="width: 100%; height: 350px;"></div>
        </div>
    </div>
'''

if 'auditChart' not in text:
    text = text.replace('<div class="card">', echart_html + '\n    <div class="card">', 1)

# Add echarts script
echart_script = '''
{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    var chartDom = document.getElementById('auditChart');
    if (chartDom) {
        var myChart = echarts.init(chartDom);
        var option = {
            tooltip: { trigger: 'axis' },
            legend: { data: ['操作次数'] },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'category', boundaryGap: false, data: ['5日前', '4日前', '3日前', '前天', '昨天', '今天'] },
            yAxis: { type: 'value' },
            series: [
                {
                    name: '操作次数',
                    type: 'line',
                    smooth: true,
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: 'rgba(58,134,255,0.8)' },
                            { offset: 1, color: 'rgba(58,134,255,0.1)' }
                        ])
                    },
                    itemStyle: { color: '#3a86ff' },
                    data: [14, 32, 21, 54, 90, 130]
                }
            ]
        };
        myChart.setOption(option);
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }
});
</script>
{% endblock %}
'''
if '{% block scripts %}' not in text and 'auditChart' in echart_html:
    text = text + echart_script

with open('D:/jingsai/2025中国高校计算机大赛/AIGC创新赛决赛/智企云盾/templates/admin/audit_logs.html', 'w', encoding='utf-8') as f:
    f.write(text)
