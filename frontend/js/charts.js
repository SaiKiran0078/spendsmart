// Thin wrapper around Chart.js (loaded from a CDN as window.Chart) that follows the theme.
import { CATEGORY_COLORS, money } from "./ui.js";

const live = new Set();
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export function destroyCharts() {
  for (const chart of live) chart.destroy();
  live.clear();
}

function make(canvas, config) {
  if (typeof window.Chart === "undefined") {
    canvas.replaceWith(Object.assign(document.createElement("p"), { className: "muted small", textContent: "Charts are unavailable offline." }));
    return null;
  }
  window.Chart.defaults.font.family = css("--font");
  window.Chart.defaults.color = css("--muted");
  const chart = new window.Chart(canvas, config);
  live.add(chart);
  return chart;
}

export function categoryDoughnut(canvas, items) {
  return make(canvas, {
    type: "doughnut",
    data: {
      labels: items.map((i) => i.category),
      datasets: [{ data: items.map((i) => i.total), backgroundColor: items.map((i) => CATEGORY_COLORS[i.category] || "#94a3b8"), borderColor: css("--surface"), borderWidth: 3 }],
    },
    options: {
      maintainAspectRatio: false, cutout: "66%",
      plugins: { legend: { position: "right", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${money(ctx.parsed)}` } } },
    },
  });
}

export function trendBars(canvas, points, labelFor) {
  return make(canvas, {
    type: "bar",
    data: {
      labels: points.map(labelFor),
      datasets: [
        { label: "Income", data: points.map((p) => p.income), backgroundColor: css("--accent"), borderRadius: 6 },
        { label: "Expenses", data: points.map((p) => p.expenses), backgroundColor: css("--info"), borderRadius: 6 },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${money(ctx.parsed.y)}` } } },
      scales: { x: { grid: { display: false } }, y: { grid: { color: css("--border") }, ticks: { callback: (v) => money(v, { compact: true }) } } },
    },
  });
}

export function dailyLine(canvas, days) {
  return make(canvas, {
    type: "line",
    data: {
      labels: days.map((d) => Number(d.date.slice(8))),
      datasets: [{ label: "Spent", data: days.map((d) => d.total), borderColor: css("--accent"), backgroundColor: `${css("--accent")}33`, fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { title: (items) => `Day ${items[0].label}`, label: (ctx) => ` ${money(ctx.parsed.y)}` } } },
      scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: css("--border") }, ticks: { callback: (v) => money(v, { compact: true }) } } },
    },
  });
}
