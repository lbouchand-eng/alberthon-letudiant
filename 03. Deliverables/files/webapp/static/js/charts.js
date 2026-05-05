/* Baromètre charts — adaptés depuis barometer_dashboard.html.
   Appelé par portal/barometre.html après chargement de /data/barometer.json. */
(function () {
  const RED = '#E8242C', BLUE = '#2563eb', GREEN = '#059669', ORANGE = '#d97706';
  let chartDomaines, chartConv, chartCRM, chartSalons, chartCSP, chartLeadDist;
  let RAW;

  async function init() {
    try {
      const res = await fetch('/data/barometer.json?t=' + Date.now());
      RAW = await res.json();
    } catch (err) {
      document.getElementById('charts-root').innerHTML =
        `<div class="alert-warn">❌ Impossible de charger les données : ${err.message}</div>`;
      return;
    }
    buildCharts(RAW);
    renderSalonTable(RAW.salons_table);

    const niveau = document.getElementById('filterNiveau');
    const csp    = document.getElementById('filterCSP');
    const ville  = document.getElementById('filterVille');
    [niveau, csp, ville].forEach(el => el && el.addEventListener('change', applyFilters));
  }

  function buildCharts(D) {
    chartDomaines = new Chart(document.getElementById('chartDomaines'), {
      type: 'bar',
      data: {
        labels: D.domaines.labels,
        datasets: [{
          label: 'Inscrits', data: D.domaines.values,
          backgroundColor: D.domaines.values.map((_, i) => i === 0 ? RED : '#e5e7eb'),
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { callback: v => (v / 1000).toFixed(0) + 'k' }, grid: { color: '#f3f4f6' } },
          y: { ticks: { font: { size: 11 } } }
        }
      }
    });

    chartConv = new Chart(document.getElementById('chartConv'), {
      type: 'line',
      data: {
        labels: D.conversations.labels,
        datasets: [{
          label: 'Conversations', data: D.conversations.values,
          borderColor: RED, backgroundColor: 'rgba(232,36,44,0.08)',
          borderWidth: 2.5, pointRadius: 4, pointBackgroundColor: RED,
          fill: true, tension: 0.3
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { ticks: { callback: v => v.toLocaleString('fr') }, grid: { color: '#f3f4f6' } },
          x: { grid: { display: false } }
        }
      }
    });

    chartCRM = new Chart(document.getElementById('chartCRM'), {
      type: 'bar',
      data: {
        labels: D.crm.labels,
        datasets: [
          { label: "Taux d'ouverture (%)", data: D.crm.ouverture, backgroundColor: BLUE,   borderRadius: 4, yAxisID: 'y' },
          { label: "Taux de clic (%)",     data: D.crm.clic,      backgroundColor: ORANGE, borderRadius: 4, yAxisID: 'y2' },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
        scales: {
          y:  { title: { display: true, text: 'Ouverture (%)', font: { size: 10 } }, grid: { color: '#f3f4f6' } },
          y2: { title: { display: true, text: 'Clic (%)',      font: { size: 10 } }, position: 'right', grid: { display: false } },
          x:  { grid: { display: false } }
        }
      }
    });

    chartSalons = new Chart(document.getElementById('chartSalons'), {
      type: 'bar',
      data: {
        labels: D.salons.labels,
        datasets: [
          { label: 'Inscrits', data: D.salons.inscrits, backgroundColor: '#e5e7eb', borderRadius: 4 },
          { label: 'Venus',    data: D.salons.venus,    backgroundColor: GREEN,     borderRadius: 4 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: { font: { size: 11 } } } },
        scales: {
          y: { ticks: { callback: v => (v / 1000).toFixed(0) + 'k' }, grid: { color: '#f3f4f6' } },
          x: { grid: { display: false } }
        }
      }
    });

    chartCSP = new Chart(document.getElementById('chartCSP'), {
      type: 'bar',
      data: {
        labels: D.csp.labels,
        datasets: [
          { label: 'CSP+', data: D.csp.cspPlus,  backgroundColor: GREEN, borderRadius: 2 },
          { label: 'CSP−', data: D.csp.cspMoins, backgroundColor: RED,   borderRadius: 2 },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { font: { size: 11 } } },
          tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.raw.toLocaleString('fr')}` } }
        },
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, ticks: { callback: v => (v / 1000).toFixed(0) + 'k' }, grid: { color: '#f3f4f6' } }
        }
      }
    });

    chartLeadDist = new Chart(document.getElementById('chartLeadDist'), {
      type: 'doughnut',
      data: {
        labels: D.lead_distribution.labels,
        datasets: [{
          data: D.lead_distribution.values,
          backgroundColor: [RED, ORANGE, '#9ca3af'], borderWidth: 0
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { font: { size: 12 } } },
          tooltip: {
            callbacks: {
              label: ctx => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const pct = (ctx.raw / total * 100).toFixed(1);
                return `${ctx.label}: ${ctx.raw.toLocaleString('fr')} (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }

  function renderSalonTable(data) {
    const tbody = document.getElementById('salonTableBody');
    if (!tbody) return;
    if (!data || !data.length) { tbody.innerHTML = ''; return; }
    const maxInscrits = Math.max(...data.map(r => r.inscrits));
    tbody.innerHTML = data.map(r => `
      <tr>
        <td><strong>${r.ville}</strong></td>
        <td>${r.inscrits.toLocaleString('fr')}</td>
        <td>${r.venus.toLocaleString('fr')}</td>
        <td><strong style="color:${r.taux >= 70 ? '#059669' : r.taux >= 50 ? '#d97706' : '#ef4444'}">${r.taux}%</strong></td>
        <td style="width:200px"><div class="bar-cell">
          <div class="bar-bg"><div class="bar-fill" style="width:${(r.venus / maxInscrits * 100).toFixed(0)}%"></div></div>
        </div></td>
      </tr>`).join('');
  }

  function applyFilters() {
    const niveau = document.getElementById('filterNiveau').value;
    const csp    = document.getElementById('filterCSP').value;
    const ville  = document.getElementById('filterVille').value;

    if (niveau !== 'all') {
      const idx = RAW.crm.labels.findIndex(l => l.includes(niveau));
      chartCRM.data.datasets[0].backgroundColor = RAW.crm.labels.map((_, i) => i === idx ? BLUE   : '#d1d5db');
      chartCRM.data.datasets[1].backgroundColor = RAW.crm.labels.map((_, i) => i === idx ? ORANGE : '#e5e7eb');
    } else {
      chartCRM.data.datasets[0].backgroundColor = BLUE;
      chartCRM.data.datasets[1].backgroundColor = ORANGE;
    }
    chartCRM.update();

    if (ville !== 'all') {
      const filtered = RAW.salons_table.filter(r => r.ville.includes(ville));
      renderSalonTable(filtered.length ? filtered : RAW.salons_table);
      chartSalons.data.datasets[1].backgroundColor = RAW.salons.labels.map(
        l => l.toUpperCase() === ville ? GREEN : '#9ca3af'
      );
    } else {
      renderSalonTable(RAW.salons_table);
      chartSalons.data.datasets[1].backgroundColor = GREEN;
    }
    chartSalons.update();

    if (csp === 'CSP+') {
      chartCSP.data.datasets[0].hidden = false;
      chartCSP.data.datasets[1].hidden = true;
    } else if (csp === 'CSP-') {
      chartCSP.data.datasets[0].hidden = true;
      chartCSP.data.datasets[1].hidden = false;
    } else {
      chartCSP.data.datasets.forEach(ds => ds.hidden = false);
    }
    chartCSP.update();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
