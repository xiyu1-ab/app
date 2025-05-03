// static/js/main.js

// --- 获取 HTML 元素 ---
const stationSelector = document.getElementById('stationSelector');
const dateSelector = document.getElementById('dateSelector');
const messageDiv = document.getElementById('message');
const nextPointInfoDiv = document.getElementById('nextPointInfo');
const nextTimeSpan = document.getElementById('nextTime');
const nextValueSpan = document.getElementById('nextValue');
const highlightIndicator = document.getElementById('highlightIndicator');
const ctx = document.getElementById('predictionChart').getContext('2d');
const breadcrumbStationName = document.getElementById('breadcrumb-station-name'); // 获取面包屑导航中显示站名的 span 元素
// --- 全局变量和配置 ---
let predictionChart = null; // 存储 Chart 实例
const highlightColor = 'red'; // 高亮颜色
const defaultPointColor = 'rgba(255, 99, 132, 0.6)'; // 预测曲线点的默认颜色 (略透明)
const defaultBorderColor = 'rgb(255, 99, 132)';     // 预测曲线线条的默认颜色
const highlightBorderColor = 'darkred';            // 高亮点的边框颜色
const defaultUnit = 'MW';                          // 默认单位

// --- 函数定义 ---

/**
 * 格式化数字，确保至少两位数，不足则前面补零
 * @param {number} num - 需要格式化的数字
 * @returns {string} 格式化后的字符串
 */
function padZero(num) {
    return num.toString().padStart(2, '0');
}

/**
 * 获取当前时间的 HH:MM:SS 格式字符串
 * @returns {string} HH:MM:SS 格式的当前时间
 */
function getCurrentTimeString() {
    const now = new Date();
    const hours = padZero(now.getHours());
    const minutes = padZero(now.getMinutes());
    const seconds = padZero(now.getSeconds());
    return `${hours}:${minutes}:${seconds}`;
}

/**
 * 获取今天的 YYYY-MM-DD 格式字符串
 * @returns {string} YYYY-MM-DD 格式的今天日期
 */
function getTodayString() {
    return new Date().toISOString().split('T')[0];
}


/**
 * 主函数：根据选择的站点和日期更新图表及相关信息
 * @param {string} stationName - 选中的站点原始名称 (e.g., 'StationA')
 * @param {string} dateString - 选中的日期字符串 (YYYY-MM-DD)
 */
async function updateChart(stationName, dateString) {
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
            try {
                const errorData = await response.json();
                if (errorData && errorData.error) errorMsg += `: ${errorData.error}`;
            } catch (e) { /* 忽略解析错误 */ }
            throw new Error(errorMsg);
        }

        const data = await response.json();
        console.log("成功接收数据:", data);

        // 4. 检查返回的数据是否有效
        if (data.message || !data.timestamps || data.timestamps.length === 0) {
            messageDiv.textContent = data.message || "该日期没有可用的预测数据。";
            if (predictionChart) { predictionChart.destroy(); predictionChart = null; }
            nextPointInfoDiv.style.display = 'none'; // 隐藏信息栏
            return;
        } else {
             nextPointInfoDiv.style.display = 'inline-block'; // 确保信息栏可见
        }

        // 5. 查找需要高亮的下一个预测点索引
        const currentTimeString = getCurrentTimeString();
        const todayString = getTodayString();
        let nextPointIndex = -1; // -1 表示没有找到或不需高亮

        for (let i = 0; i < data.timestamps.length; i++) {
            if (data.timestamps[i] > currentTimeString) {
                nextPointIndex = i;
                break; // 找到第一个大于当前时间的点
            }
        }

        // 处理当天时间已过所有点的情况
        if (nextPointIndex === -1 && data.timestamps.length > 0) {
             if (dateString === todayString) { // 如果是今天
                 nextPointIndex = data.timestamps.length - 1; // 高亮最后一个点
                 console.log("当前时间已过今日最后一个点，高亮最后一个。");
             } else if (dateString > todayString) { // 如果是未来日期
                 nextPointIndex = 0; // 高亮第一个点
                 console.log("选择未来日期，高亮第一个点。");
             } else { // 如果是过去日期
                 console.log("选择过去日期，不进行高亮。");
                 // nextPointIndex 保持 -1
             }
        }

        // 6. 更新下一个预测点的信息显示区域
        if (nextPointIndex !== -1) {
            const nextTime = data.timestamps[nextPointIndex];
            const nextValueRaw = data.predictions[nextPointIndex];
            // 格式化预测值，保留两位小数，处理非数字情况
            const nextValueFormatted = typeof nextValueRaw === 'number'
                                      ? nextValueRaw.toFixed(2)
                                      : 'N/A';
            nextTimeSpan.textContent = nextTime;
            nextValueSpan.textContent = `${nextValueFormatted} ${defaultUnit}`;
            highlightIndicator.style.backgroundColor = highlightColor; // 显示高亮指示器
            highlightIndicator.style.borderColor = highlightBorderColor;
            console.log(`高亮索引 ${nextPointIndex}: 时间 ${nextTime}, 值 ${nextValueFormatted}`);
        } else {
             console.log("没有找到需要高亮的点。");
             // 保持信息栏默认文本和隐藏的指示器
        }

        // 7. 准备 Chart.js 数据集和配置
        const chartData = {
            labels: data.timestamps,
            datasets: [{
                label: '预测值',
                data: data.predictions,
                borderColor: defaultBorderColor,
                backgroundColor: 'rgba(255, 99, 132, 0.1)', // 淡粉色填充区域
                borderWidth: 1.5,
                tension: 0.1, // 轻微曲线
                fill: true,
                pointRadius: (context) => context.dataIndex === nextPointIndex ? 5 : 2, // 高亮 vs 默认点大小
                pointHoverRadius: (context) => context.dataIndex === nextPointIndex ? 7 : 4, // 悬停时点大小
                pointBackgroundColor: (context) => context.dataIndex === nextPointIndex ? highlightColor : defaultPointColor,
                pointBorderColor: (context) => context.dataIndex === nextPointIndex ? highlightBorderColor : defaultBorderColor,
                pointBorderWidth: (context) => context.dataIndex === nextPointIndex ? 2 : 1, // 高亮点的边框稍粗
            }]
        };

        // 8. 获取下拉菜单选中的显示文本 (e.g., "光伏电站1") 用于标题
        const selectedStationDisplayName = stationSelector.options[stationSelector.selectedIndex].text;

        // 9. 销毁旧图表（如果存在）
        if (predictionChart) {
            predictionChart.destroy();
        }

        // 10. 创建并渲染新图表
        predictionChart = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true, // 图表自适应容器大小
                maintainAspectRatio: false, // 允许图表改变宽高比
                plugins: {
                    title: { // 图表主标题
                        display: true,
                        text: `${selectedStationDisplayName} - ${dateString} - 预测功率`,
                        font: { size: 16, weight: 'bold' },
                        padding: { top: 10, bottom: 20 }
                    },
                    tooltip: { // 鼠标悬停提示框
                        mode: 'index', // 同时显示同一时间戳的所有数据集信息
                        intersect: false, // 不必精确悬停在点上
                        callbacks: { // 自定义提示框内容
                             label: function(context) {
                                 let label = context.dataset.label || '';
                                 if (label) {
                                     label += ': ';
                                 }
                                 if (context.parsed.y !== null) {
                                      // 保留两位小数
                                     label += context.parsed.y.toFixed(2) + ` ${defaultUnit}`;
                                 }
                                 return label;
                             }
                        }
                    },
                    legend: { // 图例
                        position: 'top', // 图例放在顶部
                        labels: { boxWidth: 20, padding: 15 }
                    },
                },
                scales: { // 坐标轴配置
                    x: {
                        display: true,
                        title: { display: true, text: '时间 (HH:MM:SS)', font: { size: 13 } },
                        ticks: {
                            autoSkip: true, // 自动跳过标签以防重叠
                            maxTicksLimit: 15, // 最多显示15个刻度
                            maxRotation: 0, // 标签不旋转
                            minRotation: 0
                        }
                    },
                    y: {
                        display: true,
                        title: { display: true, text: `预测功率 (${defaultUnit})`, font: { size: 13 } },
                        beginAtZero: true, // Y轴从0开始
                        ticks: {
                             // 可以添加回调来格式化 Y 轴刻度标签，例如添加单位
                             // callback: function(value, index, values) {
                             //     return value + ` ${defaultUnit}`;
                             // }
                        }
                    }
                },
                interaction: { // 交互模式
                    mode: 'nearest', // 鼠标悬停时查找最近的点
                    axis: 'x',       // 限制在 X 轴方向查找
                    intersect: false
                },
                animation: { // 添加一点简单的动画效果
                     duration: 500, // 动画时长
                     easing: 'easeInOutQuad' // 缓动函数
                }
            }
        });
        console.log("图表已成功更新并渲染");

    } catch (error) { // 统一处理 fetch 或后续逻辑中的错误
        console.error("更新图表过程中发生错误:", error);
        messageDiv.textContent = `加载图表时出错: ${error.message}`;
        if (predictionChart) { predictionChart.destroy(); predictionChart = null; }
        nextPointInfoDiv.style.display = 'none'; // 出错时也隐藏信息栏
    }
}

// --- 事件监听器设置 ---

/**
 * 处理下拉菜单或日期选择器变化的事件回调函数
 */
function handleSelectionChange() {
    const selectedStation = stationSelector.value; // 获取原始站点名
    const selectedDate = dateSelector.value;       // 获取日期 YYYY-MM-DD
    updateChart(selectedStation, selectedDate);      // 调用主更新函数
}

// 绑定事件监听器
stationSelector.addEventListener('change', handleSelectionChange);
dateSelector.addEventListener('change', handleSelectionChange);

// --- 页面初始化 (修改) ---
function initializePage() {
    console.log("Initializing details page...");
    // 1. 设置日期选择器的默认值为 *最后一天*
    const minDate = dateSelector.min; // 获取 min 属性
    const maxDate = dateSelector.max; // 获取 max 属性 (由模板 dates[-1] 设置)

    if (dateSelector.disabled) {
        console.warn("Date selector disabled.");
    } else if (maxDate) { // 如果 max 属性存在且有值
        dateSelector.value = maxDate; // 将日期选择器的值设置为最后一天
        console.log(`Date selector default set to last available date: ${maxDate}`);
    } else if (minDate) { // 如果没有最后一天信息，但有第一天，则回退到第一天
        dateSelector.value = minDate;
        console.warn(`Could not determine last date, defaulting to first available date: ${minDate}`);
    } else {
        console.warn("Date selector has no min or max date available.");
        // 可以尝试设置成今天，或者留空，或者显示错误
        // dateSelector.value = getTodayString();
    }

    // 2. 设置下拉菜单的初始选中项
    // initiallySelectedStationId 是从 HTML 模板中获取的
    console.log("Received initial station ID from template:", initiallySelectedStationId); // 打印接收到的ID

    if (typeof initiallySelectedStationId !== 'undefined' && initiallySelectedStationId) {
        // 检查这个 ID 是否在选项中存在
        const optionExists = Array.from(stationSelector.options).some(option => option.value === initiallySelectedStationId);
        if (optionExists) {
            stationSelector.value = initiallySelectedStationId;
            console.log(`下拉菜单已设置为: ${initiallySelectedStationId}`);
            // 更新一下面包屑
             if (breadcrumbStationName && stationSelector.options.length > 0) {
                 breadcrumbStationName.textContent = stationSelector.options[stationSelector.selectedIndex].text || "电站详情";
            }
        } else {
            console.warn(`传递的电站 ID "${initiallySelectedStationId}" 在下拉菜单中未找到，将使用默认选项。`);
             // 更新面包屑为默认选项的文本
             if (breadcrumbStationName && stationSelector.options.length > 0) {
                 breadcrumbStationName.textContent = stationSelector.options[0].text || "电站详情";
            }
        }
    } else {
         console.log("未传递初始电站 ID，将使用下拉菜单的默认选项。");
          // 更新面包屑为默认选项的文本
         if (breadcrumbStationName && stationSelector.options.length > 0) {
             breadcrumbStationName.textContent = stationSelector.options[0].text || "电站详情";
         }
    }

    // 3. 加载初始图表 (使用当前选中的值)
    if (stationSelector.value && dateSelector.value) {
        console.log("加载初始图表...");
        handleSelectionChange();
    } else {
        console.warn("无法获取有效的初始站点或日期，不加载初始图表。");
        messageDiv.textContent = "请选择站点和日期以查看预测数据。";
        if (nextPointInfoDiv) nextPointInfoDiv.style.display = 'none';
    }
}

// 执行页面初始化
initializePage();

async function loadParticles() {
    await tsParticles.load("tsparticles", {
        fpsLimit: 60,
        particles: {
            // ... (粒子配置保持不变) ...
             number: { value: 100, density: { enable: true, value_area: 800 } },
            color: { value: "#cccccc" },
            shape: { type: "circle" },
            opacity: { value: 0.6, random: true, anim: { enable: true, speed: 0.8, opacity_min: 0.2, sync: false } },
            size: { value: 5, random: true, anim: { enable: false } },
            links: { enable: true, distance: 130, color: "#bbbbbb", opacity: 0.3, width: 1 },
            move: { enable: true, speed: 1.5, direction: "none", random: true, straight: false, out_mode: "out", bounce: false, attract: { enable: false } }
        },
        interactivity: {
            // --- *** 修改这里：从 "canvas" 改为 "window" *** ---
            detect_on: "window",
            // --- *** 修改结束 *** ---
            events: {
                onhover: {
                    enable: true,
                    mode: "attract" // 保持吸引模式
                },
                onclick: {
                    enable: true,
                    mode: "push"
                },
                resize: true
            },
            modes: {
                attract: {
                    distance: 250,
                    duration: 0.4,
                    speed: 1
                },
                push: { particles_nb: 4 },
                // ... (其他模式配置可以保留)
            }
        },
        detectRetina: true,
        // background: { color: "#e9ecef" }, // 可选背景色
        // fullScreen: { enable: true, zIndex: -1 } // 也可以用 fullScreen 模式
    });
    console.log("tsParticles loaded, detecting interaction on window.");
}

// 调用加载函数
loadParticles().catch(error => {
    console.error("Error loading tsParticles:", error);
});
