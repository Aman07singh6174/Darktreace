const palette = {
    ink: "#aab9ae",
    grid: "rgba(148, 166, 153, .12)",
    green: "#a8e06d",
    cyan: "#70d6c7",
    amber: "#efb965",
    orange: "#ef8e60",
    red: "#f27969",
    panel: "#171f1c",
};

const riskColors = [palette.cyan, palette.amber, palette.orange, palette.red];

async function loadDashboardCharts() {
    if (!window.Chart) throw new Error("Local Chart.js asset did not load.");
    const response = await fetch("/api/overview", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Could not load local dashboard data.");
    const data = await response.json();
    const commonScale = {
        x: { grid: { color: palette.grid }, ticks: { color: palette.ink, font: { family: "monospace", size: 9 } } },
        y: { beginAtZero: true, grid: { color: palette.grid }, ticks: { color: palette.ink, font: { family: "monospace", size: 9 } } },
    };

    new Chart(document.getElementById("activity-chart"), {
        type: "line",
        data: { labels: data.activity.map((item) => item.day), datasets: [{ label: "Security events", data: data.activity.map((item) => item.count), borderColor: palette.green, backgroundColor: "rgba(168,224,109,.12)", fill: true, tension: 0.32, pointRadius: 2, pointBackgroundColor: palette.green }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: commonScale },
    });

    new Chart(document.getElementById("risk-chart"), {
        type: "doughnut",
        data: { labels: data.risk.map((item) => item.level), datasets: [{ data: data.risk.map((item) => item.count), backgroundColor: riskColors, borderColor: palette.panel, borderWidth: 3, hoverOffset: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: "66%", plugins: { legend: { position: "right", labels: { color: palette.ink, usePointStyle: true, pointStyle: "circle", boxWidth: 7, padding: 11, font: { family: "monospace", size: 9 } } } } },
    });

    new Chart(document.getElementById("user-chart"), {
        type: "bar",
        data: { labels: data.users.map((item) => item.name), datasets: [{ label: "Risk score", data: data.users.map((item) => item.score), backgroundColor: data.users.map((item) => item.score >= 80 ? palette.red : item.score >= 60 ? palette.orange : item.score >= 30 ? palette.amber : palette.cyan), borderRadius: 2, barThickness: 12 }] },
        options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ...commonScale.x, max: 100 }, y: { ...commonScale.y, grid: { display: false } } } },
    });

    new Chart(document.getElementById("threat-chart"), {
        type: "bar",
        data: { labels: data.threats.map((item) => item.type), datasets: [{ label: "Reports", data: data.threats.map((item) => item.count), backgroundColor: [palette.cyan, palette.green, palette.amber, palette.orange, palette.red], borderRadius: 2, barThickness: 13 }] },
        options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ...commonScale.x, ticks: { ...commonScale.x.ticks, precision: 0 } }, y: { ...commonScale.y, grid: { display: false }, ticks: { ...commonScale.y.ticks, autoSkip: false } } } },
    });
}

loadDashboardCharts().catch((error) => {
    document.querySelectorAll(".chart-wrap").forEach((container) => {
        container.setAttribute("aria-label", `Chart unavailable: ${error.message}`);
    });
});