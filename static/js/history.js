async function loadHistory() {
  const records = await (await fetch('/api/history')).json();
  const history = document.querySelector('#history-content');
  const dashboard = document.querySelector('#dashboard-content');
  if (!records.length) {
    const empty = '<p class="empty">No analysis history available yet.</p>';
    if (history) history.innerHTML = empty;
    if (dashboard) dashboard.innerHTML = empty;
    return;
  }
  if (history) history.innerHTML = records.slice().reverse().map((record) => `<article class="history-row"><time>${new Date(record.created_at).toLocaleString()}</time><span>pH ${record.ph.value}</span><span>NH₃ ${record.ammonia.value} ppm</span><span>Protein ${record.protein.value}%</span><span>Moisture ${record.moisture.value}%</span><strong>${record.overall.status}</strong></article>`).join('');
  if (dashboard) {
    const counts = records.reduce((summary, record) => { summary[record.overall.status] += 1; return summary; }, { GOOD: 0, MODERATE: 0, BAD: 0 });
    dashboard.innerHTML = `<article><strong>${records.length}</strong><p>Total completed scans</p></article><article><strong>${counts.GOOD}</strong><p>GOOD overall results</p></article><article><strong>${counts.MODERATE}</strong><p>MODERATE overall results</p></article><article><strong>${counts.BAD}</strong><p>BAD overall results</p></article>`;
  }
}
loadHistory();
