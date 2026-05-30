// static/js/history_panel.js

function updateHistoryAssessmentsTable(searchQuery = '') {
    const tableBody = document.getElementById('historyRecordsTableBody');
    if (!tableBody) return;

    const historyType = tableBody.dataset.historyType; // Get the history type from data attribute
    let apiUrl = '';

    // Map Flask endpoint names to specific history APIs
    // Note: Flask endpoint names are used as data-history-type
    if (historyType === 'index') {
        apiUrl = '/api/history/assessments';
    } else if (historyType === 'q1_qiyexinxihecha') {
        apiUrl = '/api/history/qcc_verify';
    } else if (historyType === 'q1_gongshangxinxi') {
        apiUrl = '/api/history/industrial_info';
    } else if (historyType === 'q1_mohusousuo') {
        apiUrl = '/api/history/fuzzy_search';
    } else if (historyType === 'q1_shuihaokaipiao') {
        apiUrl = '/api/history/tax_invoice';
    } else if (historyType === 'q2_kehushenfenshibie') {
        apiUrl = '/api/history/kyc_verify';
    } else if (historyType === 'q2_zizhizhengshu') {
        apiUrl = '/api/history/certification';
    } else if (historyType === 'q2_shangbiaochaxun') {
        apiUrl = '/api/history/trademark';
    } else if (historyType === 'q2_zhuanlichaxun') {
        apiUrl = '/api/history/patent';
    } else if (historyType === 'q2_nianbaoxinxi') {
        apiUrl = '/api/history/annual_report';
    } else if (historyType === 'q3_zonghefengxianpaizha') { // New: Comprehensive Risk history
        apiUrl = '/api/history/comprehensive_risk';
    } else if (historyType === 'q3_shixinhecha') { // New: Shixin Check history
        apiUrl = '/api/history/shixin_check';
    } else if (historyType === 'q3_jingyinyichanghecha') { // New: Exception Check history
        apiUrl = '/api/history/exception_check';
    } else if (historyType === 'q3_beizhixingrenhecha') { // New: Zhixing Check history
        apiUrl = '/api/history/zhixing_check';
    } else if (historyType === 'q3_yanzhongweifahecha') { // New: Serious Illegal Check history
        apiUrl = '/api/history/serious_illegal_check';
    } else if (historyType === 'q3_caipanwenshuhecha') { // New: Judgment Doc Check history
        apiUrl = '/api/history/judgment_doc_check';
    }
    // Add more conditions for other smart search pages as needed
    else {
        console.warn(`Unknown history type: ${historyType}. Cannot fetch history.`);
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--warning-color);">未知历史类型，无法加载。</td></tr>';
        return;
    }

    tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在加载历史记录...</td></tr>';

    fetch(`${apiUrl}?query=${encodeURIComponent(searchQuery)}`)
        .then(response => response.json())
        .then(records => {
            tableBody.innerHTML = '';
            if (records.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #a3c3ff;">暂无历史记录</td></tr>';
                return;
            }

            records.forEach(record => {
                const row = tableBody.insertRow();
                row.innerHTML = `
                    <td>${record.companyName}</td>
                    <td><span style="color: ${record.riskColor};">${record.riskLevel}</span></td>
                    <td>${record.time}</td>
                    <td><a href="/report/${record.id}" target="_blank" class="case-link">查看报告</a></td>
                `;
            });
        })
        .catch(error => {
            console.error('Failed to fetch history assessment records:', error);
            tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--danger-color);">加载历史记录失败</td></tr>';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if history panel elements exist
    const historyTableBody = document.getElementById('historyRecordsTableBody');
    if (historyTableBody) {
        updateHistoryAssessmentsTable(); // Initial load

        const historySearchInput = document.getElementById('historySearchInput');
        if (historySearchInput) {
            historySearchInput.addEventListener('input', function() {
                updateHistoryAssessmentsTable(this.value);
            });
        }
    }
});