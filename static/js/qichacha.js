// static/js/qichacha.js

// Event listener for QCC Verify (企业信息核验)
document.getElementById('qccAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('qccSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('companyNameForBlueLM').value.trim();
    const qccResultDisplay = document.getElementById('qccResultDisplay');
    const qccRiskFactors = document.getElementById('qccRiskFactors');
    const qccSuggestions = document.getElementById('qccSuggestions');
    const qccAnalyzeBtn = document.getElementById('qccAnalyzeBtn');

    // 获取卡片元素
    const qccResultCard = document.getElementById('qccResultCard');
    const qccRiskFactorsCard = document.getElementById('qccRiskFactorsCard');
    const qccSuggestionsCard = document.getElementById('qccSuggestionsCard');
    const knowledgeGraphCard = document.getElementById('knowledgeGraphCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    qccAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    qccAnalyzeBtn.disabled = true;

    // 清空并显示加载状态
    qccResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询内部数据库数据...</p>';
    qccRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    qccSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见，即使BlueLM失败，QCC数据也应该显示
    if (qccResultCard) qccResultCard.style.display = 'block';
    if (qccRiskFactorsCard) qccRiskFactorsCard.style.display = 'block';
    if (qccSuggestionsCard) qccSuggestionsCard.style.display = 'block';
    if (knowledgeGraphCard) knowledgeGraphCard.style.display = 'block';
    if (typeof window.renderGraph === 'function') window.renderGraph(searchKey);

    let qccData = null; // 用于存储内部数据库原始数据

    try {
        const response = await fetch('/api/qichacha/verify_and_analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey, companyNameForBlueLM: companyNameForBlueLM })
        });

        if (!response.ok) {
            const errorData = await response.json();
            // 如果后端返回了QCC数据，即使BlueLM失败，也尝试渲染
            if (errorData.qccData) {
                qccData = errorData.qccData;
                renderQccVerifyData(qccData, qccResultDisplay);
            } else {
                qccResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            qccRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            qccSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error'); // 继续抛出错误，以便finally块执行
        }

        const result = await response.json();

        if (result.success) {
            qccData = result.qccData; // 保存内部数据库数据
            renderQccVerifyData(qccData, qccResultDisplay); // Specific render function for verify
            qccRiskFactors.innerHTML = result.riskFactorsHtml;
            qccSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'qcc_verification',
                searchKey: searchKey,
                companyName: qccData?.Name || searchKey,
                qccData: qccData,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            // Update history panel for this page
            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            // QCC API 调用成功但BlueLM失败 (后端返回success: false)
            qccData = result.qccData; // 尝试获取QCC数据，即使BlueLM失败
            if (qccData) {
                renderQccVerifyData(qccData, qccResultDisplay); // 仍然渲染QCC数据
            } else {
                qccResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            qccRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            qccSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Qichacha verify or AI analysis error:', error);
        // 如果整个请求都失败了 (例如网络错误)，则显示通用错误
        // 注意：如果errorData.qccData已渲染，这里不再覆盖qccResultDisplay
        if (!qccData) { // 只有当QCC数据也未获取到时才显示通用错误
            qccResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (qccRiskFactors.innerHTML.includes('正在进行AI风险分析')) { // 避免覆盖已有的AI错误信息
            qccRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (qccSuggestions.innerHTML.includes('正在生成AI改进建议')) { // 避免覆盖已有的AI错误信息
            qccSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        qccAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 查询并AI分析';
        qccAnalyzeBtn.disabled = false;
    }
});

// Event listener for Industrial Info Query
document.getElementById('industrialInfoAnalyzeBtn')?.addEventListener('click', async function() {
    const keyword = document.getElementById('companyNameIndustrial').value.trim();
    const industrialInfoResultDisplay = document.getElementById('industrialInfoResultDisplay');
    const industrialInfoRiskFactors = document.getElementById('industrialInfoRiskFactors');
    const industrialInfoSuggestions = document.getElementById('industrialInfoSuggestions');
    const industrialInfoAnalyzeBtn = document.getElementById('industrialInfoAnalyzeBtn');

    // 获取卡片元素
    const industrialInfoResultCard = document.getElementById('industrialInfoResultCard');
    const industrialInfoRiskFactorsCard = document.getElementById('industrialInfoRiskFactorsCard');
    const industrialInfoSuggestionsCard = document.getElementById('industrialInfoSuggestionsCard');

    if (!keyword) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    industrialInfoAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    industrialInfoAnalyzeBtn.disabled = true;
    industrialInfoResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询企业工商信息...</p>';
    industrialInfoRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    industrialInfoSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (industrialInfoResultCard) industrialInfoResultCard.style.display = 'block';
    if (industrialInfoRiskFactorsCard) industrialInfoRiskFactorsCard.style.display = 'block';
    if (industrialInfoSuggestionsCard) industrialInfoSuggestionsCard.style.display = 'block';

    let industrialInfoData = null;

    try {
        const response = await fetch('/api/qichacha/industrial_info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ keyword: keyword })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.qccData) {
                industrialInfoData = errorData.qccData;
                renderIndustrialInfoData(industrialInfoData, industrialInfoResultDisplay);
            } else {
                industrialInfoResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            industrialInfoRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            industrialInfoSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            industrialInfoData = result.qccData;
            renderIndustrialInfoData(industrialInfoData, industrialInfoResultDisplay);
            industrialInfoRiskFactors.innerHTML = result.riskFactorsHtml;
            industrialInfoSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'industrial_info_query',
                keyword: keyword,
                companyName: industrialInfoData?.Name || keyword,
                qccData: industrialInfoData,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            industrialInfoData = result.qccData;
            if (industrialInfoData) {
                renderIndustrialInfoData(industrialInfoData, industrialInfoResultDisplay);
            } else {
                industrialInfoResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            industrialInfoRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            industrialInfoSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Industrial info query or AI analysis error:', error);
        if (!industrialInfoData) {
            industrialInfoResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (industrialInfoRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            industrialInfoRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (industrialInfoSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            industrialInfoSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        industrialInfoAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        industrialInfoAnalyzeBtn.disabled = false;
    }
});

// Event listener for Fuzzy Search
document.getElementById('fuzzySearchAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('fuzzySearchKey').value.trim();
    const fuzzySearchResultDisplay = document.getElementById('fuzzySearchResultDisplay');
    const fuzzySearchRiskFactors = document.getElementById('fuzzySearchRiskFactors');
    const fuzzySearchSuggestions = document.getElementById('fuzzySearchSuggestions');
    const fuzzySearchAnalyzeBtn = document.getElementById('fuzzySearchAnalyzeBtn');

    // 获取卡片元素
    const fuzzySearchResultCard = document.getElementById('fuzzySearchResultCard');
    const fuzzySearchRiskFactorsCard = document.getElementById('fuzzySearchRiskFactorsCard');
    const fuzzySearchSuggestionsCard = document.getElementById('fuzzySearchSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词！');
        return;
    }

    fuzzySearchAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 模糊搜索并AI分析中...';
    fuzzySearchAnalyzeBtn.disabled = true;
    fuzzySearchResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行模糊搜索...</p>';
    fuzzySearchRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    fuzzySearchSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (fuzzySearchResultCard) fuzzySearchResultCard.style.display = 'block';
    if (fuzzySearchRiskFactorsCard) fuzzySearchRiskFactorsCard.style.display = 'block';
    if (fuzzySearchSuggestionsCard) fuzzySearchSuggestionsCard.style.display = 'block';

    let fuzzySearchDataList = null;

    try {
        const response = await fetch('/api/qichacha/fuzzy_search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.qccDataList) {
                fuzzySearchDataList = errorData.qccDataList;
                renderFuzzySearchData(fuzzySearchDataList, fuzzySearchResultDisplay);
            } else {
                fuzzySearchResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 搜索失败: ${errorData.error || '服务器错误'}</p>`;
            }
            fuzzySearchRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            fuzzySearchSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            fuzzySearchDataList = result.qccDataList;
            renderFuzzySearchData(fuzzySearchDataList, fuzzySearchResultDisplay);
            fuzzySearchRiskFactors.innerHTML = result.riskFactorsHtml;
            fuzzySearchSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'fuzzy_search_query',
                searchKey: searchKey,
                companyName: `模糊搜索: ${searchKey}`, // For chat context
                qccDataList: fuzzySearchDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            fuzzySearchDataList = result.qccDataList;
            if (fuzzySearchDataList) {
                renderFuzzySearchData(fuzzySearchDataList, fuzzySearchResultDisplay);
            } else {
                fuzzySearchResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 搜索失败: ${result.error}</p>`;
            }
            fuzzySearchRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            fuzzySearchSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Fuzzy search or AI analysis error:', error);
        if (!fuzzySearchDataList) {
            fuzzySearchResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (fuzzySearchRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            fuzzySearchRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (fuzzySearchSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            fuzzySearchSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        fuzzySearchAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 开始模糊搜索并AI分析';
        fuzzySearchAnalyzeBtn.disabled = false;
    }
});

// Event listener for Tax Invoice Query
document.getElementById('taxIdInvoiceAnalyzeBtn')?.addEventListener('click', async function() {
    const keyword = document.getElementById('taxIdInvoiceKey').value.trim();
    const taxIdInvoiceResultDisplay = document.getElementById('taxIdInvoiceResultDisplay');
    const taxIdInvoiceRiskFactors = document.getElementById('taxIdInvoiceRiskFactors');
    const taxIdInvoiceSuggestions = document.getElementById('taxIdInvoiceSuggestions');
    const taxIdInvoiceAnalyzeBtn = document.getElementById('taxIdInvoiceAnalyzeBtn');

    // 获取卡片元素
    const taxIdInvoiceResultCard = document.getElementById('taxIdInvoiceResultCard');
    const taxIdInvoiceRiskFactorsCard = document.getElementById('taxIdInvoiceRiskFactorsCard');
    const taxIdInvoiceSuggestionsCard = document.getElementById('taxIdInvoiceSuggestionsCard');

    if (!keyword) {
        alert('请输入查询关键字（公司名称）！');
        return;
    }

    taxIdInvoiceAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    taxIdInvoiceAnalyzeBtn.disabled = true;
    taxIdInvoiceResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询税号开票信息...</p>';
    taxIdInvoiceRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    taxIdInvoiceSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (taxIdInvoiceResultCard) taxIdInvoiceResultCard.style.display = 'block';
    if (taxIdInvoiceRiskFactorsCard) taxIdInvoiceRiskFactorsCard.style.display = 'block';
    if (taxIdInvoiceSuggestionsCard) taxIdInvoiceSuggestionsCard.style.display = 'block';

    let taxIdInvoiceData = null;

    try {
        const response = await fetch('/api/qichacha/tax_invoice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ keyword: keyword })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.qccData) {
                taxIdInvoiceData = errorData.qccData;
                renderTaxInvoiceData(taxIdInvoiceData, taxIdInvoiceResultDisplay);
            } else {
                taxIdInvoiceResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            taxIdInvoiceRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            taxIdInvoiceSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            taxIdInvoiceData = result.qccData;
            renderTaxInvoiceData(taxIdInvoiceData, taxIdInvoiceResultDisplay);
            taxIdInvoiceRiskFactors.innerHTML = result.riskFactorsHtml;
            taxIdInvoiceSuggestions.innerHTML = result.suggestionsHtml;

            document.getElementById('taxIdInvoiceResultCard').style.display = 'block';
            document.getElementById('taxIdInvoiceRiskFactorsCard').style.display = 'block';
            document.getElementById('taxIdInvoiceSuggestionsCard').style.display = 'block';

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'tax_invoice_query',
                keyword: keyword,
                companyName: taxIdInvoiceData?.Name || keyword,
                qccData: taxIdInvoiceData,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            taxIdInvoiceData = result.qccData;
            if (taxIdInvoiceData) {
                renderTaxInvoiceData(taxIdInvoiceData, taxIdInvoiceResultDisplay);
            } else {
                taxIdInvoiceResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            taxIdInvoiceRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            taxIdInvoiceSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Tax invoice query or AI analysis error:', error);
        if (!taxIdInvoiceData) {
            taxIdInvoiceResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (taxIdInvoiceRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            taxIdInvoiceRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (taxIdInvoiceSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            taxIdInvoiceSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        taxIdInvoiceAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        taxIdInvoiceAnalyzeBtn.disabled = false;
    }
});

// Event listener for KYC Verify Query (客户身份识别)
document.getElementById('kycAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('kycSearchKey').value.trim();
    const kycResultDisplay = document.getElementById('kycResultDisplay');
    const kycRiskFactors = document.getElementById('kycRiskFactors');
    const kycSuggestions = document.getElementById('kycSuggestions');
    const kycAnalyzeBtn = document.getElementById('kycAnalyzeBtn');

    // 获取卡片元素
    const kycResultCard = document.getElementById('kycResultCard');
    const kycRiskFactorsCard = document.getElementById('kycRiskFactorsCard');
    const kycSuggestionsCard = document.getElementById('kycSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    kycAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    kycAnalyzeBtn.disabled = true;
    kycResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询客户身份识别信息...</p>';
    kycRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    kycSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (kycResultCard) kycResultCard.style.display = 'block';
    if (kycRiskFactorsCard) kycRiskFactorsCard.style.display = 'block';
    if (kycSuggestionsCard) kycSuggestionsCard.style.display = 'block';

    let kycData = null;

    try {
        const response = await fetch('/api/qichacha/kyc_verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.kycData) {
                kycData = errorData.kycData;
                renderKycData(kycData, kycResultDisplay);
            } else {
                kycResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            kycRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            kycSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            kycData = result.kycData;
            renderKycData(kycData, kycResultDisplay);
            kycRiskFactors.innerHTML = result.riskFactorsHtml;
            kycSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'kyc_verify',
                searchKey: searchKey,
                companyName: kycData?.Name || searchKey,
                kycData: kycData,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            kycData = result.kycData;
            if (kycData) {
                renderKycData(kycData, kycResultDisplay);
            } else {
                kycResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            kycRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            kycSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('KYC verify query or AI analysis error:', error);
        if (!kycData) {
            kycResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (kycRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            kycRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (kycSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            kycSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        kycAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        kycAnalyzeBtn.disabled = false;
    }
});

// Event listener for Certification Query (资质证书)
document.getElementById('certificationAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('certificationSearchKey').value.trim();
    const certificationResultDisplay = document.getElementById('certificationResultDisplay');
    const certificationRiskFactors = document.getElementById('certificationRiskFactors');
    const certificationSuggestions = document.getElementById('certificationSuggestions');
    const certificationAnalyzeBtn = document.getElementById('certificationAnalyzeBtn');

    // 获取卡片元素
    const certificationResultCard = document.getElementById('certificationResultCard');
    const certificationRiskFactorsCard = document.getElementById('certificationRiskFactorsCard');
    const certificationSuggestionsCard = document.getElementById('certificationSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（公司名称）！');
        return;
    }

    certificationAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    certificationAnalyzeBtn.disabled = true;

    // 清空并显示加载状态
    certificationResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询资质证书信息...</p>';
    certificationRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    certificationSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (certificationResultCard) certificationResultCard.style.display = 'block';
    if (certificationRiskFactorsCard) certificationRiskFactorsCard.style.display = 'block';
    if (certificationSuggestionsCard) certificationSuggestionsCard.style.display = 'block';

    let certificationDataList = null;

    try {
        const response = await fetch('/api/qichacha/certification', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.certificationDataList) {
                certificationDataList = errorData.certificationDataList;
                renderCertificationData(certificationDataList, certificationResultDisplay);
            } else {
                certificationResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            certificationRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            certificationSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            certificationDataList = result.certificationDataList;
            renderCertificationData(certificationDataList, certificationResultDisplay);
            certificationRiskFactors.innerHTML = result.riskFactorsHtml;
            certificationSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'certification',
                searchKey: searchKey,
                companyName: searchKey, // Use searchKey as company name for context
                certificationDataList: certificationDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            certificationDataList = result.certificationDataList;
            if (certificationDataList) {
                renderCertificationData(certificationDataList, certificationResultDisplay);
            } else {
                certificationResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            certificationRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            certificationSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Certification query or AI analysis error:', error);
        if (!certificationDataList) {
            certificationResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (certificationRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            certificationRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (certificationSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            certificationSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        certificationAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        certificationAnalyzeBtn.disabled = false;
    }
});

// Event listener for Trademark Query (全国商标查询)
document.getElementById('trademarkAnalyzeBtn')?.addEventListener('click', async function() {
    const keyword = document.getElementById('trademarkKeyword').value.trim();
    const trademarkResultDisplay = document.getElementById('trademarkResultDisplay');
    const trademarkRiskFactors = document.getElementById('trademarkRiskFactors');
    const trademarkSuggestions = document.getElementById('trademarkSuggestions');
    const trademarkAnalyzeBtn = document.getElementById('trademarkAnalyzeBtn');

    // 获取卡片元素
    const trademarkResultCard = document.getElementById('trademarkResultCard');
    const trademarkRiskFactorsCard = document.getElementById('trademarkRiskFactorsCard');
    const trademarkSuggestionsCard = document.getElementById('trademarkSuggestionsCard');

    if (!keyword) {
        alert('请输入申请人名称！');
        return;
    }

    trademarkAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    trademarkAnalyzeBtn.disabled = true;
    trademarkResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询商标信息...</p>';
    trademarkRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    trademarkSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (trademarkResultCard) trademarkResultCard.style.display = 'block';
    if (trademarkRiskFactorsCard) trademarkRiskFactorsCard.style.display = 'block';
    if (trademarkSuggestionsCard) trademarkSuggestionsCard.style.display = 'block';

    let trademarkDataList = null;

    try {
        const response = await fetch('/api/qichacha/trademark', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ keyword: keyword })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.trademarkDataList) {
                trademarkDataList = errorData.trademarkDataList;
                renderTrademarkData(trademarkDataList, trademarkResultDisplay);
            } else {
                trademarkResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            trademarkRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            trademarkSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            trademarkDataList = result.trademarkDataList;
            renderTrademarkData(trademarkDataList, trademarkResultDisplay);
            trademarkRiskFactors.innerHTML = result.riskFactorsHtml;
            trademarkSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'trademark',
                keyword: keyword,
                companyName: keyword, // Use keyword as company name for context
                trademarkDataList: trademarkDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            trademarkDataList = result.trademarkDataList;
            if (trademarkDataList) {
                renderTrademarkData(trademarkDataList, trademarkResultDisplay);
            } else {
                trademarkResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            trademarkRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            trademarkSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Trademark query or AI analysis error:', error);
        if (!trademarkDataList) {
            trademarkResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (trademarkRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            trademarkRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (trademarkSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            trademarkSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        trademarkAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        trademarkAnalyzeBtn.disabled = false;
    }
});

// Event listener for Patent Query (专利查询)
document.getElementById('patentAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('patentSearchKey').value.trim();
    const patentResultDisplay = document.getElementById('patentResultDisplay');
    const patentRiskFactors = document.getElementById('patentRiskFactors');
    const patentSuggestions = document.getElementById('patentSuggestions');
    const patentAnalyzeBtn = document.getElementById('patentAnalyzeBtn');

    // 获取卡片元素
    const patentResultCard = document.getElementById('patentResultCard');
    const patentRiskFactorsCard = document.getElementById('patentRiskFactorsCard');
    const patentSuggestionsCard = document.getElementById('patentSuggestionsCard');

    if (!searchKey) {
        alert('请输入查询关键字（公司名称或专利名称）！');
        return;
    }

    patentAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    patentAnalyzeBtn.disabled = true;
    patentResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询专利信息...</p>';
    patentRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    patentSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (patentResultCard) patentResultCard.style.display = 'block';
    if (patentRiskFactorsCard) patentRiskFactorsCard.style.display = 'block';
    if (patentSuggestionsCard) patentSuggestionsCard.style.display = 'block';

    let patentDataList = null;

    try {
        const response = await fetch('/api/qichacha/patent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.patentDataList) {
                patentDataList = errorData.patentDataList;
                renderPatentData(patentDataList, patentResultDisplay);
            } else {
                patentResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            patentRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            patentSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            patentDataList = result.patentDataList;
            renderPatentData(patentDataList, patentResultDisplay);
            patentRiskFactors.innerHTML = result.riskFactorsHtml;
            patentSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'patent',
                searchKey: searchKey,
                companyName: searchKey, // Use searchKey as company name for context
                patentDataList: patentDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            patentDataList = result.patentDataList;
            if (patentDataList) {
                renderPatentData(patentDataList, patentResultDisplay);
            } else {
                patentResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            patentRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            patentSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Patent query or AI analysis error:', error);
        if (!patentDataList) {
            patentResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (patentRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            patentRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (patentSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            patentSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        patentAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        patentAnalyzeBtn.disabled = false;
    }
});

// Event listener for Annual Report Query (企业年报信息)
document.getElementById('annualReportAnalyzeBtn')?.addEventListener('click', async function() {
    const keyNo = document.getElementById('annualReportKeyNo').value.trim();
    const year = document.getElementById('annualReportYear').value.trim(); // Optional
    const annualReportResultDisplay = document.getElementById('annualReportResultDisplay');
    const annualReportRiskFactors = document.getElementById('annualReportRiskFactors');
    const annualReportSuggestions = document.getElementById('annualReportSuggestions');
    const annualReportAnalyzeBtn = document.getElementById('annualReportAnalyzeBtn');

    // 获取卡片元素
    const annualReportResultCard = document.getElementById('annualReportResultCard');
    const annualReportRiskFactorsCard = document.getElementById('annualReportRiskFactorsCard');
    const annualReportSuggestionsCard = document.getElementById('annualReportSuggestionsCard');

    if (!keyNo) {
        alert('请输入查询关键字（企业名称或统一社会信用代码）！');
        return;
    }

    annualReportAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    annualReportAnalyzeBtn.disabled = true;
    annualReportResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询企业年报信息...</p>';
    annualReportRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    annualReportSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (annualReportResultCard) annualReportResultCard.style.display = 'block';
    if (annualReportRiskFactorsCard) annualReportRiskFactorsCard.style.display = 'block';
    if (annualReportSuggestionsCard) annualReportSuggestionsCard.style.display = 'block';

    let annualReportDataList = null;

    try {
        const response = await fetch('/api/qichacha/annual_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ keyNo: keyNo, year: year })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.annualReportDataList) {
                annualReportDataList = errorData.annualReportDataList;
                renderAnnualReportData(annualReportDataList, annualReportResultDisplay);
            } else {
                annualReportResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            annualReportRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            annualReportSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            annualReportDataList = result.annualReportDataList;
            renderAnnualReportData(annualReportDataList, annualReportResultDisplay);
            annualReportRiskFactors.innerHTML = result.riskFactorsHtml;
            annualReportSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'annual_report',
                key_no: keyNo,
                companyName: keyNo, // Use keyNo as company name for context
                annualReportDataList: annualReportDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            annualReportDataList = result.annualReportDataList;
            if (annualReportDataList) {
                renderAnnualReportData(annualReportDataList, annualReportResultDisplay);
            } else {
                annualReportResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            annualReportRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            annualReportSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Annual Report query or AI analysis error:', error);
        if (!annualReportDataList) {
            annualReportResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (annualReportRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            annualReportRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (annualReportSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            annualReportSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        annualReportAnalyzeBtn.innerHTML = '<i class="fas fa-search"></i> 查询并AI分析';
        annualReportAnalyzeBtn.disabled = false;
    }
});

// Event listener for Comprehensive Risk Scan (综合风险排查)
document.getElementById('comprehensiveAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('comprehensiveSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('comprehensiveCompanyNameForBlueLM').value.trim();
    const comprehensiveResultDisplay = document.getElementById('comprehensiveResultDisplay');
    const comprehensiveRiskFactors = document.getElementById('comprehensiveRiskFactors');
    const comprehensiveSuggestions = document.getElementById('comprehensiveSuggestions');
    const comprehensiveAnalyzeBtn = document.getElementById('comprehensiveAnalyzeBtn');

    // 获取卡片元素
    const comprehensiveResultCard = document.getElementById('comprehensiveResultCard');
    const comprehensiveRiskFactorsCard = document.getElementById('comprehensiveRiskFactorsCard');
    const comprehensiveSuggestionsCard = document.getElementById('comprehensiveSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    comprehensiveAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 综合查询并AI分析中...';
    comprehensiveAnalyzeBtn.disabled = true;
    comprehensiveResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询内部数据库综合风险数据...</p>';
    comprehensiveRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    comprehensiveSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (comprehensiveResultCard) comprehensiveResultCard.style.display = 'block';
    if (comprehensiveRiskFactorsCard) comprehensiveRiskFactorsCard.style.display = 'block';
    if (comprehensiveSuggestionsCard) comprehensiveSuggestionsCard.style.display = 'block';

    let comprehensiveData = null;

    try {
        const response = await fetch('/api/qichacha/comprehensive_risk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey, companyNameForBlueLM: companyNameForBlueLM })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.qccData) {
                comprehensiveData = errorData.qccData;
                renderComprehensiveRiskData(comprehensiveData, comprehensiveResultDisplay);
            } else {
                comprehensiveResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            comprehensiveRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            comprehensiveSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            comprehensiveData = result.qccData;
            renderComprehensiveRiskData(comprehensiveData, comprehensiveResultDisplay);
            comprehensiveRiskFactors.innerHTML = result.riskFactorsHtml;
            comprehensiveSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'comprehensive_risk',
                searchKey: searchKey,
                companyName: comprehensiveData?.Name || searchKey,
                qccData: comprehensiveData,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            comprehensiveData = result.qccData;
            if (comprehensiveData) {
                renderComprehensiveRiskData(comprehensiveData, comprehensiveResultDisplay);
            } else {
                comprehensiveResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            comprehensiveRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            comprehensiveSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Comprehensive risk query or AI analysis error:', error);
        if (!comprehensiveData) {
            comprehensiveResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (comprehensiveRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            comprehensiveRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (comprehensiveSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            comprehensiveSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        comprehensiveAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 综合查询并AI分析';
        comprehensiveAnalyzeBtn.disabled = false;
    }
});

// Event listener for Shixin Check (失信核查)
document.getElementById('shixinAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('shixinSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('shixinCompanyNameForBlueLM').value.trim();
    const shixinResultDisplay = document.getElementById('shixinResultDisplay');
    const shixinRiskFactors = document.getElementById('shixinRiskFactors');
    const shixinSuggestions = document.getElementById('shixinSuggestions');
    const shixinAnalyzeBtn = document.getElementById('shixinAnalyzeBtn');

    // 获取卡片元素
    const shixinResultCard = document.getElementById('shixinResultCard');
    const shixinRiskFactorsCard = document.getElementById('shixinRiskFactorsCard');
    const shixinSuggestionsCard = document.getElementById('shixinSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    shixinAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    shixinAnalyzeBtn.disabled = true;
    shixinResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询失信信息...</p>';
    shixinRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    shixinSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (shixinResultCard) shixinResultCard.style.display = 'block';
    if (shixinRiskFactorsCard) shixinRiskFactorsCard.style.display = 'block';
    if (shixinSuggestionsCard) shixinSuggestionsCard.style.display = 'block';

    let shixinDataList = null;

    try {
        const response = await fetch('/api/qichacha/shixin_check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey, companyNameForBlueLM: companyNameForBlueLM })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.shixinDataList) {
                shixinDataList = errorData.shixinDataList;
                renderShixinData(shixinDataList, shixinResultDisplay);
            } else {
                shixinResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            shixinRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            shixinSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            shixinDataList = result.shixinDataList;
            renderShixinData(shixinDataList, shixinResultDisplay);
            shixinRiskFactors.innerHTML = result.riskFactorsHtml;
            shixinSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'shixin_check',
                searchKey: searchKey,
                companyName: companyNameForBlueLM || searchKey,
                shixinDataList: shixinDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            shixinDataList = result.shixinDataList;
            if (shixinDataList) {
                renderShixinData(shixinDataList, shixinResultDisplay);
            } else {
                shixinResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            shixinRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            shixinSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Shixin check query or AI analysis error:', error);
        if (!shixinDataList) {
            shixinResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (shixinRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            shixinRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (shixinSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            shixinSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        shixinAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 查询并AI分析';
        shixinAnalyzeBtn.disabled = false;
    }
});

// Event listener for Exception Check (经营异常核查)
document.getElementById('exceptionAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('exceptionSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('exceptionCompanyNameForBlueLM').value.trim();
    const exceptionResultDisplay = document.getElementById('exceptionResultDisplay');
    const exceptionRiskFactors = document.getElementById('exceptionRiskFactors');
    const exceptionSuggestions = document.getElementById('exceptionSuggestions');
    const exceptionAnalyzeBtn = document.getElementById('exceptionAnalyzeBtn');

    // 获取卡片元素
    const exceptionResultCard = document.getElementById('exceptionResultCard');
    const exceptionRiskFactorsCard = document.getElementById('exceptionRiskFactorsCard');
    const exceptionSuggestionsCard = document.getElementById('exceptionSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    exceptionAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    exceptionAnalyzeBtn.disabled = true;
    exceptionResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询经营异常信息...</p>';
    exceptionRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    exceptionSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (exceptionResultCard) exceptionResultCard.style.display = 'block';
    if (exceptionRiskFactorsCard) exceptionRiskFactorsCard.style.display = 'block';
    if (exceptionSuggestionsCard) exceptionSuggestionsCard.style.display = 'block';

    let exceptionDataList = null;

    try {
        const response = await fetch('/api/qichacha/exception_check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey, companyNameForBlueLM: companyNameForBlueLM })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.exceptionDataList) {
                exceptionDataList = errorData.exceptionDataList;
                renderExceptionData(exceptionDataList, exceptionResultDisplay);
            } else {
                exceptionResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            exceptionRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            exceptionSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            exceptionDataList = result.exceptionDataList;
            renderExceptionData(exceptionDataList, exceptionResultDisplay);
            exceptionRiskFactors.innerHTML = result.riskFactorsHtml;
            exceptionSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'exception_check',
                searchKey: searchKey,
                companyName: companyNameForBlueLM || searchKey,
                exceptionDataList: exceptionDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            exceptionDataList = result.exceptionDataList;
            if (exceptionDataList) {
                renderExceptionData(exceptionDataList, exceptionResultDisplay);
            } else {
                exceptionResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            exceptionRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            exceptionSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Exception check query or AI analysis error:', error);
        if (!exceptionDataList) {
            exceptionResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (exceptionRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            exceptionRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (exceptionSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            exceptionSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        exceptionAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 查询并AI分析';
        exceptionAnalyzeBtn.disabled = false;
    }
});

// Event listener for Zhixing Check (被执行人核查)
document.getElementById('zhixingAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('zhixingSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('zhixingCompanyNameForBlueLM').value.trim();
    const zhixingResultDisplay = document.getElementById('zhixingResultDisplay');
    const zhixingRiskFactors = document.getElementById('zhixingRiskFactors');
    const zhixingSuggestions = document.getElementById('zhixingSuggestions');
    const zhixingAnalyzeBtn = document.getElementById('zhixingAnalyzeBtn');

    // 获取卡片元素
    const zhixingResultCard = document.getElementById('zhixingResultCard');
    const zhixingRiskFactorsCard = document.getElementById('zhixingRiskFactorsCard');
    const zhixingSuggestionsCard = document.getElementById('zhixingSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    zhixingAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    zhixingAnalyzeBtn.disabled = true;
    zhixingResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询被执行信息...</p>';
    zhixingRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    zhixingSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (zhixingResultCard) zhixingResultCard.style.display = 'block';
    if (zhixingRiskFactorsCard) zhixingRiskFactorsCard.style.display = 'block';
    if (zhixingSuggestionsCard) zhixingSuggestionsCard.style.display = 'block';

    let zhixingDataList = null;

    try {
        const response = await fetch('/api/qichacha/zhixing_check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey, companyNameForBlueLM: companyNameForBlueLM })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.zhixingDataList) {
                zhixingDataList = errorData.zhixingDataList;
                renderZhixingData(zhixingDataList, zhixingResultDisplay);
            } else {
                zhixingResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            zhixingRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            zhixingSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            zhixingDataList = result.zhixingDataList;
            renderZhixingData(zhixingDataList, zhixingResultDisplay);
            zhixingRiskFactors.innerHTML = result.riskFactorsHtml;
            zhixingSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'zhixing_check',
                searchKey: searchKey,
                companyName: companyNameForBlueLM || searchKey,
                zhixingDataList: zhixingDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            zhixingDataList = result.zhixingDataList;
            if (zhixingDataList) {
                renderZhixingData(zhixingDataList, zhixingResultDisplay);
            } else {
                zhixingResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            zhixingRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            zhixingSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Zhixing check query or AI analysis error:', error);
        if (!zhixingDataList) {
            zhixingResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (zhixingRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            zhixingRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (zhixingSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            zhixingSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        zhixingAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 查询并AI分析';
        zhixingAnalyzeBtn.disabled = false;
    }
});

// Event listener for Serious Illegal Check (严重违法核查)
document.getElementById('seriousIllegalAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('seriousIllegalSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('seriousIllegalCompanyNameForBlueLM').value.trim();
    const seriousIllegalResultDisplay = document.getElementById('seriousIllegalResultDisplay');
    const seriousIllegalRiskFactors = document.getElementById('seriousIllegalRiskFactors');
    const seriousIllegalSuggestions = document.getElementById('seriousIllegalSuggestions');
    const seriousIllegalAnalyzeBtn = document.getElementById('seriousIllegalAnalyzeBtn');

    // 获取卡片元素
    const seriousIllegalResultCard = document.getElementById('seriousIllegalResultCard');
    const seriousIllegalRiskFactorsCard = document.getElementById('seriousIllegalRiskFactorsCard');
    const seriousIllegalSuggestionsCard = document.getElementById('seriousIllegalSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    seriousIllegalAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    seriousIllegalAnalyzeBtn.disabled = true;
    seriousIllegalResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询严重违法信息...</p>';
    seriousIllegalRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    seriousIllegalSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (seriousIllegalResultCard) seriousIllegalResultCard.style.display = 'block';
    if (seriousIllegalRiskFactorsCard) seriousIllegalRiskFactorsCard.style.display = 'block';
    if (seriousIllegalSuggestionsCard) seriousIllegalSuggestionsCard.style.display = 'block';

    let seriousIllegalDataList = null;

    try {
        const response = await fetch('/api/qichacha/serious_illegal_check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ searchKey: searchKey, companyNameForBlueLM: companyNameForBlueLM })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.seriousIllegalDataList) {
                seriousIllegalDataList = errorData.seriousIllegalDataList;
                renderSeriousIllegalData(seriousIllegalDataList, seriousIllegalResultDisplay);
            } else {
                seriousIllegalResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            seriousIllegalRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            seriousIllegalSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            seriousIllegalDataList = result.seriousIllegalDataList;
            renderSeriousIllegalData(seriousIllegalDataList, seriousIllegalResultDisplay);
            seriousIllegalRiskFactors.innerHTML = result.riskFactorsHtml;
            seriousIllegalSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'serious_illegal_check',
                searchKey: searchKey,
                companyName: companyNameForBlueLM || searchKey,
                seriousIllegalDataList: seriousIllegalDataList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            seriousIllegalDataList = result.seriousIllegalDataList;
            if (seriousIllegalDataList) {
                renderSeriousIllegalData(seriousIllegalDataList, seriousIllegalResultDisplay);
            } else {
                seriousIllegalResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            seriousIllegalRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            seriousIllegalSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Serious illegal check query or AI analysis error:', error);
        if (!seriousIllegalDataList) {
            seriousIllegalResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (seriousIllegalRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            seriousIllegalRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (seriousIllegalSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            seriousIllegalSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        seriousIllegalAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 查询并AI分析';
        seriousIllegalAnalyzeBtn.disabled = false;
    }
});

// Event listener for Judgment Doc Check (裁决文书核查)
document.getElementById('judgmentDocAnalyzeBtn')?.addEventListener('click', async function() {
    const searchKey = document.getElementById('judgmentDocSearchKey').value.trim();
    const companyNameForBlueLM = document.getElementById('judgmentDocCompanyNameForBlueLM').value.trim();
    const pubYear = document.getElementById('judgmentDocPubYear').value.trim();
    const caseIdentity = document.getElementById('judgmentDocCaseIdentity').value.trim();
    const caseStatus = document.getElementById('judgmentDocCaseStatus').value.trim();
    const keyWordFilter = document.getElementById('judgmentDocKeyWordFilter').value.trim();

    const judgmentDocResultDisplay = document.getElementById('judgmentDocResultDisplay');
    const judgmentDocRiskFactors = document.getElementById('judgmentDocRiskFactors');
    const judgmentDocSuggestions = document.getElementById('judgmentDocSuggestions');
    const judgmentDocAnalyzeBtn = document.getElementById('judgmentDocAnalyzeBtn');

    // 获取卡片元素
    const judgmentDocResultCard = document.getElementById('judgmentDocResultCard');
    const judgmentDocRiskFactorsCard = document.getElementById('judgmentDocRiskFactorsCard');
    const judgmentDocSuggestionsCard = document.getElementById('judgmentDocSuggestionsCard');

    if (!searchKey) {
        alert('请输入搜索关键词（企业名称或统一社会信用代码）！');
        return;
    }

    judgmentDocAnalyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 查询并AI分析中...';
    judgmentDocAnalyzeBtn.disabled = true;
    judgmentDocResultDisplay.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在查询裁决文书信息...</p>';
    judgmentDocRiskFactors.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在进行AI风险分析...</p>';
    judgmentDocSuggestions.innerHTML = '<p style="text-align: center; color: #a3c3ff;"><i class="fas fa-spinner fa-spin"></i> 正在生成AI改进建议...</p>';

    // 确保卡片可见
    if (judgmentDocResultCard) judgmentDocResultCard.style.display = 'block';
    if (judgmentDocRiskFactorsCard) judgmentDocRiskFactorsCard.style.display = 'block';
    if (judgmentDocSuggestionsCard) judgmentDocSuggestionsCard.style.display = 'block';

    let judgmentDocList = null;

    try {
        const response = await fetch('/api/qichacha/judgment_doc_check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                searchKey: searchKey,
                companyNameForBlueLM: companyNameForBlueLM,
                pubYear: pubYear || null, // Pass null if empty
                caseIdentity: caseIdentity || null,
                caseStatus: caseStatus || null,
                keyWordFilter: keyWordFilter || null
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            if (errorData.judgmentDocList) {
                judgmentDocList = errorData.judgmentDocList;
                renderJudgmentDocData(judgmentDocList, judgmentDocResultDisplay);
            } else {
                judgmentDocResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${errorData.error || '服务器错误'}</p>`;
            }
            judgmentDocRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${errorData.error || '未能获取AI风险分析结果。'}</p>`;
            judgmentDocSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${errorData.error || '未能获取AI改进建议。'}</p>`;
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json();

        if (result.success) {
            judgmentDocList = result.judgmentDocList;
            renderJudgmentDocData(judgmentDocList, judgmentDocResultDisplay);
            judgmentDocRiskFactors.innerHTML = result.riskFactorsHtml;
            judgmentDocSuggestions.innerHTML = result.suggestionsHtml;

            sessionStorage.setItem('lastAnalysis', JSON.stringify({
                type: 'judgment_doc_check',
                searchKey: searchKey,
                companyName: companyNameForBlueLM || searchKey,
                judgmentDocList: judgmentDocList,
                bluelmOutput: result.bluelmOutput,
                assessmentId: result.assessmentId
            }));

            if (typeof updateHistoryAssessmentsTable === 'function') {
                updateHistoryAssessmentsTable();
            }

        } else {
            judgmentDocList = result.judgmentDocList;
            if (judgmentDocList) {
                renderJudgmentDocData(judgmentDocList, judgmentDocResultDisplay);
            } else {
                judgmentDocResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 查询失败: ${result.error}</p>`;
            }
            judgmentDocRiskFactors.innerHTML = `<p class="qcc-error">AI风险分析失败: ${result.error || '未能获取AI风险分析结果。'}</p>`;
            judgmentDocSuggestions.innerHTML = `<p class="qcc-error">AI改进建议失败: ${result.error || '未能获取AI改进建议。'}</p>`;
        }
    } catch (error) {
        console.error('Judgment Doc check query or AI analysis error:', error);
        if (!judgmentDocList) {
            judgmentDocResultDisplay.innerHTML = `<p class="qcc-error"><i class="fas fa-times-circle"></i> 请求出错，请稍后再试。错误: ${error.message}</p>`;
        }
        if (judgmentDocRiskFactors.innerHTML.includes('正在进行AI风险分析')) {
            judgmentDocRiskFactors.innerHTML = '<p class="qcc-error">未能获取AI风险分析结果。</p>';
        }
        if (judgmentDocSuggestions.innerHTML.includes('正在生成AI改进建议')) {
            judgmentDocSuggestions.innerHTML = '<p class="qcc-error">未能获取AI改进建议。</p>';
        }
    } finally {
        judgmentDocAnalyzeBtn.innerHTML = '<i class="fas fa-magic"></i> 查询并AI分析';
        judgmentDocAnalyzeBtn.disabled = false;
    }
});


// Render functions for different QCC APIs (已有的渲染函数，以及新增的综合风险、失信、经营异常、被执行人、严重违法、裁决文书渲染函数)

function renderQccVerifyData(data, containerElement) {
    if (!data) {
        containerElement.innerHTML = '<p class="qcc-error">未获取到详细企业信息。</p>';
        return;
    }

    let html = `<div class="qcc-data-grid">`;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-building"></i> 基本信息</h4>
            <div class="qcc-data-item"><strong>企业名称:</strong> <span>${data.Name || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>统一社会信用代码:</strong> <span>${data.CreditCode || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>法定代表人:</strong> <span>${data.OperName || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>登记状态:</strong> <span>${data.Status || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>成立日期:</strong> <span>${data.StartDate ? data.StartDate.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册资本:</strong> <span>${data.RegistCapi || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>实缴资本:</strong> <span>${data.RealCapi || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>企业类型:</strong> <span>${data.EconKind || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>营业期限:</strong> <span>${data.TermStart ? data.TermStart.split(' ')[0] : 'N/A'} 至 ${data.TermEnd ? data.TermEnd.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>核准日期:</strong> <span>${data.CheckDate ? data.CheckDate.split(' ')[0] : 'N/A'}</span></div>
        </div>
    `;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-chart-line"></i> 经营与资质</h4>
            <div class="qcc-data-item"><strong>纳税人资质:</strong> <span>${data.TaxpayerType || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>人员规模:</strong> <span>${data.PersonScope || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>参保人数:</strong> <span>${data.InsuredCount || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>是否小微企业:</strong> <span>${data.IsSmall === '1' ? '是' : (data.IsSmall === '0' ? '否' : 'N/A')}</span></div>
            <div class="qcc-data-item"><strong>企业规模:</strong> <span>${data.Scale || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>国标行业:</strong> <span>${data.Industry?.Industry || 'N/A'} - ${data.Industry?.SubIndustry || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>内部数据库行业:</strong> <span>${data.QccIndustry?.AName || 'N/A'} > ${data.QccIndustry?.BName || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>经营范围:</strong> <span>${data.Scope ? data.Scope.substring(0, 300) + (data.Scope.length > 300 ? '...' : '') : 'N/A'}</span></div>
        </div>
    `;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-map-marker-alt"></i> 地址与联系</h4>
            <div class="qcc-data-item"><strong>注册地址:</strong> <span>${data.Address || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>所属地区:</strong> <span>${data.Area?.Province || 'N/A'} ${data.Area?.City || 'N/A'} ${data.Area?.County || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>联系电话:</strong> <span>${data.ContactInfo?.Tel || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>邮箱:</strong> <span>${data.ContactInfo?.Email || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>网址:</strong> <span>${data.ContactInfo?.WebSiteList?.join(', ') || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>经纬度:</strong> <span>${data.LongLat?.Longitude || 'N/A'}, ${data.LongLat?.Latitude || 'N/A'}</span></div>
        </div>
    `;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-info-circle"></i> 其他信息</h4>
            <div class="qcc-data-item"><strong>上市信息:</strong> <span>${data.StockInfo?.StockType || 'N/A'} ${data.StockInfo?.StockNumber ? `(${data.StockInfo.StockNumber})` : ''}</span></div>
            <div class="qcc-data-item"><strong>曾用名:</strong> <span>${data.OriginalName?.map(n => n.Name).join(', ') || '无'}</span></div>
            <div class="qcc-data-item"><strong>注销/吊销信息:</strong> <span>${data.RevokeInfo ? (data.RevokeInfo.CancelDate ? `注销日期: ${data.RevokeInfo.CancelDate}, 原因: ${data.RevokeInfo.CancelReason || 'N/A'}` : (data.RevokeInfo.RevokeDate ? `吊销日期: ${data.RevokeInfo.RevokeDate}, 原因: ${data.RevokeInfo.RevokeReason || 'N/A'}` : '无')) : '无'}</span></div>
            <div class="qcc-data-item"><strong>开票银行:</strong> <span>${data.BankInfo?.Bank || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>开票账号:</strong> <span>${data.BankInfo?.BankAccount || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>总公司:</strong> <span>${data.Parent?.Name || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>实际控制人:</strong> <span>${data.ActualControllerList?.[0]?.Name || 'N/A'}</span></div>
        </div>
    `;

    if (data.PartnerList && data.PartnerList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-users"></i> 股东信息 (前5条)</h4>
                <ul class="qcc-nested-list">
                    ${data.PartnerList.slice(0, 5).map(p => `<li><strong>${p.StockName || 'N/A'}:</strong> ${p.StockPercent || 'N/A'}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.EmployeeList && data.EmployeeList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-user-tie"></i> 主要人员 (前5条)</h4>
                <ul class="qcc-nested-list">
                    ${data.EmployeeList.slice(0, 5).map(e => `<li><strong>${e.Name || 'N/A'}:</strong> ${e.Job || 'N/A'}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.InvestmentList && data.InvestmentList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-handshake"></i> 对外投资 (前3条)</h4>
                <ul class="qcc-nested-list">
                    ${data.InvestmentList.slice(0, 3).map(i => `<li><strong>${i.Name || 'N/A'}:</strong> 持股 ${i.FundedRatio || 'N/A'} (${i.Status || 'N/A'})</li>`).join('')}
                </ul>
            </div>
        `;
    }

    html += `</div>`;
    containerElement.innerHTML = html;
}

function renderIndustrialInfoData(data, containerElement) {
    if (!data) {
        containerElement.innerHTML = '<p class="qcc-error">未获取到详细企业工商信息。</p>';
        return;
    }

    let html = `<div class="qcc-data-grid">`;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-building"></i> 基本工商信息</h4>
            <div class="qcc-data-item"><strong>企业名称:</strong> <span>${data.Name || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>统一社会信用代码:</strong> <span>${data.CreditCode || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册号:</strong> <span>${data.No || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>法定代表人:</strong> <span>${data.OperName || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>登记状态:</strong> <span>${data.Status || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>成立日期:</strong> <span>${data.StartDate ? data.StartDate.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册资本:</strong> <span>${data.RegistCapi || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>实缴资本:</strong> <span>${data.RecCap || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>企业类型:</strong> <span>${data.EconKind || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>营业期限:</strong> <span>${data.TermStart ? data.TermStart.split(' ')[0] : 'N/A'} 至 ${data.TermEnd ? data.TermEnd.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>核准日期:</strong> <span>${data.CheckDate ? data.CheckDate.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>登记机关:</strong> <span>${data.BelongOrg || 'N/A'}</span></div>
        </div>
    `;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-map-marker-alt"></i> 地址与经营</h4>
            <div class="qcc-data-item"><strong>注册地址:</strong> <span>${data.Address || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>所属省份:</strong> <span>${data.Province || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>行政区划:</strong> <span>${data.Area?.Province || 'N/A'} ${data.Area?.City || 'N/A'} ${data.Area?.County || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>经营范围:</strong> <span>${data.Scope ? data.Scope.substring(0, 300) + (data.Scope.length > 300 ? '...' : '') : 'N/A'}</span></div>
        </div>
    `;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-info-circle"></i> 其他工商信息</h4>
            <div class="qcc-data-item"><strong>是否上市:</strong> <span>${data.IsOnStock === '1' ? '是' : (data.IsOnStock === '0' ? '否' : 'N/A')}</span></div>
            <div class="qcc-data-item"><strong>上市类型:</strong> <span>${data.StockType || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>股票代码:</strong> <span>${data.StockNumber || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>曾用名:</strong> <span>${data.OriginalName?.map(n => n.Name).join(', ') || '无'}</span></div>
            <div class="qcc-data-item"><strong>注销/吊销信息:</strong> <span>${data.RevokeInfo ? (data.RevokeInfo.CancelDate ? `注销日期: ${data.RevokeInfo.CancelDate}, 原因: ${data.RevokeInfo.CancelReason || 'N/A'}` : (data.RevokeInfo.RevokeDate ? `吊销日期: ${data.RevokeInfo.RevokeDate}, 原因: ${data.RevokeInfo.RevokeReason || 'N/A'}` : '无')) : '无'}</span></div>
        </div>
    `;

    html += `</div>`;
    containerElement.innerHTML = html;
}

function renderFuzzySearchData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关企业信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-list-alt"></i> 搜索结果列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>企业名称:</strong> <span>${data.Name || 'N/A'}</span><br>
                <strong>法定代表人:</strong> <span>${data.OperName || 'N/A'}</span><br>
                <strong>登记状态:</strong> <span>${data.Status || 'N/A'}</span><br>
                <strong>统一社会信用代码:</strong> <span>${data.CreditCode || 'N/A'}</span><br>
                <strong>成立日期:</strong> <span>${data.StartDate || 'N/A'}</span><br>
                <strong>注册地址:</strong> <span>${data.Address || 'N/A'}</span>
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

function renderTaxInvoiceData(data, containerElement) {
    if (!data) {
        containerElement.innerHTML = '<p class="qcc-error">未获取到税号开票信息。</p>';
        return;
    }

    let html = `<div class="qcc-data-grid">`;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-file-invoice-dollar"></i> 税号开票信息详情</h4>
            <div class="qcc-data-item"><strong>企业名称:</strong> <span>${data.Name || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>统一社会信用代码 (纳税人识别号):</strong> <span>${data.CreditCode || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>企业类型:</strong> <span>${data.EconKind || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>企业状态:</strong> <span>${data.Status || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>地址:</strong> <span>${data.Address || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>联系电话:</strong> <span>${data.Tel || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>开户行:</strong> <span>${data.Bank || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>开户行账号:</strong> <span>${data.BankAccount || 'N/A'}</span></div>
        </div>
    `;

    html += `</div>`;
    containerElement.innerHTML = html;
}

// Render function for KYC Verify Data (客户身份识别)
function renderKycData(data, containerElement) {
    if (!data) {
        containerElement.innerHTML = '<p class="qcc-error">未获取到详细客户身份识别信息。</p>';
        return;
    }

    let html = `<div class="qcc-data-grid">`;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-id-card"></i> 客户身份信息</h4>
            <div class="qcc-data-item"><strong>企业名称:</strong> <span>${data.Name || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>统一社会信用代码:</strong> <span>${data.CreditCode || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>法定代表人:</strong> <span>${data.OperName || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>登记状态:</strong> <span>${data.Status || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>成立日期:</strong> <span>${data.StartDate ? data.StartDate.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册资本:</strong> <span>${data.RegistCapi || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>实缴资本:</strong> <span>${data.RealCapi || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>企业类型:</strong> <span>${data.EconKind || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>营业期限:</strong> <span>${data.TermStart ? data.TermStart.split(' ')[0] : 'N/A'} 至 ${data.TermEnd ? data.TermEnd.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>纳税人资质:</strong> <span>${data.TaxpayerType || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>人员规模:</strong> <span>${data.PersonScope || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>参保人数:</strong> <span>${data.InsuredCount || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册地址:</strong> <span>${data.Address || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>联系电话:</strong> <span>${data.ContactInfo?.Tel || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>邮箱:</strong> <span>${data.ContactInfo?.Email || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>经营范围:</strong> <span>${data.Scope ? data.Scope.substring(0, 300) + (data.Scope.length > 300 ? '...' : '') : 'N/A'}</span></div>
        </div>
    `;

    if (data.PartnerList && data.PartnerList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-users"></i> 股东信息 (前5条)</h4>
                <ul class="qcc-nested-list">
                    ${data.PartnerList.slice(0, 5).map(p => `<li><strong>${p.StockName || 'N/A'}:</strong> ${p.StockPercent || 'N/A'}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.EmployeeList && data.EmployeeList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-user-tie"></i> 主要人员 (前5条)</h4>
                <ul class="qcc-nested-list">
                    ${data.EmployeeList.slice(0, 5).map(e => `<li><strong>${e.Name || 'N/A'}:</strong> ${e.Job || 'N/A'}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.ActualControllerList && data.ActualControllerList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-user-shield"></i> 实际控制人</h4>
                <ul class="qcc-nested-list">
                    ${data.ActualControllerList.slice(0, 1).map(ac => `<li><strong>${ac.Name || 'N/A'}:</strong> 控制比例 ${ac.ControlPercent || 'N/A'}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    html += `</div>`;
    containerElement.innerHTML = html;
}

// Render function for Certification Data (资质证书)
function renderCertificationData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关资质证书信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-award"></i> 资质证书列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>名称:</strong> <span>${data.Name || 'N/A'}</span><br>
                <strong>类型:</strong> <span>${data.TypeDesc || 'N/A'}</span><br>
                <strong>编号:</strong> <span>${data.No || 'N/A'}</span><br>
                <strong>生效日期:</strong> <span>${data.StartDate || 'N/A'}</span><br>
                <strong>截止日期:</strong> <span>${data.EndDate || 'N/A'}</span><br>
                <strong>发证机构:</strong> <span>${data.InstitutionList?.join(', ') || 'N/A'}</span><br>
                <strong>状态:</strong> <span>${data.Status || 'N/A'}</span>
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Trademark Data (全国商标查询)
function renderTrademarkData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关商标信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-trademark"></i> 商标列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>名称:</strong> <span>${data.Name || 'N/A'}</span><br>
                <strong>注册号:</strong> <span>${data.RegNo || 'N/A'}</span><br>
                <strong>国际分类:</strong> <span>${data.Category || 'N/A'}</span><br>
                <strong>申请人:</strong> <span>${data.ApplicantCn || 'N/A'}</span><br>
                <strong>申请日期:</strong> <span>${data.AppDate || 'N/A'}</span><br>
                <strong>状态:</strong> <span>${data.FlowStatusDesc || 'N/A'}</span>
                ${data.ImageUrl ? `<br><img src="${data.ImageUrl}" alt="商标图案" style="max-width: 100px; max-height: 100px; margin-top: 5px;">` : ''}
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Patent Data (专利查询)
function renderPatentData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关专利信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-lightbulb"></i> 专利列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>标题:</strong> <span>${data.Title || 'N/A'}</span><br>
                <strong>申请号:</strong> <span>${data.ApplicationNumber || 'N/A'}</span><br>
                <strong>申请日期:</strong> <span>${data.ApplicationDate ? data.ApplicationDate.split(' ')[0] : 'N/A'}</span><br>
                <strong>公开号:</strong> <span>${data.PublicationNumber || 'N/A'}</span><br>
                <strong>公开日期:</strong> <span>${data.PublicationDate ? data.PublicationDate.split(' ')[0] : 'N/A'}</span><br>
                <strong>类型:</strong> <span>${data.KindCodeDesc || 'N/A'}</span><br>
                <strong>法律状态:</strong> <span>${data.LegalStatusDesc || 'N/A'}</span><br>
                <strong>申请人:</strong> <span>${data.AssigneestringList?.join(', ') || 'N/A'}</span>
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Annual Report Data (企业年报信息)
function renderAnnualReportData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关企业年报信息。</p>';
        return;
    }

    // Usually, we display the latest annual report
    const data = dataList[0];
    if (!data) {
        containerElement.innerHTML = '<p class="qcc-error">年报数据为空。</p>';
        return;
    }

    let html = `<div class="qcc-data-grid">`;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-file-alt"></i> ${data.Year || '最新'}年度报告 - 基本信息</h4>
            <div class="qcc-data-item"><strong>企业名称:</strong> <span>${data.BasicInfoData?.CompanyName || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>统一社会信用代码:</strong> <span>${data.BasicInfoData?.CreditCode || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>经营状态:</strong> <span>${data.BasicInfoData?.Status || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>从业人数:</strong> <span>${data.BasicInfoData?.EmployeeCount || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>通信地址:</strong> <span>${data.BasicInfoData?.Address || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>电子邮箱:</strong> <span>${data.BasicInfoData?.EmailAddress || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>发布日期:</strong> <span>${data.PublishDate ? data.PublishDate.split(' ')[0] : 'N/A'}</span></div>
        </div>
    `;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-chart-bar"></i> 资产状况信息</h4>
            <div class="qcc-data-item"><strong>资产总额:</strong> <span>${data.AssetsData?.TotalAssets || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>负债总额:</strong> <span>${data.AssetsData?.TotalLiabilities || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>营业总收入:</strong> <span>${data.AssetsData?.GrossTradingIncome || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>利润总额:</strong> <span>${data.AssetsData?.TotalProfit || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>净利润:</strong> <span>${data.AssetsData?.NetProfit || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>纳税总额:</strong> <span>${data.AssetsData?.TotalTaxAmount || 'N/A'}</span></div>
        </div>
    `;

    if (data.PartnerList && data.PartnerList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-users"></i> 股东及出资信息 (前3条)</h4>
                <ul class="qcc-nested-list">
                    ${data.PartnerList.slice(0, 3).map(p => `<li><strong>${p.Name || 'N/A'}:</strong> 认缴 ${p.ShouldCapi || 'N/A'}, 实缴 ${p.RealCapi || 'N/A'}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.StockChangeList && data.StockChangeList.length > 0) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-exchange-alt"></i> 股权变更信息 (前3条)</h4>
                <ul class="qcc-nested-list">
                    ${data.StockChangeList.slice(0, 3).map(sc => `<li><strong>${sc.Name || 'N/A'}:</strong> 变更前 ${sc.Before || 'N/A'}%, 变更后 ${sc.After || 'N/A'}% (${sc.ChangeDate ? sc.ChangeDate.split(' ')[0] : 'N/A'})</li>`).join('')}
                </ul>
            </div>
        `;
    }

    if (data.SocialInsurance) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-shield-alt"></i> 社保信息</h4>
                <div class="qcc-data-item"><strong>城镇职工基本养老保险:</strong> <span>${data.SocialInsurance.UrbanBasicIns || 'N/A'}</span></div>
                <div class="qcc-data-item"><strong>职工基本医疗保险:</strong> <span>${data.SocialInsurance.EmployeeBasicIns || 'N/A'}</span></div>
                <div class="qcc-data-item"><strong>生育保险:</strong> <span>${data.SocialInsurance.MaternityIns || 'N/A'}</span></div>
                <div class="qcc-data-item"><strong>失业保险:</strong> <span>${data.SocialInsurance.UnemploymentIns || 'N/A'}</span></div>
                <div class="qcc-data-item"><strong>工伤保险:</strong> <span>${data.SocialInsurance.IndustrialInjuryIns || 'N/A'}</span></div>
            </div>
        `;
    }

    html += `</div>`;
    containerElement.innerHTML = html;
}

// Render function for Comprehensive Risk Data (综合风险排查)
function renderComprehensiveRiskData(data, containerElement) {
    if (!data) {
        containerElement.innerHTML = '<p class="qcc-error">未获取到详细综合风险信息。</p>';
        return;
    }

    let html = `<div class="qcc-data-grid">`;

    html += `
        <div class="qcc-data-card">
            <h4><i class="fas fa-building"></i> 基本信息</h4>
            <div class="qcc-data-item"><strong>企业名称:</strong> <span>${data.Name || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>统一社会信用代码:</strong> <span>${data.CreditCode || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>法定代表人:</strong> <span>${data.OperName || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>登记状态:</strong> <span>${data.Status || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>成立日期:</strong> <span>${data.StartDate ? data.StartDate.split(' ')[0] : 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册资本:</strong> <span>${data.RegistCapi || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>注册地址:</strong> <span>${data.Address || 'N/A'}</span></div>
            <div class="qcc-data-item"><strong>经营范围:</strong> <span>${data.Scope ? data.Scope.substring(0, 150) + (data.Scope.length > 150 ? '...' : '') : 'N/A'}</span></div>
        </div>
    `;

    const riskSections = {
        'ShiXin': { icon: 'fas fa-user-times', title: '失信被执行人' },
        'ZhiXing': { icon: 'fas fa-gavel', title: '被执行人' },
        'AdminPenalty': { icon: 'fas fa-balance-scale', title: '行政处罚' },
        'Exception': { icon: 'fas fa-exclamation-circle', title: '经营异常' },
        'SeriousIllegal': { icon: 'fas fa-exclamation-triangle', title: '严重违法' },
        'EquityFreeze': { icon: 'fas fa-hand-paper', title: '股权冻结' },
        'EquityPledge': { icon: 'fas fa-handshake', title: '股权出质' },
        'ChattelMortgage': { icon: 'fas fa-car', title: '动产抵押' },
        'JudicialSale': { icon: 'fas fa-money-bill-wave', title: '司法拍卖' },
        'Bankruptcy': { icon: 'fas fa-times-circle', title: '破产重整' },
        'Sumptuary': { icon: 'fas fa-ban', title: '限制高消费' },
        'EnvPunishment': { icon: 'fas fa-leaf', title: '环保处罚' },
        'TaxOweNotice': { icon: 'fas fa-receipt', title: '欠税公告' },
        'TaxIllegal': { icon: 'fas fa-file-invoice', title: '税收违法' },
        'TaxAbnormal': { icon: 'fas fa-exclamation', title: '税务非正常户' },
        'TaxHurry': { icon: 'fas fa-bell', title: '税务催缴' },
        'TaxReminder': { icon: 'fas fa-calendar-check', title: '税务催报' },
        'Liquidation': { icon: 'fas fa-undo-alt', title: '清算信息' },
    };

    for (const key in riskSections) {
        const riskInfo = data[key];
        if (riskInfo && riskInfo.TotalCount && parseInt(riskInfo.TotalCount) > 0) {
            let riskHtml = `
                <div class="qcc-data-card">
                    <h4><i class="${riskSections[key].icon}"></i> ${riskSections[key].title}</h4>
                    <div class="qcc-data-item"><strong>总条目数:</strong> <span>${riskInfo.TotalCount || 'N/A'}</span></div>
            `;
            if (riskInfo.TotalAmount) {
                riskHtml += `<div class="qcc-data-item"><strong>涉案总金额:</strong> <span>${riskInfo.TotalAmount} 万元</span></div>`;
            }
            if (riskInfo.DataList && riskInfo.DataList.length > 0) {
                const firstItem = riskInfo.DataList[0];
                riskHtml += `<div class="qcc-data-item"><strong>最新记录:</strong>`;
                if (key === 'ShiXin') {
                    riskHtml += `<span>案号: ${firstItem.CaseNo || 'N/A'}, 金额: ${firstItem.Amount || 'N/A'}元, 履行情况: ${firstItem.ExecuteStatus || 'N/A'}</span>`;
                } else if (key === 'ZhiXing') {
                    riskHtml += `<span>案号: ${firstItem.CaseNo || 'N/A'}, 标的: ${firstItem.BiaoDi || 'N/A'}元, 立案日期: ${firstItem.RegisterDate || 'N/A'}</span>`;
                } else if (key === 'AdminPenalty' || key === 'EnvPunishment') {
                    riskHtml += `<span>文书号: ${firstItem.DocNo || 'N/A'}, 处罚金额: ${firstItem.PunishAmt || 'N/A'}元, 处罚日期: ${firstItem.PunishDate || 'N/A'}</span>`;
                } else if (key === 'Exception' || key === 'SeriousIllegal') {
                    riskHtml += `<span>原因: ${firstItem.AddReason || 'N/A'}, 列入日期: ${firstItem.AddDate || 'N/A'}</span>`;
                } else if (key === 'EquityFreeze') {
                    riskHtml += `<span>被执行人: ${firstItem.BeExecuted || 'N/A'}, 股权数额: ${firstItem.EquityAmount || 'N/A'}, 状态: ${firstItem.Status || 'N/A'}</span>`;
                } else if (key === 'EquityPledge') {
                    riskHtml += `<span>出质人: ${firstItem.PledgorList?.join(', ') || 'N/A'}, 质权人: ${firstItem.PledgeeList?.join(', ') || 'N/A'}, 股权数额: ${firstItem.PledgedAmount || 'N/A'}</span>`;
                } else if (key === 'ChattelMortgage') {
                    riskHtml += `<span>登记号: ${firstItem.RegisterNo || 'N/A'}, 担保债权数额: ${firstItem.SecureClaimsAmount || 'N/A'}, 状态: ${firstItem.Status || 'N/A'}</span>`;
                } else if (key === 'JudicialSale') {
                    riskHtml += `<span>标题: ${firstItem.Name || 'N/A'}, 拍卖时间: ${firstItem.AuctionTime || 'N/A'}</span>`;
                } else if (key === 'Bankruptcy') {
                    riskHtml += `<span>案号: ${firstItem.CaseNo || 'N/A'}, 申请人: ${firstItem.ApplicantList?.join(', ') || 'N/A'}, 公开日期: ${firstItem.PublicDate || 'N/A'}</span>`;
                } else if (key === 'Sumptuary') {
                    riskHtml += `<span>限消对象: ${firstItem.CompanyName || 'N/A'}, 案号: ${firstItem.CaseNo || 'N/A'}, 发布日期: ${firstItem.PublicDate || 'N/A'}</span>`;
                } else if (key === 'TaxOweNotice') {
                    riskHtml += `<span>税种: ${firstItem.Title || 'N/A'}, 欠税余额: ${firstItem.Amount || 'N/A'}元, 发布日期: ${firstItem.PublishDate || 'N/A'}</span>`;
                } else if (key === 'TaxIllegal') {
                    riskHtml += `<span>案件性质: ${firstItem.CaseNature || 'N/A'}, 发布日期: ${firstItem.PublishDate || 'N/A'}</span>`;
                } else if (key === 'TaxAbnormal') {
                    riskHtml += `<span>列入机关: ${firstItem.AddOffice || 'N/A'}, 列入日期: ${firstItem.AddDate || 'N/A'}</span>`;
                } else if (key === 'TaxHurry') {
                    riskHtml += `<span>税种: ${firstItem.TaxCategory || 'N/A'}, 欠缴金额: ${firstItem.TaxOwedAmt || 'N/A'}元, 缴款期限: ${firstItem.DeadlineDate || 'N/A'}</span>`;
                } else if (key === 'TaxReminder') {
                    riskHtml += `<span>税种: ${firstItem.TaxCategory || 'N/A'}, 所属期: ${firstItem.PeriodStartDate || 'N/A'}至${firstItem.PeriodEndDate || 'N/A'}, 发布日期: ${firstItem.PublishDate || 'N/A'}</span>`;
                }
                riskHtml += `</div>`;
            }
            riskHtml += `</div>`;
            html += riskHtml;
        }
    }

    // Special handling for Liquidation if it exists and has data
    if (data.Liquidation && (data.Liquidation.Leader || data.Liquidation.Member)) {
        html += `
            <div class="qcc-data-card">
                <h4><i class="fas fa-undo-alt"></i> 清算信息</h4>
                <div class="qcc-data-item"><strong>清算组负责人:</strong> <span>${data.Liquidation.Leader || 'N/A'}</span></div>
                <div class="qcc-data-item"><strong>清算组成员:</strong> <span>${data.Liquidation.Member || 'N/A'}</span></div>
            </div>
        `;
    }

    html += `</div>`;
    containerElement.innerHTML = html;
}

// Render function for Shixin Data (失信核查)
function renderShixinData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关失信信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-user-times"></i> 失信记录列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>案号:</strong> <span>${data.Anno || 'N/A'}</span><br>
                <strong>立案日期:</strong> <span>${data.Liandate || 'N/A'}</span><br>
                <strong>执行法院:</strong> <span>${data.Executegov || 'N/A'}</span><br>
                <strong>涉案金额:</strong> <span>${data.Amount || 'N/A'}元</span><br>
                <strong>履行情况:</strong> <span>${data.Executestatus || 'N/A'}</span><br>
                <strong>失信行为:</strong> <span>${data.ActionRemark || 'N/A'}</span><br>
                <strong>发布日期:</strong> <span>${data.Publicdate || 'N/A'}</span>
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Exception Data (经营异常核查)
function renderExceptionData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关经营异常信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-exclamation-circle"></i> 经营异常记录列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>列入原因:</strong> <span>${data.AddReason || 'N/A'}</span><br>
                <strong>列入日期:</strong> <span>${data.AddDate || 'N/A'}</span><br>
                <strong>作出决定机关:</strong> <span>${data.DecisionOffice || 'N/A'}</span>
                ${data.RomoveReason ? `<br><strong>移出原因:</strong> <span>${data.RomoveReason || 'N/A'}</span>` : ''}
                ${data.RemoveDate ? `<br><strong>移出日期:</strong> <span>${data.RemoveDate || 'N/A'}</span>` : ''}
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Zhixing Data (被执行人核查)
function renderZhixingData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关被执行信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-gavel"></i> 被执行记录列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>案号:</strong> <span>${data.Anno || 'N/A'}</span><br>
                <strong>立案时间:</strong> <span>${data.Liandate || 'N/A'}</span><br>
                <strong>执行法院:</strong> <span>${data.ExecuteGov || 'N/A'}</span><br>
                <strong>执行标的:</strong> <span>${data.Biaodi || 'N/A'}元</span><br>
                <strong>疑似申请执行人:</strong> <span>${data.SuspectedApplicant || 'N/A'}</span>
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Serious Illegal Data (严重违法核查)
function renderSeriousIllegalData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关严重违法信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-exclamation-triangle"></i> 严重违法记录列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>列入原因:</strong> <span>${data.AddReason || 'N/A'}</span><br>
                <strong>列入时间:</strong> <span>${data.AddDate || 'N/A'}</span><br>
                <strong>列入决定机关:</strong> <span>${data.AddOffice || 'N/A'}</span>
                ${data.RemoveReason ? `<br><strong>移除原因:</strong> <span>${data.RemoveReason || 'N/A'}</span>` : ''}
                ${data.RemoveDate ? `<br><strong>移除时间:</strong> <span>${data.RemoveDate || 'N/A'}</span>` : ''}
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}

// Render function for Judgment Doc Data (裁决文书核查)
function renderJudgmentDocData(dataList, containerElement) {
    if (!dataList || dataList.length === 0) {
        containerElement.innerHTML = '<p class="qcc-error">未找到相关裁决文书信息。</p>';
        return;
    }

    let html = `
        <div class="qcc-data-card">
            <h4><i class="fas fa-file-alt"></i> 裁决文书列表 (前5条)</h4>
            <ul class="qcc-nested-list">
    `;

    dataList.slice(0, 5).forEach((data, index) => {
        html += `
            <li>
                <strong>文书标题:</strong> <span>${data.CaseName || 'N/A'}</span><br>
                <strong>案号:</strong> <span>${data.CaseNo || 'N/A'}</span><br>
                <strong>案由:</strong> <span>${data.CaseReason || 'N/A'}</span><br>
                <strong>案件金额:</strong> <span>${data.Amount || 'N/A'}元</span><br>
                <strong>裁判日期:</strong> <span>${data.JudgeDate || 'N/A'}</span><br>
                <strong>发布日期:</strong> <span>${data.PublishDate || 'N/A'}</span><br>
                <strong>当事人:</strong> <span>${data.PartyList?.map(p => `${p.Name || 'N/A'}(${p.RoleType || 'N/A'})`).join(', ') || 'N/A'}</span><br>
                <strong>裁判结果:</strong> <span>${data.JudgeResult ? data.JudgeResult.substring(0, 150) + (data.JudgeResult.length > 150 ? '...' : '') : 'N/A'}</span>
            </li>
        `;
    });

    html += `
            </ul>
        </div>
    `;
    containerElement.innerHTML = html;
}