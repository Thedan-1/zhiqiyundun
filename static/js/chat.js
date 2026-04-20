// static/js/chat.js

let chatHistory = []; // Stores chat history
const MAX_CHAT_HISTORY = 5; // Max number of chat turns to retain

// Get context data for the current page
function getPageContext() {
    const path = window.location.pathname;
    let context = {
        page: path,
        lastAnalysis: null // Will store the relevant last analysis data
    };

    // Check for a specific report being viewed
    if (path.startsWith('/report/')) {
        const reportId = path.split('/').pop();
        const reportBluelmOutput = document.getElementById('reportBluelmOutput')?.value; // Get BlueLM output from hidden input
        const reportType = document.getElementById('reportType')?.value || 'unknown'; // Get report type
        const reportCompanyName = document.getElementById('reportCompanyName')?.value || '未知企业'; // Get company name from hidden input

        context.lastAnalysis = {
            type: 'report_view',
            reportId: reportId,
            companyName: reportCompanyName,
            totalRisk: document.querySelector('.report-subtitle .risk-score')?.textContent.trim() || '--',
            bluelmOutput: reportBluelmOutput, // Pass the full BlueLM output
            reportType: reportType // Pass the specific report type
        };
    } else {
        // Retrieve last analysis from session storage based on current page type
        // This prioritizes the most recent relevant analysis for the current view
        if (path.includes('q1_qiyexinxihecha')) {
            const lastQccData = sessionStorage.getItem('lastQccData');
            if (lastQccData) context.lastAnalysis = JSON.parse(lastQccData);
        } else if (path.includes('q1_gongshangxinxi')) {
            const lastIndustrialInfoData = sessionStorage.getItem('lastIndustrialInfoData');
            if (lastIndustrialInfoData) context.lastAnalysis = JSON.parse(lastIndustrialInfoData);
        } else if (path.includes('q1_mohusousuo')) {
            const lastFuzzySearchData = sessionStorage.getItem('lastFuzzySearchData');
            if (lastFuzzySearchData) context.lastAnalysis = JSON.parse(lastFuzzySearchData);
        } else if (path.includes('q1_shuihaokaipiao')) {
            const lastTaxInvoiceData = sessionStorage.getItem('lastTaxInvoiceData');
            if (lastTaxInvoiceData) context.lastAnalysis = JSON.parse(lastTaxInvoiceData);
        } else if (path.includes('q2_kehushenfenshibie')) {
            const lastKycData = sessionStorage.getItem('lastKycData');
            if (lastKycData) context.lastAnalysis = JSON.parse(lastKycData);
        } else if (path.includes('q2_zizhizhengshu')) {
            const lastCertificationData = sessionStorage.getItem('lastCertificationData');
            if (lastCertificationData) context.lastAnalysis = JSON.parse(lastCertificationData);
        } else if (path.includes('q2_shangbiaochaxun')) {
            const lastTrademarkData = sessionStorage.getItem('lastTrademarkData');
            if (lastTrademarkData) context.lastAnalysis = JSON.parse(lastTrademarkData);
        } else if (path.includes('q2_zhuanlichaxun')) {
            const lastPatentData = sessionStorage.getItem('lastPatentData');
            if (lastPatentData) context.lastAnalysis = JSON.parse(lastPatentData);
        } else if (path.includes('q2_nianbaoxinxi')) {
            const lastAnnualReportData = sessionStorage.getItem('lastAnnualReportData');
            if (lastAnnualReportData) context.lastAnalysis = JSON.parse(lastAnnualReportData);
        } else if (path.includes('q3_zonghefengxianpaizha')) { // 新增：综合风险排查上下文
            const lastComprehensiveRiskData = sessionStorage.getItem('lastComprehensiveRiskData');
            if (lastComprehensiveRiskData) context.lastAnalysis = JSON.parse(lastComprehensiveRiskData);
        } else if (path.includes('q3_shixinhecha')) { // 新增：失信核查上下文
            const lastShixinData = sessionStorage.getItem('lastShixinData');
            if (lastShixinData) context.lastAnalysis = JSON.parse(lastShixinData);
        } else if (path.includes('q3_jingyinyichanghecha')) { // 新增：经营异常核查上下文
            const lastExceptionData = sessionStorage.getItem('lastExceptionData');
            if (lastExceptionData) context.lastAnalysis = JSON.parse(lastExceptionData);
        } else if (path.includes('q3_beizhixingrenhecha')) { // 新增：被执行人核查上下文
            const lastZhixingData = sessionStorage.getItem('lastZhixingData');
            if (lastZhixingData) context.lastAnalysis = JSON.parse(lastZhixingData);
        } else if (path.includes('q3_yanzhongweifahecha')) { // 新增：严重违法核查上下文
            const lastSeriousIllegalData = sessionStorage.getItem('lastSeriousIllegalData');
            if (lastSeriousIllegalData) context.lastAnalysis = JSON.parse(lastSeriousIllegalData);
        } else if (path.includes('q3_caipanwenshuhecha')) { // 新增：裁决文书核查上下文
            const lastJudgmentDocData = sessionStorage.getItem('lastJudgmentDocData');
            if (lastJudgmentDocData) context.lastAnalysis = JSON.parse(lastJudgmentDocData);
        } else if (path === '/') { // Dashboard page
            const lastAssessmentData = sessionStorage.getItem('lastAssessmentData');
            if (lastAssessmentData) context.lastAnalysis = JSON.parse(lastAssessmentData);
        }
    }

    return context;
}

// Display a message in the chat window
function displayMessage(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error("chatMessages element not found.");
        return;
    }
    const messageElement = document.createElement('div');
    messageElement.classList.add('chat-message', sender);
    messageElement.innerHTML = `<p>${message}</p>`;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom to show latest message
}

// Send user message to backend chatbot API
async function sendChatMessageToBackend(userMessage) {
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');

    if (!chatInput || !sendChatBtn) {
        console.error("Chat input or send button not found.");
        return;
    }

    sendChatBtn.disabled = true; // Disable button to prevent multiple submissions
    chatInput.disabled = true;   // Disable input
    chatInput.placeholder = "AI 思考中..."; // Show thinking status

    displayMessage('user', userMessage); // Display user's message immediately

    const context = getPageContext(); // Get current page context
    console.log("Sending chat message with context:", context);

    // Add user message to chat history
    chatHistory.push({ role: 'user', content: userMessage });
    // Keep chat history length within limits (MAX_CHAT_HISTORY turns of user+AI messages)
    if (chatHistory.length > MAX_CHAT_HISTORY * 2) {
        chatHistory = chatHistory.slice(-MAX_CHAT_HISTORY * 2); // Keep only the most recent messages
    }

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: userMessage,
                context: context,
                chatHistory: chatHistory // Send current chat history to backend
            })
        });

        if (!response.ok) {
            // If HTTP status is not OK (e.g., 4xx, 5xx), parse error message from response
            const errorData = await response.json();
            throw new Error(errorData.error || 'Server error');
        }

        const result = await response.json(); // Parse JSON response
        const aiResponse = result.response;   // Extract AI's response
        displayMessage('ai', aiResponse);     // Display AI's response

        // Add AI message to chat history
        chatHistory.push({ role: 'ai', content: aiResponse });

    } catch (error) {
        console.error('Chatbot API error:', error);
        displayMessage('ai', `抱歉，AI助手暂时无法响应。错误: ${error.message}`); // Display error to user
    } finally {
        sendChatBtn.disabled = false; // Re-enable button
        chatInput.disabled = false;   // Re-enable input
        chatInput.value = '';         // Clear input field
        chatInput.placeholder = "输入您的问题..."; // Restore placeholder
        chatInput.focus();            // Focus input for next message
    }
}

// Initialize the chatbot functionality (event listeners, initial state)
function initializeChatbot() {
    const chatBubble = document.getElementById('chatBubble');
    const chatWindow = document.getElementById('chatWindow');
    const closeChatBtn = document.getElementById('closeChatBtn');
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');
    const chatHeader = document.querySelector('.chat-header'); // Get the header for dragging

    // Check if all necessary chatbot elements exist on the page
    if (!chatBubble || !chatWindow || !closeChatBtn || !chatInput || !sendChatBtn || !chatHeader) {
        console.warn("Chatbot elements not found. Chatbot will not be initialized.");
        return; // Exit if elements are missing
    }

    // --- Draggable Chat Window Logic ---
    let isDragging = false;
    let offsetX, offsetY; // Mouse position relative to the element's top-left corner

    chatHeader.addEventListener('mousedown', (e) => {
        isDragging = true;
        chatHeader.style.cursor = 'grabbing'; // Change cursor while dragging

        // Calculate offset relative to the chat window's current position
        const rect = chatWindow.getBoundingClientRect();
        offsetX = e.clientX - rect.left;
        offsetY = e.clientY - rect.top;

        // Ensure it's fixed for direct top/left manipulation
        chatWindow.style.position = 'fixed';
        chatWindow.style.transition = 'none'; // Disable transition during drag
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;

        // Calculate new position
        let newLeft = e.clientX - offsetX;
        let newTop = e.clientY - offsetY;

        // Boundary checks (optional but recommended)
        const windowWidth = chatWindow.offsetWidth;
        const windowHeight = chatWindow.offsetHeight;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Keep within viewport bounds
        newLeft = Math.max(0, Math.min(newLeft, viewportWidth - windowWidth));
        newTop = Math.max(0, Math.min(newTop, viewportHeight - windowHeight));

        chatWindow.style.left = `${newLeft}px`;
        chatWindow.style.top = `${newTop}px`;
        chatWindow.style.right = 'auto'; // Disable right/bottom if setting left/top
        chatWindow.style.bottom = 'auto';
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        chatHeader.style.cursor = 'grab'; // Restore cursor
        chatWindow.style.transition = 'transform 0.3s ease-out, opacity 0.3s ease-out'; // Re-enable transition
    });
    // --- End Draggable Chat Window Logic ---

    // Event listener for clicking the chat bubble to open/close the chat window
    chatBubble.addEventListener('click', () => {
        chatWindow.classList.toggle('open'); // Toggle 'open' class for visibility
        if (chatWindow.classList.contains('open')) {
            // Set initial position if not already set by dragging
            // Check if left/top are explicitly set by dragging, if not, apply default
            if (!chatWindow.style.left || chatWindow.style.left === 'auto') {
                const defaultRight = 30; // From CSS
                const defaultBottom = 100; // From CSS
                chatWindow.style.left = `${window.innerWidth - chatWindow.offsetWidth - defaultRight}px`;
                chatWindow.style.top = `${window.innerHeight - chatWindow.offsetHeight - defaultBottom}px`;
                chatWindow.style.right = 'auto';
                chatWindow.style.bottom = 'auto';
            }
            chatInput.focus(); // Focus input when opened
            // On first open, if there's a last analysis, prompt the user with context
            const context = getPageContext();
            if (context.lastAnalysis && chatHistory.length === 0) { // Only prompt if no chat history exists yet
                let welcomeMessage = "您好！我是您的AI智能助手。";
                let companyNameDisplay = context.lastAnalysis.companyName || '这家企业';

                if (context.lastAnalysis.type === 'dashboard_assessment') {
                    welcomeMessage += `我注意到您刚刚评估了 <strong>${companyNameDisplay}</strong>。您想了解更多关于该公司的风险或建议吗？`;
                } else if (context.lastAnalysis.type === 'qcc_verification') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的企查查信息。您想了解更多关于该公司的风险、股权结构或经营状况吗？`;
                } else if (context.lastAnalysis.type === 'industrial_info_query') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的企业工商信息。您想了解更多关于该公司的注册详情或潜在风险吗？`;
                } else if (context.lastAnalysis.type === 'fuzzy_search_query') {
                    companyNameDisplay = context.lastAnalysis.searchKey || '某个关键词'; // Fuzzy search uses searchKey
                    welcomeMessage += `我注意到您刚刚进行了 <strong>${companyNameDisplay}</strong> 的企业模糊搜索。您想了解搜索结果的潜在风险或进一步的核实建议吗？`;
                } else if (context.lastAnalysis.type === 'tax_invoice_query') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的税号开票信息。您想了解更多关于该公司的税务合规或财务风险吗？`;
                } else if (context.lastAnalysis.type === 'kyc_verify') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的客户身份识别（KYC）信息。您想了解更多关于该公司的身份真实性、股权结构或合规风险吗？`;
                } else if (context.lastAnalysis.type === 'certification') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的资质证书信息。您想了解更多关于该公司的资质有效性或合规风险吗？`;
                } else if (context.lastAnalysis.type === 'trademark') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的全国商标信息。您想了解更多关于该公司的商标保护或侵权风险吗？`;
                } else if (context.lastAnalysis.type === 'patent') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的专利信息。您想了解更多关于该公司的专利保护或技术创新风险吗？`;
                } else if (context.lastAnalysis.type === 'annual_report') {
                    welcomeMessage += `我注意到您刚刚查询了 <strong>${companyNameDisplay}</strong> 的企业年报信息。您想了解更多关于该公司的财务健康状况或经营稳定性吗？`;
                } else if (context.lastAnalysis.type === 'comprehensive_risk') { // 新增：综合风险排查
                    welcomeMessage += `我注意到您刚刚对 <strong>${companyNameDisplay}</strong> 进行了综合风险排查。您想了解更多关于该公司的司法涉诉、经营合规或财务资产风险吗？`;
                } else if (context.lastAnalysis.type === 'shixin_check') { // 新增：失信核查
                    welcomeMessage += `我注意到您刚刚对 <strong>${companyNameDisplay}</strong> 进行了失信核查。您想了解更多关于该公司的信用风险或法律风险吗？`;
                } else if (context.lastAnalysis.type === 'exception_check') { // 新增：经营异常核查
                    welcomeMessage += `我注意到您刚刚对 <strong>${companyNameDisplay}</strong> 进行了经营异常核查。您想了解更多关于该公司的经营合规或市场信誉风险吗？`;
                } else if (context.lastAnalysis.type === 'zhixing_check') { // 新增：被执行人核查
                    welcomeMessage += `我注意到您刚刚对 <strong>${companyNameDisplay}</strong> 进行了被执行人核查。您想了解更多关于该公司的法律风险或财务偿付能力吗？`;
                } else if (context.lastAnalysis.type === 'serious_illegal_check') { // 新增：严重违法核查
                    welcomeMessage += `我注意到您刚刚对 <strong>${companyNameDisplay}</strong> 进行了严重违法核查。您想了解更多关于该公司的法律合规或市场信誉风险吗？`;
                } else if (context.lastAnalysis.type === 'judgment_doc_check') { // 新增：裁决文书核查
                    welcomeMessage += `我注意到您刚刚对 <strong>${companyNameDisplay}</strong> 进行了裁决文书核查。您想了解更多关于该公司的法律诉讼或财务影响风险吗？`;
                } else if (context.lastAnalysis.type === 'report_view') {
                    welcomeMessage += `您好！我注意到您正在查看 <strong>${companyNameDisplay}</strong> 的详细报告。您想深入了解报告中的某个风险点，或者需要其他帮助吗？`;
                }
                displayMessage('ai', welcomeMessage); // Display the contextual welcome message
                chatHistory.push({ role: 'ai', content: welcomeMessage }); // Add to history
            }
        }
    });

    // Event listener for closing the chat window
    closeChatBtn.addEventListener('click', () => {
        chatWindow.classList.remove('open'); // Remove 'open' class to hide
    });

    // Event listener for sending a chat message when the send button is clicked
    sendChatBtn.addEventListener('click', () => {
        const message = chatInput.value.trim(); // Get message from input and trim whitespace
        if (message) { // Only send if message is not empty
            sendChatMessageToBackend(message);
        }
    });

    // Event listener for sending a chat message when Enter key is pressed in the input field
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendChatBtn.click(); // Simulate a click on the send button
        }
    });
}

// Ensure chatbot initialization is called after the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initializeChatbot);