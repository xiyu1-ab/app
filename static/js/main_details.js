// static/js/main_details.js

// --- 获取 HTML 元素 (保持不变) ---
const stationSelector = document.getElementById('stationSelector');
const dateSelector = document.getElementById('dateSelector');
const messageDiv = document.getElementById('message');
const nextPointInfoDiv = document.getElementById('nextPointInfo');
const nextTimeSpan = document.getElementById('nextTime');
const nextValueSpan = document.getElementById('nextValue');
const highlightIndicator = document.getElementById('highlightIndicator');
const ctx = document.getElementById('predictionChart').getContext('2d');

// --- 全局变量和配置 (保持不变) ---
let predictionChart = null;
const highlightColor = 'red';
const defaultPointColor = 'rgba(255, 99, 132, 0.6)';
const defaultBorderColor = 'rgb(255, 99, 132)';
const highlightBorderColor = 'darkred';
const defaultUnit = 'MW';

// --- 函数定义 (padZero, getCurrentTimeString, getTodayString, updateChart 保持不变) ---
function padZero(num) { /* ... */ return num.toString().padStart(2, '0'); }
function getCurrentTimeString() { /* ... */ const now = new Date(); return `${padZero(now.getHours())}:${padZero(now.getMinutes())}:${padZero(now.getSeconds())}`; }
function getTodayString() { /* ... */ return new Date().toISOString().split('T')[0]; }
async function updateChart(stationName, dateString) { /* ... (函数体与之前最终版完全相同) ... */
    // 1. 清理工作区
    messageDiv.textContent = '';
    nextTimeSpan.textContent = '--:--:--';
    nextValueSpan.textContent = `--- ${defaultUnit}`;
    highlightIndicator.style.backgroundColor = 'transparent';
    highlightIndicator.style.borderColor = 'transparent';

    // 2. 输入验证
    if (!stationName || !dateString) {
        messageDiv.textContent = "请选择有效的站点和日期。";
        if (predictionChart) { predictionChart.destroy(); predictionChart = null; }
        return;
    }

    console.log(`请求数据: 站点='${stationName}', 日期='${dateString}'`);
    try {
        // 3. 调用后端 API 获取数据
        const apiUrl = `/api/data/${stationName}/${dateString}`;
        const response = await fetch(apiUrl);

        if (!response.ok) { // 处理 HTTP 错误
            let errorMsg = `获取数据失败 (${response.status})`;
            try { const errorData = await response.json(); if (errorData && errorData.error) errorMsg += `: ${errorData.error}`; } catch (e) {}
            throw new Error(errorMsg);
        }

        const data = await response.json();
        console.log("成功接收数据:", data);

        // 4. 检查返回的数据是否有效
        if (data.message || !data.timestamps || data.timestamps.length === 0) {
            messageDiv.textContent = data.message || "该日期没有可用的预测数据。";
            if (predictionChart) { predictionChart.destroy(); predictionChart = null; }
            nextPointInfoDiv.style.display = 'none';
            return;
        } else {
             nextPointInfoDiv.style.display = 'inline-block';
        }

        // 5. 查找需要高亮的下一个预测点索引
        const currentTimeString = getCurrentTimeString();
        const todayString = getTodayString();
        let nextPointIndex = -1;
        for (let i = 0; i < data.timestamps.length; i++) { if (data.timestamps[i] > currentTimeString) { nextPointIndex = i; break; } }
        if (nextPointIndex === -1 && data.timestamps.length > 0) {
             if (dateString === todayString) { nextPointIndex = data.timestamps.length - 1; console.log("当前时间已过今日最后一个点，高亮最后一个。"); }
             else if (dateString > todayString) { nextPointIndex = 0; console.log("选择未来日期，高亮第一个点。"); }
             else { console.log("选择过去日期，不进行高亮。"); }
        }

        // 6. 更新下一个预测点的信息显示区域
        if (nextPointIndex !== -1) {
            const nextTime = data.timestamps[nextPointIndex];
            const nextValueRaw = data.predictions[nextPointIndex];
            const nextValueFormatted = typeof nextValueRaw === 'number' ? nextValueRaw.toFixed(2) : 'N/A';
            nextTimeSpan.textContent = nextTime;
            nextValueSpan.textContent = `${nextValueFormatted} ${defaultUnit}`;
            highlightIndicator.style.backgroundColor = highlightColor;
            highlightIndicator.style.borderColor = highlightBorderColor;
            console.log(`高亮索引 ${nextPointIndex}: 时间 ${nextTime}, 值 ${nextValueFormatted}`);
        } else {
             console.log("没有找到需要高亮的点。");
        }

        // 7. 准备 Chart.js 数据集和配置
        const chartData = {
            labels: data.timestamps,
            datasets: [{
                label: '预测值', data: data.predictions, borderColor: defaultBorderColor, backgroundColor: 'rgba(255, 99, 132, 0.1)',
                borderWidth: 1.5, tension: 0.1, fill: true,
                pointRadius: (context) => context.dataIndex === nextPointIndex ? 5 : 2,
                pointHoverRadius: (context) => context.dataIndex === nextPointIndex ? 7 : 4,
                pointBackgroundColor: (context) => context.dataIndex === nextPointIndex ? highlightColor : defaultPointColor,
                pointBorderColor: (context) => context.dataIndex === nextPointIndex ? highlightBorderColor : defaultBorderColor,
                pointBorderWidth: (context) => context.dataIndex === nextPointIndex ? 2 : 1,
            }]
        };

        // 8. 获取下拉菜单选中的显示文本 (e.g., "光伏电站1") 用于标题
        const selectedStationDisplayName = stationSelector.options[stationSelector.selectedIndex].text;

        // 9. 销毁旧图表（如果存在）
        if (predictionChart) { predictionChart.destroy(); }

        // 10. 创建并渲染新图表
        predictionChart = new Chart(ctx, {
            type: 'line', data: chartData,
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `${selectedStationDisplayName} - ${dateString} - 预测功率`, font: { size: 16, weight: 'bold' }, padding: { top: 10, bottom: 20 } },
                    tooltip: { mode: 'index', intersect: false, callbacks: { label: function(context) { let label = context.dataset.label || ''; if (label) { label += ': '; } if (context.parsed.y !== null) { label += context.parsed.y.toFixed(2) + ` ${defaultUnit}`; } return label; } } },
                    legend: { position: 'top', labels: { boxWidth: 20, padding: 15 } },
                },
                scales: {
                    x: { display: true, title: { display: true, text: '时间 (HH:MM:SS)', font: { size: 13 } }, ticks: { autoSkip: true, maxTicksLimit: 15, maxRotation: 0, minRotation: 0 } },
                    y: { display: true, title: { display: true, text: `预测功率 (${defaultUnit})`, font: { size: 13 } }, beginAtZero: true }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false },
                animation: { duration: 500, easing: 'easeInOutQuad' }
            }
        });
        console.log("图表已成功更新并渲染");

    } catch (error) {
        console.error("更新图表过程中发生错误:", error);
        messageDiv.textContent = `加载图表时出错: ${error.message}`;
        if (predictionChart) { predictionChart.destroy(); predictionChart = null; }
        nextPointInfoDiv.style.display = 'none';
    }
}

// --- 事件监听器设置 (保持不变) ---
function handleSelectionChange() {
    const selectedStation = stationSelector.value;
    const selectedDate = dateSelector.value;
    updateChart(selectedStation, selectedDate);
}
stationSelector.addEventListener('change', handleSelectionChange);
dateSelector.addEventListener('change', handleSelectionChange);

// --- 页面初始化 (修改这里) ---
function initializePage() {
    // 1. 处理 URL 参数，尝试预选电站
    const urlParams = new URLSearchParams(window.location.search);
    const stationIdFromUrl = urlParams.get('station');
    let initialStationSelected = false; // 标记是否通过 URL 参数成功选择了电站

    if (stationIdFromUrl && stationSelector) {
        // 检查这个 ID 是否在下拉选项中存在
        const optionExists = Array.from(stationSelector.options).some(option => option.value === stationIdFromUrl);
        if (optionExists) {
            stationSelector.value = stationIdFromUrl; // 设置下拉菜单的值
            console.log(`通过 URL 参数预选电站: ${stationIdFromUrl}`);
            initialStationSelected = true;
        } else {
            console.warn(`URL 参数中的电站 ID '${stationIdFromUrl}' 在下拉菜单中未找到。`);
        }
    }

    // 2. 设置日期选择器的默认值 (保持不变)
    const today = getTodayString();
    const minDate = dateSelector.min;
    const maxDate = dateSelector.max;
    if (dateSelector.disabled) {
        console.warn("日期选择器被禁用，无法设置默认值。");
    } else if (today >= minDate && today <= maxDate) {
        dateSelector.value = today;
    } else if (minDate) {
        dateSelector.value = minDate;
    }

    // 3. 加载初始图表
    if (stationSelector.value && dateSelector.value) {
        console.log(`页面初始化，加载图表: 站点=${stationSelector.value}, 日期=${dateSelector.value}`);
        handleSelectionChange(); // 使用当前选定的值加载初始图表
    } else if (!initialStationSelected) { // 只有当没有通过 URL 选定，并且默认选项无效时才显示警告
        console.warn("无法获取有效的初始站点或日期，不加载初始图表。");
        messageDiv.textContent = "请选择站点和日期以查看预测数据。";
        nextPointInfoDiv.style.display = 'none';
    } else {
         // 如果通过 URL 选定了，即使日期无效也尝试加载（updateChart会处理日期无效）
         console.log("通过 URL 选定电站，但日期可能无效，尝试加载...");
         handleSelectionChange();
    }
}

// --- tsParticles 初始化 (保持不变) ---
async function loadParticlesDetails() { // 重命名函数避免冲突 (如果放一个文件里)
    await tsParticles.load("page-body", { // 目标是 body
        fpsLimit: 60,
        particles: { /* ... (与 main_index.js 相同的粒子配置) ... */
            number: { value: 80, density: { enable: true, value_area: 800 } },
            color: { value: "#aaaaaa" },
            shape: { type: "circle" },
            opacity: { value: 0.6, random: true, anim: { enable: true, speed: 0.8, opacity_min: 0.2, sync: false } },
            size: { value: 2.5, random: true, anim: { enable: false } },
            links: { enable: true, distance: 130, color: "#bbbbbb", opacity: 0.3, width: 1 },
            move: { enable: true, speed: 1.5, direction: "none", random: true, straight: false, out_mode: "out", bounce: false, attract: { enable: false } }
         },
        interactivity: {
            detect_on: "canvas", // 交互只在空白区域有效
            events: {
                onhover: { enable: true, mode: "attract" },
                onclick: { enable: true, mode: "push" },
                resize: true
            },
            modes: {
                attract: { distance: 150, duration: 0.4, speed: 1 },
                push: { particles_nb: 4 },
            }
        },
        detectRetina: true,
    });
    console.log("Details page tsParticles loaded onto body.");
}

// --- 执行初始化 ---
initializePage(); // 初始化页面逻辑 (包括URL参数处理)
loadParticlesDetails().catch(error => { // 加载粒子效果
    console.error("Error loading details page tsParticles:", error);
});