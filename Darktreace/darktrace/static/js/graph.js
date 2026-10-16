const canvas = document.getElementById("relationship-graph");
const summary = document.getElementById("graph-summary");
const colors = { user: "#a8e06d", community: "#70d6c7", post: "#efb965", report: "#f27969" };

async function renderRelationshipGraph() {
    if (!canvas) return;
    const response = await fetch("/api/graph", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Unable to load relationship data.");
    const graph = await response.json();
    const groups = ["user", "post", "community", "report"];
    const grouped = new Map(groups.map((kind) => [kind, graph.nodes.filter((node) => node.kind === kind)]));
    const maxNodes = Math.max(1, ...[...grouped.values()].map((items) => items.length));
    const width = 1080;
    const height = Math.max(520, 86 + maxNodes * 42);
    const scale = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = width * scale;
    canvas.height = height * scale;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const context = canvas.getContext("2d");
    context.scale(scale, scale);

    const columns = new Map(groups.map((kind, index) => [kind, 100 + index * 290]));
    const positions = new Map();
    groups.forEach((kind) => {
        const items = grouped.get(kind);
        const gap = Math.min(42, (height - 60) / Math.max(items.length, 1));
        const total = gap * items.length;
        const startY = Math.max(30, (height - total) / 2);
        items.forEach((node, index) => positions.set(node.id, { x: columns.get(kind), y: startY + index * gap + gap / 2, node }));
    });

    context.clearRect(0, 0, width, height);
    graph.edges.forEach((edge) => {
        const from = positions.get(edge.from);
        const to = positions.get(edge.to);
        if (!from || !to) return;
        context.beginPath();
        context.moveTo(from.x + 82, from.y);
        context.lineTo(to.x - 82, to.y);
        context.strokeStyle = "rgba(133, 161, 141, .26)";
        context.lineWidth = 1;
        context.stroke();
    });

    groups.forEach((kind, index) => {
        const x = columns.get(kind);
        context.fillStyle = colors[kind];
        context.font = "10px monospace";
        context.fillText(kind.toUpperCase(), x - 48, 20);
        context.fillStyle = "rgba(148, 163, 151, .12)";
        context.fillRect(x - 54, 27, 108, 1);
        context.fillStyle = colors[kind];
        context.fillRect(x - 49, 14, 5, 5);
    });

    for (const { x, y, node } of positions.values()) {
        const text = node.label.length > 19 ? `${node.label.slice(0, 17)}…` : node.label;
        context.fillStyle = "rgba(25, 35, 30, .95)";
        context.strokeStyle = colors[node.kind];
        context.lineWidth = node.risk === "Critical" || node.risk === "High" ? 1.5 : 1;
        context.beginPath();
        context.roundRect(x - 77, y - 13, 154, 26, 2);
        context.fill();
        context.stroke();
        context.fillStyle = "#e8eee8";
        context.font = "10px monospace";
        context.textAlign = "center";
        context.textBaseline = "middle";
        context.fillText(text, x, y);
    }
    context.textAlign = "start";
    summary.textContent = `${graph.nodes.filter((node) => node.kind === "user").length} users · ${graph.nodes.filter((node) => node.kind === "community").length} communities · ${graph.nodes.filter((node) => node.kind === "post").length} posts · ${graph.nodes.filter((node) => node.kind === "report").length} reports · ${graph.edges.length} links`;
}

renderRelationshipGraph().catch((error) => {
    if (summary) summary.textContent = error.message;
});