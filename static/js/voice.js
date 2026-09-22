const translations = {
  en: { overall: 'Overall feed quality is {status}.', lines: { ph: 'The pH level is {status}.', ammonia: 'The ammonia level is {status}.', protein: 'The protein level is {status}.', moisture: 'The moisture level is {status}.' }, unavailable: 'Tamil voice is not available in this browser. Please enable a Tamil voice or use a browser/device that supports Tamil speech.' },
  ta: { overall: 'மொத்த தீவன தரம் {status} நிலையில் உள்ளது.', lines: { ph: 'pH நிலை {status} நிலையில் உள்ளது.', ammonia: 'அமோனியா நிலை {status} நிலையில் உள்ளது.', protein: 'புரத அளவு {status} நிலையில் உள்ளது.', moisture: 'ஈரப்பதம் {status} நிலையில் உள்ளது.' }, unavailable: 'Tamil voice is not available in this browser. Please enable a Tamil voice or use a browser/device that supports Tamil speech.' }
};
const tamilStatus = { GOOD: 'நல்ல', MODERATE: 'மிதமான', BAD: 'மோசமான' };

function finalAnalysisSummary(results, language) {
  const ph = results.ph;
  const ammonia = results.ammonia;
  const protein = results.protein;
  const moisture = results.moisture;
  const overall = results.overall;
  const attention = ['ph', 'ammonia', 'protein', 'moisture']
    .map((key) => ({ key, item: results[key] }))
    .filter(({ item }) => item.status !== 'GOOD');
  if (language === 'ta') {
    const attentionText = attention.length
      ? `கவனம் தேவைப்படும் அளவுரு: ${attention.map(({ key, item }) => `${key === 'ph' ? 'pH' : key === 'ammonia' ? 'அமோனியா' : key === 'protein' ? 'புரதம்' : 'ஈரப்பதம்'} (${item.condition || item.problem || item.status}). பரிந்துரை: ${item.remedy || 'கிடைக்கவில்லை'}`).join(', ')}.`
      : 'கூடுதல் கவனம் தேவைப்படும் அளவுரு இல்லை.';
    return `வணக்கம். உங்கள் தீவன பரிசோதனை முடிவுகள் தயாராக உள்ளன. pH அளவு ${ph.value} ${ph.unit}; ${ph.condition || ph.problem || ph.remedy || ''}. அமோனியா அளவு ${ammonia.value} ${ammonia.unit}. புரத அளவு ${protein.value}${protein.unit}. ஈரப்பதம் ${moisture.value}${moisture.unit}; உள்ளீட்டு முறை கைமுறை. மொத்த தீவனத் தரம் ${tamilStatus[overall.status]} நிலையில் உள்ளது. ${attentionText} நன்றி.`;
  }
  const attentionText = attention.length
    ? `Parameters requiring attention: ${attention.map(({ key, item }) => `${key === 'ph' ? 'pH' : key} (${item.condition || item.problem || item.status}). Recommendation: ${item.remedy || 'Unavailable'}`).join('; ')}.`
    : 'No parameter requires additional attention.';
  return `Feed analysis is completed. The measured pH is ${ph.value} ${ph.unit}, which indicates ${ph.condition || ph.problem || ph.remedy || 'the configured reference result'}. Ammonia was measured at ${ammonia.value} ${ammonia.unit}, protein was measured at ${protein.value}${protein.unit}, and moisture was recorded at ${moisture.value}${moisture.unit} from manual input. Based on the analyzed parameters, the overall feed quality is ${overall.status}. ${attentionText}`;
}

function resultSummary(results, language) {
  const dictionary = translations[language];
  const status = language === 'ta' ? tamilStatus[results.overall.status] : results.overall.status.toLowerCase();
  return [dictionary.overall.replace('{status}', status), ...['ph', 'ammonia', 'protein', 'moisture'].map((key) => dictionary.lines[key].replace('{status}', language === 'ta' ? tamilStatus[results[key].status] : results[key].status.toLowerCase()))].join(' ');
}

function speakResults(results, language, feedback) {
  if (!window.speechSynthesis) { feedback.textContent = 'Speech synthesis is not supported in this browser.'; return; }
  const voices = window.speechSynthesis.getVoices();
  const tamil = voices.find((voice) => /^ta(-|$)/i.test(voice.lang));
  const english = voices.find((voice) => /^en(-|$)/i.test(voice.lang));
  if (language === 'ta' && !tamil) { window.speechSynthesis.cancel(); feedback.textContent = translations.ta.unavailable; return; }
  if (language === 'en' && !english) { feedback.textContent = 'English voice is not available in this browser.'; return; }
  const utterance = new SpeechSynthesisUtterance(`${resultSummary(results, language)} ${finalAnalysisSummary(results, language)}`);
  utterance.lang = language === 'ta' ? tamil.lang : english.lang;
  utterance.voice = language === 'ta' ? tamil : english;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
  feedback.textContent = '';
}
