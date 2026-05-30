// static/js/script.js

// Initialize charts
let radarChart = null;
let riskDistributionChart = null;

// Initialize radar chart
function initRadarChart(initialValues = [0, 0, 0, 0]) {
    const radarChartDom = document.getElementById('radarChart');
    if (!radarChartDom) {
        console.warn("Radar chart element not found.");
        return;
    }
    // Destroy old ECharts instance if exists
    if (echarts.getInstanceByDom(radarChartDom)) {
        echarts.getInstanceByDom(radarChartDom).dispose();
    }
    radarChart = echarts.init(radarChartDom);

    const option = {
        title: {
            text: '风险维度分析',
            left: 'center',
            textStyle: {
                color: '#e0f0ff',
                fontSize: 16
            }
        },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                return `${params.name}: ${params.value[params.dataIndex]}分`;
            },
            textStyle: {
                color: '#e0f0ff'
            },
            backgroundColor: 'rgba(15, 41, 66, 0.9)',
            borderColor: 'var(--secondary-color)',
            borderWidth: 1
        },
        radar: {
            indicator: [
                { name: '财务风险', max: 100 },
                { name: '市场风险', max: 100 },
                { name: '管理风险', max: 100 },
                { name: '外部风险', max: 100 }
            ],
            axisName: {
                color: '#e0f0ff',
                fontSize: 14
            },
            splitLine: {
                lineStyle: {
                    color: 'var(--border-color-light)'
                }
            },
            splitArea: {
                areaStyle: {
                    color: ['rgba(23, 162, 184, 0.05)', 'rgba(23, 162, 184, 0.15)'] // Adjusted based on new info-color
                }
            },
            axisLine: {
                lineStyle: {
                    color: 'rgba(23, 162, 184, 0.5)' // Adjusted based on new info-color
                }
            }
        },
        series: [{
            type: 'radar',
            name: '风险评估',
            data: [{
                value: initialValues,
                name: '风险评估'
            }],
            lineStyle: {
                color: 'var(--accent-color)', // Adjusted
                width: 2
            },
            areaStyle: {
                opacity: 0.7,
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                    offset: 0, color: 'rgba(0, 212, 255, 0.8)' // Adjusted
                }, {
                    offset: 1, color: 'rgba(0, 212, 255, 0.3)' // Adjusted
                }])
            },
            itemStyle: {
                color: 'var(--accent-color)', // Adjusted
                borderColor: '#fff',
                borderWidth: 1
            },
            symbolSize: 8
        }]
    };

    radarChart.setOption(option);
    radarChart.resize();
}

// Calculate preliminary risk score
function calculateRiskScore(data) {
    const weights = {
        financial: 0.4,
        market: 0.3,
        management: 0.2,
        external: 0.1
    };

    const revenue = parseFloat(data.revenue) || 0;
    const profitMargin = parseFloat(data.profitMargin) || 0;
    const debtRatio = parseFloat(data.debtRatio) || 0;
    const cashFlow = data.cashFlow;
    const marketShare = parseFloat(data.marketShare) || 0;
    const competitors = parseFloat(data.competitors) || 0;
    const customerChurn = parseFloat(data.customerChurn) || 0;
    const employeeTurnover = parseFloat(data.employeeTurnover) || 0;
    const managementStability = data.managementStability;
    const innovationAbility = data.innovationAbility;
    const industryRisk = data.industryRisk;
    const policySupport = data.policySupport;

    let industryRiskScore = 0;
    if (industryRisk === 'high') {
        industryRiskScore = 100;
    } else if (industryRisk === 'medium') {
        industryRiskScore = 50;
    } else {
        industryRiskScore = 0;
    }

    let policySupportScore = 0;
    if (policySupport === 'no') {
        policySupportScore = 100;
    } else {
        policySupportScore = 0;
    }

    let financialRisk = (
        (100 - Math.min(Math.max(profitMargin, 0), 100)) * 0.4 +
        Math.min(Math.max(debtRatio, 0), 100) * 0.4 +
        (cashFlow === 'negative' ? 100 : 0) * 0.2
    );
    financialRisk = Math.min(Math.max(financialRisk, 0), 100);

    let marketRisk = (
        (100 - Math.min(Math.max(marketShare, 0), 100)) * 0.5 +
        Math.min(Math.max(competitors * 5, 0), 100) * 0.5 +
        Math.min(Math.max(customerChurn, 0), 100) * 0.5
    );
    marketRisk = Math.min(Math.max(marketRisk, 0), 100);

    let managementRisk = (
        Math.min(Math.max(employeeTurnover, 0), 100) * 0.5 +
        (managementStability === 'low' ? 100 : managementStability === 'medium' ? 50 : 0) * 0.3 +
        (innovationAbility === 'low' ? 100 : innovationAbility === 'medium' ? 50 : 0) * 0.2
    );
    managementRisk = Math.min(Math.max(managementRisk, 0), 100);

    let externalRisk = (
        industryRiskScore * 0.7 +
        policySupportScore * 0.3
    );
    externalRisk = Math.min(Math.max(externalRisk, 0), 100);

    const totalScore = (
        financialRisk * weights.financial +
        marketRisk * weights.market +
        managementRisk * weights.management +
        externalRisk * weights.external
    );

    return {
        total: Math.round(totalScore),
        financial: Math.round(financialRisk),
        market: Math.round(marketRisk),
        management: Math.round(managementRisk),
        external: Math.round(externalRisk)
    };
}

// Update risk level display
function updateRiskLevel(score) {
    const riskLevelElement = document.getElementById('riskLevel');
    const riskScoreElement = document.getElementById('riskScore');

    if (!riskLevelElement || !riskScoreElement) return;

    if (score === '--' || isNaN(score)) {
        riskLevelElement.textContent = '--';
        riskLevelElement.className = 'risk-level';
        riskScoreElement.className = 'risk-score';
        riskScoreElement.textContent = '--';
        return;
    }

    if (score >= 70) {
        riskLevelElement.textContent = '高风险';
        riskLevelElement.className = 'risk-level level-high';
        riskScoreElement.className = 'risk-score risk-high';
    } else if (score >= 40) {
        riskLevelElement.textContent = '中风险';
        riskLevelElement.className = 'risk-level level-medium';
        riskScoreElement.className = 'risk-score risk-medium';
    } else {
        riskLevelElement.textContent = '低风险';
        riskLevelElement.className = 'risk-level level-low';
        riskScoreElement.className = 'risk-score risk-low';
    }

    riskScoreElement.textContent = score;
}

// Update dashboard statistics
async function updateDashboardStats() {
    try {
        const response = await fetch('/api/dashboard_stats');
        const stats = await response.json();

        // These elements are in the persistent left panel
        document.getElementById('totalAssessments').textContent = stats.totalAssessments;
        document.getElementById('highRiskCount').textContent = stats.highRiskCount;
        document.getElementById('todayAssessments').textContent = stats.todayAssessments;

        // These elements are in the main content area (index.html specific)
        // Check if they exist before updating, as they might not be present on other pages
        if (document.getElementById('controlTodayAssessments')) {
            document.getElementById('controlTodayAssessments').textContent = stats.todayAssessments;
        }
        if (document.getElementById('controlHighRiskCount')) {
            document.getElementById('controlHighRiskCount').textContent = stats.highRiskCount;
        }
        if (document.getElementById('controlAvgTotalRisk')) {
            document.getElementById('controlAvgTotalRisk').textContent = stats.avgTotalRisk;
        }

        if (document.getElementById('statTodayAssessments')) {
            document.getElementById('statTodayAssessments').textContent = stats.todayAssessments;
        }
        if (document.getElementById('statHighRiskCount')) {
            document.getElementById('statHighRiskCount').textContent = stats.highRiskCount;
        }
        if (document.getElementById('statAvgTotalRisk')) {
            document.getElementById('statAvgTotalRisk').textContent = stats.avgTotalRisk;
        }

        if (document.getElementById('highRiskPercentage')) {
            const highRiskPercentage = stats.totalAssessments > 0 ? ((stats.highRiskCount / stats.totalAssessments) * 100).toFixed(1) : 0;
            document.getElementById('highRiskPercentage').textContent = highRiskPercentage;
        }

        // The pie chart is now in the persistent right panel
        initializePieChart(stats.riskDistribution);

    } catch (error) {
        console.error('Failed to fetch dashboard statistics:', error);
    }
}

// Update recent assessments table
async function updateRecentAssessmentsTable() {
    try {
        const response = await fetch('/api/recent_assessments');
        const records = await response.json();
        const tableBody = document.getElementById('recentAssessmentsTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        if (records.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">暂无评估记录</td></tr>'; // Adjusted colspan
            return;
        }

        records.forEach(record => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td>${record.companyName}</td>
                <td><span style="color: ${record.riskColor};">${record.riskLevel}</span></td>
                <td>${record.time}</td>
                <td><a href="/report/${record.id}" target="_blank" class="case-link">查看报告</a></td> <!-- Added view report link -->
            `;
        });
    } catch (error) {
        console.error('Failed to fetch recent assessment records:', error);
    }
}


// Event listener for the analyze button (only exists on index.html)
document.getElementById('analyzeBtn')?.addEventListener('click', async function() {
    const data = {
        companyName: document.getElementById('companyName').value,
        revenue: document.getElementById('revenue').value,
        profitMargin: document.getElementById('profitMargin').value,
        debtRatio: document.getElementById('debtRatio').value,
        cashFlow: document.getElementById('cashFlow').value,
        marketShare: document.getElementById('marketShare').value,
        competitors: document.getElementById('competitors').value,
        customerChurn: document.getElementById('customerChurn').value,
        employeeTurnover: document.getElementById('employeeTurnover').value,
        managementStability: document.getElementById('managementStability').value,
        innovationAbility: document.getElementById('innovationAbility').value,
        industryRisk: document.getElementById('industryRisk').value,
        policySupport: document.getElementById('policySupport').value
    };

    if (data.companyName.trim() === '') {
        alert('请填写公司名称！');
        return;
    }
    for (const key in data) {
        if (key !== 'companyName' && (data[key] === '' || data[key] === null)) {
            alert('请填写所有风险评估字段！');
            return;
        }
    }

    const preliminaryRiskData = calculateRiskScore(data);

    const dataToSend = {
        ...data,
        financialRisk: preliminaryRiskData.financial,
        marketRisk: preliminaryRiskData.market,
        managementRisk: preliminaryRiskData.management,
        externalRisk: preliminaryRiskData.external,
        totalRisk: preliminaryRiskData.total
    };

    const analyzeBtn = document.getElementById('analyzeBtn');
    const originalBtnText = analyzeBtn.innerHTML;
    analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 评估中...';
    analyzeBtn.disabled = true;

    // Show initial loading states and hide previous results
    document.getElementById('riskAnalysisResultCard').style.display = 'none';
    document.getElementById('riskFactorsCard').style.display = 'none';
    document.getElementById('suggestionsCard').style.display = 'none';

    document.getElementById('riskFactors').innerHTML = '<p class="suggestion-item">正在分析风险因素...</p>';
    document.getElementById('suggestions').innerHTML = '<p class="suggestion-item">正在生成改进建议...</p>';
    updateRiskLevel('--');
    initRadarChart();

    try {
        const response = await fetch('/api/analyze_risk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dataToSend)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        analyzeBtn.innerHTML = originalBtnText;
        analyzeBtn.disabled = false;

        if (result.success) {
            // Show result cards
            document.getElementById('riskAnalysisResultCard').style.display = 'block';
            document.getElementById('riskFactorsCard').style.display = 'block';
            document.getElementById('suggestionsCard').style.display = 'block';

            updateRiskLevel(result.totalRisk);
            initRadarChart([result.financialRisk, result.marketRisk, result.managementRisk, result.externalRisk]);
            radarChart.resize();

            document.getElementById('riskFactors').innerHTML = result.riskFactorsHtml;
            document.getElementById('suggestions').innerHTML = result.suggestionsHtml;

            updateDashboardStats();
            updateRecentAssessmentsTable();

            // Store last assessment data for chatbot
            sessionStorage.setItem('lastAssessmentData', JSON.stringify({
                type: 'dashboard_assessment',
                companyName: data.companyName,
                inputData: data,
                preliminaryRisk: preliminaryRiskData,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

        } else {
            console.error('Risk analysis failed:', result.error);
            document.getElementById('riskFactors').innerHTML = `<p class="suggestion-item" style="color: var(--danger-color);">风险分析失败: ${result.error}</p>`;
            document.getElementById('suggestions').innerHTML = '<p class="suggestion-item" style="color: var(--danger-color);">未能获取AI改进建议。</p>';
            updateRiskLevel('--');
            initRadarChart();
            radarChart.resize();
        }
    } catch (error) {
        analyzeBtn.innerHTML = originalBtnText;
        analyzeBtn.disabled = false;

        console.error('Error calling backend API:', error);
        document.getElementById('riskFactors').innerHTML = `<p class="suggestion-item" style="color: var(--danger-color);">请求出错，请稍后再试。错误: ${error.message}</p>`;
        document.getElementById('suggestions').innerHTML = '<p class="suggestion-item" style="color: var(--danger-color);">未能获取AI改进建议。</p>';
        updateRiskLevel('--');
        initRadarChart();
        radarChart.resize();
    }
});


// Dashboard risk board data (replace legacy map view)
const riskBoardCompanies = [
        { name: "涧石科技有限公司", lat: 39.9042, lng: 116.4074, city: "北京", risk: "low", description: "财务健康状况良好，现金流充裕，负债率低，市场份额稳步增长，管理团队稳定且具备创新能力。" },
        { name: "云岫商贸有限公司", lat: 31.2304, lng: 121.4737, city: "上海", risk: "medium", description: "市场竞争激烈，客户流失率略高，但管理层积极应对，正在探索新的市场策略和产品线。" },
        { name: "磐石基建有限公司", lat: 23.1291, lng: 113.2644, city: "广州", risk: "high", description: "项目回款周期长，资金压力大，负债率高，且面临行业政策收紧的外部风险，需警惕现金流断裂风险。" },
        { name: "物联物流有限公司", lat: 22.5431, lng: 114.0579, city: "深圳", risk: "high", description: "资金链紧张，外部环境复杂多变，竞争对手众多，员工流动率较高，管理层稳定性有待加强。" },
        { name: "和光食品有限公司", lat: 30.5728, lng: 104.0668, city: "成都", risk: "medium", description: "管理层稳定性一般，创新能力不足，市场份额增长缓慢，但行业整体风险较低，有一定政策支持。" },
        { name: "启明教育有限公司", lat: 34.3416, lng: 108.9398, city: "西安", risk: "low", description: "业务稳定增长，利润率高，现金流充裕，政策支持良好，客户忠诚度高，员工团队稳定且富有创新精神。" },
        { name: "山岚建筑有限公司", lat: 36.0611, lng: 120.3826, city: "青岛", risk: "high", description: "负债率高，现金流紧张，新项目获取困难，市场份额萎缩，行业风险大，急需进行战略调整和风险控制。" },
        { name: "知微医疗有限公司", lat: 38.0377, lng: 121.5156, city: "大连", risk: "medium", description: "研发投入压力大，市场份额波动较大，竞争激烈，但公司拥有核心技术和稳定的管理团队，具备发展潜力。" },
        { name: "青野农业有限公司", lat: 32.0603, lng: 118.7969, city: "南京", risk: "low", description: "政策支持良好，客户流失率低，产品质量稳定，市场需求旺盛，财务状况健康，管理高效，创新能力强。" },
        { name: "方舟电子有限公司", lat: 30.2741, lng: 120.1551, city: "杭州", risk: "high", description: "技术更新压力大，员工流动率高，市场竞争异常激烈，利润率下降，现金流承压，亟需提升创新能力和市场竞争力。" },
        { name: "天府科技", lat: 29.5630, lng: 106.5516, city: "重庆", risk: "medium", description: "新兴市场，竞争加剧，产品同质化严重，但公司积极拓展新业务，管理团队年轻有活力，创新意识较强。" },
        { name: "楚汉制造", lat: 30.5928, lng: 114.3055, city: "武汉", risk: "low", description: "供应链稳定，利润率高，负债率低，市场份额稳固，管理层经验丰富，员工忠诚度高，是行业内的佼佼者。" },
        { name: "齐鲁能源", lat: 36.6687, lng: 117.0009, city: "济南", risk: "high", description: "环保政策收紧，行业风险大，产能过剩，市场需求不足，财务状况恶化，急需转型升级，寻找新的增长点。" },
        { name: "中原物流", lat: 34.7466, lng: 113.6253, city: "郑州", risk: "medium", description: "运输成本上涨，客户需求变化快，竞争激烈，但公司通过技术升级和优化路线，逐步提升服务效率和市场竞争力。" },
        { name: "东北重工", lat: 41.7922, lng: 123.4328, city: "沈阳", risk: "high", description: "产能过剩，市场需求不足，订单量持续下滑，利润空间被压缩，企业面临较大的经营风险和转型压力。" }
    ];

function getRiskLabel(risk) {
    if (risk === 'high') return '高风险';
    if (risk === 'medium') return '中风险';
    return '低风险';
}

function renderRiskBoard(companies) {
    const listDom = document.getElementById('riskCompaniesList');
    if (!listDom) {
        return;
    }

    if (!companies.length) {
        listDom.innerHTML = '<div class="risk-company-empty">没有匹配到企业，请调整筛选条件或关键词。</div>';
        return;
    }

    const cards = companies.map(company => `
        <div class="risk-company-card">
            <div class="risk-company-head">
                <div class="risk-company-name">${company.name}</div>
                <div class="risk-company-level level-${company.risk}">${getRiskLabel(company.risk)}</div>
            </div>
            <div class="risk-company-city"><i class="fas fa-location-dot"></i> ${company.city}</div>
            <div class="risk-company-desc">${company.description}</div>
        </div>
    `).join('');

    listDom.innerHTML = cards;
}

function initializeRiskBoard() {
    if (!document.getElementById('riskOverviewPanel')) {
        return;
    }

    const searchInput = document.getElementById('searchInput');
    const riskFilter = document.getElementById('riskFilter');

    const applyFilters = () => {
        const searchTerm = (searchInput?.value || '').toLowerCase().trim();
        const selectedRisk = riskFilter?.value || 'all';

        const filtered = riskBoardCompanies.filter(company => {
            const matchText = !searchTerm ||
                company.name.toLowerCase().includes(searchTerm) ||
                company.city.toLowerCase().includes(searchTerm);
            const matchRisk = selectedRisk === 'all' || company.risk === selectedRisk;
            return matchText && matchRisk;
        });

        renderRiskBoard(filtered);
    };

    renderRiskBoard(riskBoardCompanies);
    searchInput?.addEventListener('input', applyFilters);
    riskFilter?.addEventListener('change', applyFilters);
}


// Initialize pie chart (now in persistent right panel)
function initializePieChart(riskData = { low: 0, medium: 0, high: 0 }) {
    const ctx = document.getElementById('riskDistributionChart');
    if (!ctx) {
        console.warn("Risk distribution chart element not found.");
        return;
    }

    if (riskDistributionChart) {
        riskDistributionChart.destroy();
    }

    // 获取计算后的CSS变量值
    const style = getComputedStyle(document.documentElement);
    const successColor = style.getPropertyValue('--success-color').trim();
    const warningColor = style.getPropertyValue('--warning-color').trim();
    const dangerColor = style.getPropertyValue('--danger-color').trim();
    const cardBgColor = style.getPropertyValue('--card-bg').trim();
    const textColor = style.getPropertyValue('--text-color').trim();
    const secondaryColor = style.getPropertyValue('--secondary-color').trim();

    riskDistributionChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['低风险', '中风险', '高风险'],
            datasets: [{
                data: [riskData.low, riskData.medium, riskData.high],
                backgroundColor: [
                    successColor, // 使用显式获取的颜色值
                    warningColor, // 使用显式获取的颜色值
                    dangerColor   // 使用显式获取的颜色值
                ],
                borderColor: cardBgColor, // 使用显式获取的颜色值
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: textColor, // 使用显式获取的颜色值
                        font: {
                            size: 14
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed !== null) {
                                label += context.parsed + ' 家';
                            }
                            return label;
                        }
                    },
                    backgroundColor: cardBgColor, // 使用显式获取的颜色值
                    titleColor: secondaryColor, // 使用显式获取的颜色值
                    bodyColor: textColor, // 使用显式获取的颜色值
                    borderColor: secondaryColor, // 使用显式获取的颜色值
                    borderWidth: 1
                }
            }
        }
    });
}


// Execute on page load (for elements in base.html and current page's center_content)
window.addEventListener('load', function() {
    // Only if on the index page, initialize index-specific right panel elements
    // Check if the current path is the index page
    if (window.location.pathname === '/') {
        if (document.getElementById('riskDistributionChart') && document.getElementById('recentAssessmentsTableBody')) {
            initializePieChart();
            updateDashboardStats(); // This also updates totalAssessments, highRiskCount, todayAssessments in left panel
            updateRecentAssessmentsTable();
        }

        initializeRiskBoard();
        if (document.getElementById('radarChart')) { // Only for index.html
            initRadarChart();
        }
    }
});