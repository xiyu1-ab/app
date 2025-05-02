// static/js/main_index.js

// --- tsParticles 初始化 ---
async function loadParticles() {
    await tsParticles.load("page-body", { // 目标是 body
        fpsLimit: 60,
        particles: {
            number: { value: 60, density: { enable: true, value_area: 700 } }, // 减少点数量
            color: { value: "#aaaaaa" },
            shape: { type: "circle" },
            opacity: { value: 0.5, random: true, anim: { enable: true, speed: 0.8, opacity_min: 0.15, sync: false } },
            size: { value: 2, random: true }, // 减小点大小
            links: { enable: true, distance: 120, color: "#bbbbbb", opacity: 0.3, width: 1 },
            move: { enable: true, speed: 1.2, direction: "none", random: true, straight: false, out_mode: "out", bounce: false, attract: { enable: false } }
        },
        interactivity: {
            detect_on: "canvas", // 交互只在空白区域有效
            events: {
                onhover: { enable: true, mode: "attract" },
                onclick: { enable: true, mode: "push" },
                resize: true
            },
            modes: {
                attract: { distance: 140, duration: 0.4, speed: 0.8 }, // 调整吸引参数
                push: { particles_nb: 3 }, // 减少推出数量
                // ... 其他模式可以移除或保留
            }
        },
        detectRetina: true,
    });
    console.log("Index page tsParticles loaded onto body.");
}

// 调用加载函数
loadParticles().catch(error => {
    console.error("Error loading index page tsParticles:", error);
});

// 未来可以在这里添加一级页面的其他交互逻辑