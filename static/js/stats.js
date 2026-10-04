// Stats dashboard chart (stats/stats.html)
(function () {
  const dataEl = document.getElementById("chart-data");
  const canvas = document.getElementById("statsChart");
  if (!dataEl || !canvas || typeof Chart === "undefined") return;

  const data = JSON.parse(dataEl.textContent);
  const line = (label, values, color) => ({
    label: label,
    data: values,
    borderColor: color,
    backgroundColor: color + "22",
    fill: true,
    tension: 0.3,
    pointRadius: 2,
  });

  new Chart(canvas, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [
        line("Views", data.views, "#667eea"),
        line("Reads", data.reads, "#2193b0"),
        line("Likes", data.likes, "#e11d48"),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
})();

// Period selector: reload the page when the value changes
document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
  select.addEventListener("change", function () { select.form.submit(); });
});
