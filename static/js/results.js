const payload = JSON.parse(sessionStorage.getItem('feedsenseResults') || 'null');
const grid = document.querySelector('#result-grid');
const overall = document.querySelector('#overall');
const language = document.querySelector('#language');
const voiceMessage = document.querySelector('#voice-message');
const summaryEnglish = document.querySelector('#summary-en');
const summaryTamil = document.querySelector('#summary-ta');
const analysisGraph = document.querySelector('#analysis-graph');
const labels = { en: { ph: 'pH', ammonia: 'Ammonia', protein: 'Protein', moisture: 'Moisture', condition: 'Condition', problem: 'Problem', remedy: 'Remedy', manual: 'Input Method: Manual' }, ta: { ph: 'pH', ammonia: 'அமோனியா', protein: 'புரதம்', moisture: 'ஈரப்பதம்', condition: 'நிலை', problem: 'பிரச்சினை', remedy: 'தீர்வு', manual: 'உள்ளீட்டு முறை: கைமுறை' } };

function renderAnalysisGraph(results) {
  const context = analysisGraph.getContext('2d');
  const entries = ['ph', 'ammonia', 'protein', 'moisture'].map((key) => ({ key, ...results[key] }));
  const width = Math.max(analysisGraph.clientWidth, 320);
  const height = 280;
  const scale = window.devicePixelRatio || 1;
  analysisGraph.width = width * scale;
  analysisGraph.height = height * scale;
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, height);
  context.font = '14px Verdana, sans-serif';
  context.textBaseline = 'middle';
  const colors = { GOOD: '#238b58', MODERATE: '#c58b16', BAD: '#b5483e' };
  const names = { ph: 'pH', ammonia: 'Ammonia', protein: 'Protein', moisture: 'Moisture' };
  const maxValue = Math.max(...entries.map((entry) => Math.abs(Number(entry.value))), 1);
  const labelWidth = 95;
  const valueWidth = 100;
  const chartWidth = Math.max(width - labelWidth - valueWidth - 24, 80);
  entries.forEach((entry, index) => {
    const y = 34 + index * 58;
    const barWidth = chartWidth * Math.abs(Number(entry.value)) / maxValue;
    context.fillStyle = '#173042';
    context.fillText(names[entry.key], 8, y);
    context.fillStyle = '#e3e8e3';
    context.fillRect(labelWidth, y - 12, chartWidth, 24);
    context.fillStyle = colors[entry.status] || '#087e8b';
    context.fillRect(labelWidth, y - 12, barWidth, 24);
    context.fillStyle = '#173042';
    context.fillText(`${entry.value} ${entry.unit} · ${entry.status}`, labelWidth + chartWidth + 12, y);
  });
  analysisGraph.setAttribute('aria-label', entries.map((entry) => `${names[entry.key]} ${entry.value} ${entry.unit}, ${entry.status}`).join('; '));
}

function renderResults() {
  if (!payload) return;
  const dictionary = labels[language.value];
  overall.className = `overall status-${payload.results.overall.status.toLowerCase()}`;
  overall.textContent = `${payload.results.overall.status} · ${payload.results.overall.reason}`;
  grid.innerHTML = ['ph', 'ammonia', 'protein', 'moisture'].map((key) => {
    const item = payload.results[key];
    return `<article class="result-card status-${item.status.toLowerCase()}"><h2>${dictionary[key]}</h2><strong class="value">${item.value} ${item.unit}</strong><span class="status-pill">${item.status}</span><dl><dt>${dictionary.condition}</dt><dd>${item.condition || 'Reference data unavailable'}</dd><dt>${dictionary.problem}</dt><dd>${item.problem || 'Reference data unavailable'}</dd><dt>${dictionary.remedy}</dt><dd>${item.remedy || 'Reference data unavailable'}</dd></dl>${item.input_method ? `<p class="input-note">${dictionary.manual}</p>` : ''}</article>`;
  }).join('');
  renderAnalysisGraph(payload.results);
  summaryEnglish.textContent = finalAnalysisSummary(payload.results, 'en');
  summaryTamil.textContent = finalAnalysisSummary(payload.results, 'ta');
}

language.addEventListener('change', renderResults);
document.querySelector('#read-result').addEventListener('click', () => {
  if (payload) speakResults(payload.results, language.value, voiceMessage);
});
document.querySelector('#download-report').addEventListener('click', async () => {
  if (!payload) return;
  const response = await fetch('/api/report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ results: payload.results, language: language.value }) });
  if (!response.ok) { voiceMessage.textContent = 'PDF report could not be generated.'; return; }
  const blob = await response.blob();
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'feedsense-report.pdf'; link.click(); URL.revokeObjectURL(link.href);
});

if (window.speechSynthesis) window.speechSynthesis.addEventListener('voiceschanged', () => {});
renderResults();
window.addEventListener('resize', () => { if (payload) renderAnalysisGraph(payload.results); });
