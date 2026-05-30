import re

def update_html():
    with open('templates/smart_search/q1_qiyexinxihecha.html', 'r', encoding='utf-8') as f:
        text = f.read()

    echarts_html = '''
        <!-- 相关图谱 -->
        <div class="card" id="knowledgeGraphCard" style="display: none;">
            <div class="panel-title">
                <i class="fas fa-project-diagram"></i> 企业关系图谱分析
            </div>
            <div class="card-content" style="position: relative; min-height: 600px;">
                <div id="knowledgeGraph" style="width: 100%; height: 600px; border-radius: 4px; background: #f8f9fa;"></div>
            </div>
        </div>
    </div>
'''

    echarts_script = '''
    <script>
        let chartInstance = null;

        const mockGraphData = {
            nodes: [
                { id: '1', name: '核心企业', category: 0, symbolSize: 60, val: '核心企业' },
                { id: '2', name: '全资子公司A', category: 1, symbolSize: 40, val: '全资子公司(100%)' },
                { id: '3', name: '控股子公司B', category: 1, symbolSize: 40, val: '控股子公司(100%)' },
                { id: '4', name: '投资管理平台', category: 1, symbolSize: 35, val: '股权投资平台' },
                { id: '5', name: '被投企业(下游)', category: 2, symbolSize: 30, val: ' 被投资企业(下游)' },
                { id: '6', name: '被投企业C', category: 2, symbolSize: 30, val: ' 被投资企业' },
                { id: '7', name: '被投企业D', category: 2, symbolSize: 30, val: '关联被投资企业' },
                { id: '8', name: '法定代表人', category: 3, symbolSize: 45, val: '法定代表人/高管' },
                { id: '9', name: '管理层成员', category: 3, symbolSize: 35, val: '高管' },
                { id: '10', name: '上游硬件供应商', category: 4, symbolSize: 30, val: '上游硬件供应商' },
                { id: '11', name: '基础设施供应商', category: 4, symbolSize: 30, val: 'IaaS基础设施供应商' },
                { id: '12', name: '被投企业E', category: 2, symbolSize: 30, val: '被投资企业' },
                { id: '13', name: '被投企业F', category: 2, symbolSize: 20, val: '被投资企业' },
                { id: '14', name: '控股企业G', category: 1, symbolSize: 35, val: '控股企业' },
                { id: '15', name: '海外被投企业', category: 2, symbolSize: 25, val: ' 海外被投企业' }
            ],
            links: [
                { source: '1', target: '2', name: '100%控股' },
                { source: '1', target: '3', name: '100%控股' },
                { source: '1', target: '4', name: '发起设立' },
                { source: '4', target: '5', name: '领投' },
                { source: '4', target: '6', name: '战略投资' },
                { source: '4', target: '7', name: '重要股东' },
                { source: '8', target: '1', name: '担任法定代表人' },
                { source: '9', target: '1', name: '高管/副总裁' },
                { source: '10', target: '1', name: '上游供应' },
                { source: '11', target: '1', name: '机房合作' },
                { source: '4', target: '12', name: '持股' },
                { source: '4', target: '13', name: '持股' },
                { source: '1', target: '14', name: '控股及业务整合' },
                { source: '4', target: '15', name: '股权收购' }
            ],
            categories: [
                { name: '核心企业' },
                { name: '控股/子公司' },
                { name: '对外投资/下游' },
                { name: '自然人/高管' },
                { name: '上游供应商' }
            ]
        };

        window.renderGraph = function(query) {
            if (!query) return;
            
            let targetCompany = mockGraphData.nodes[0];
            targetCompany.name = query; // Replace center node

            if (chartInstance != null) {
                chartInstance.dispose();
            }

            const dom = document.getElementById('knowledgeGraph');
            if(!dom) return;
            
            // support dark mode check dynamically within the current site context
            chartInstance = echarts.init(dom, document.body.classList.contains('dark-mode') ? 'dark' : null);
            
            const option = {
                title: {
                    text: '《' + query + '》商业关系网络',
                    top: 'bottom',
                    left: 'right'
                },
                tooltip: {
                    formatter: function (params) {
                        if (params.dataType === 'node') {
                            return params.data.name + '<br/>属性: ' + params.data.val;
                        } else if (params.dataType === 'edge') {
                            return params.data.name;
                        }
                    }
                },
                legend: [{
                    data: mockGraphData.categories.map(function (a) { return a.name; }),
                    orient: 'vertical',
                    left: '20',
                    top: '20'
                }],
                animationDuration: 1500,
                animationEasingUpdate: 'quinticInOut',
                series: [
                    {
                        name: '企业图谱',
                        type: 'graph',
                        layout: 'force',
                        data: mockGraphData.nodes.map(node => ({
                            ...node,
                            label: { show: node.symbolSize > 25 }
                        })),
                        links: mockGraphData.links,
                        categories: mockGraphData.categories,
                        roam: true,
                        draggable: true,
                        label: { position: 'right', formatter: '{b}' },
                        force: { repulsion: 800, edgeLength: 150, gravity: 0.1 },
                        edgeSymbol: ['circle', 'arrow'],
                        edgeSymbolSize: [4, 10],
                        edgeLabel: { show: true, fontSize: 12, formatter: "{c}" },
                        lineStyle: { color: 'source', curveness: 0.2, width: 2 },
                        emphasis: { focus: 'adjacency', lineStyle: { width: 5 } }
                    }
                ]
            };

            chartInstance.setOption(option);
        };
    </script>
'''

    if 'knowledgeGraphCard' not in text:
        text = text.replace(
            '</div>\n{% endblock %}\n\n{% block right_panel_content %}',
            echarts_html + '\n{% endblock %}\n\n{% block right_panel_content %}'
        )
        
        text = text.replace(
            "updateHistoryAssessmentsTable(); // Load history for this specific page\n            }\n        });\n    </script>\n{% endblock %}",
            "updateHistoryAssessmentsTable(); // Load history for this specific page\n            }\n        });\n    </script>" + echarts_script + "\n{% endblock %}"
        )

        with open('templates/smart_search/q1_qiyexinxihecha.html', 'w', encoding='utf-8') as f:
            f.write(text)

update_html()
print("Updated HTML")
