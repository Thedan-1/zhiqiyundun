# -*- coding: utf-8 -*-
with open('D:/jingsai/2025中国高校计算机大赛/AIGC创新赛决赛/智企云盾/templates/admin/users.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add ECharts before the table
echart_html = '''
    <div class="row" style="display: flex; gap: 20px; margin-bottom: 20px;">
        <div class="card" style="flex: 1; margin: 0;">
            <div class="panel-title">
                <i class="fas fa-chart-pie"></i> 用户角色分布
            </div>
            <div class="card-content">
                <div id="roleChart" style="width: 100%; height: 300px;"></div>
            </div>
        </div>
        <div class="card" style="flex: 1; margin: 0;">
            <div class="panel-title">
                <i class="fas fa-chart-bar"></i> 活跃用户趋势
            </div>
            <div class="card-content">
                <div id="activeChart" style="width: 100%; height: 300px;"></div>
            </div>
        </div>
    </div>
'''

if 'roleChart' not in text:
    text = text.replace('<div class="card">', echart_html + '\n    <div class="card">', 1)

# Add echarts script
echart_script = '''
{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Role Chart
    var roleChartDom = document.getElementById('roleChart');
    if (roleChartDom) {
        var roleChart = echarts.init(roleChartDom);
        var roleOption = {
            tooltip: { trigger: 'item' },
            legend: { orient: 'vertical', left: 'left' },
            series: [{
                name: '用户角色',
                type: 'pie',
                radius: '50%',
                data: [
                    { value: 2, name: '超级管理员' },
                    { value: 15, name: '普通管理员' },
                    { value: 145, name: '初级用户' },
                    { value: 48, name: '认证企业用户' }
                ],
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };
        roleChart.setOption(roleOption);
    }
    
    // Active Chart
    var activeChartDom = document.getElementById('activeChart');
    if (activeChartDom) {
        var activeChart = echarts.init(activeChartDom);
        var activeOption = {
            tooltip: { trigger: 'axis' },
            xAxis: { type: 'category', data: ['一月', '二月', '三月', '四月', '五月', '六月'] },
            yAxis: { type: 'value' },
            series: [{
                data: [120, 200, 150, 80, 70, 110],
                type: 'bar',
                showBackground: true,
                backgroundStyle: { color: 'rgba(180, 180, 180, 0.2)' },
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#83bff6' },
                        { offset: 0.5, color: '#188df0' },
                        { offset: 1, color: '#188df0' }
                    ])
                }
            }]
        };
        activeChart.setOption(activeOption);
    }
    
    window.addEventListener('resize', function() {
        if(roleChart) roleChart.resize();
        if(activeChart) activeChart.resize();
    });
});
</script>
{% endblock %}
'''
if '{% block scripts %}' not in text and 'roleChart' in echart_html:
    text = text + echart_script

with open('D:/jingsai/2025中国高校计算机大赛/AIGC创新赛决赛/智企云盾/templates/admin/users.html', 'w', encoding='utf-8') as f:
    f.write(text)
