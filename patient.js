(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const prettySize = bytes => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  let dependents = [], selectedFile = null, toastTimer;

  async function api(url, options = {}) {
    let response;
    try { response = await fetch(url, {cache: 'no-store', ...options}); }
    catch { throw new Error('Não foi possível acessar o servidor local.'); }
    const type = response.headers.get('content-type') || '';
    const body = type.includes('application/json') ? await response.json() : null;
    if (!response.ok) throw new Error(body?.error || `A operação falhou (${response.status}).`);
    return body;
  }
  function toast(message, error = false) { const el = $('#toast'); el.textContent = message; el.classList.toggle('error', error); el.classList.remove('hidden'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.add('hidden'), 4200); }
  function renderDependents() {
    const select = $('#dependent-select'), oldValue = select.value;
    select.innerHTML = `<option value="">${dependents.length ? 'Selecione uma pessoa' : 'Cadastre uma pessoa primeiro'}</option>` + dependents.map(person => `<option value="${esc(person.id)}">${esc(person.name)}</option>`).join('');
    if (dependents.some(person => person.id === oldValue)) select.value = oldValue;
    $('#dependent-list').innerHTML = dependents.length ? dependents.map(person => `<div class="dependent-row"><span class="dependent-avatar">${esc(person.name.trim().charAt(0).toUpperCase())}</span><div class="dependent-copy"><strong>${esc(person.name)}</strong><small>${person.document_count} envio${person.document_count === 1 ? '' : 's'} associado${person.document_count === 1 ? '' : 's'}</small></div></div>`).join('') : '<p class="muted small">Nenhuma pessoa cadastrada ainda.</p>';
  }
  async function loadDependents() { dependents = (await api('/api/dependents')).items || []; renderDependents(); }
  function showUploadError(message) { $('#upload-error').textContent = message; $('#upload-error').classList.remove('hidden'); }
  function setSelected(file) {
    selectedFile = null; $('#selected-file').classList.add('hidden'); $('#selected-file').innerHTML = ''; $('#dropzone').classList.remove('hidden'); $('#upload-error').classList.add('hidden');
    if (!file) return;
    if (!['image/jpeg','image/png','image/webp','application/pdf'].includes(file.type)) return showUploadError('Selecione JPG, PNG, WEBP ou PDF.');
    if (!file.size || file.size > 10 * 1024 * 1024) return showUploadError('O arquivo deve ter até 10 MB.');
    selectedFile = file; $('#dropzone').classList.add('hidden'); const target = $('#selected-file');
    target.innerHTML = `<span class="file-icon">${file.type === 'application/pdf' ? 'PDF' : 'IMG'}</span><strong>${esc(file.name)}</strong><small>${prettySize(file.size)}</small><button type="button" id="remove-file" class="remove-file" aria-label="Remover arquivo">×</button>`; target.classList.remove('hidden');
    $('#remove-file').addEventListener('click', () => { $('#file-input').value = ''; setSelected(null); });
  }
  $('#dependent-form').addEventListener('submit', async event => { event.preventDefault(); const input = $('#dependent-name'), name = input.value.trim(); if (!name) return input.focus(); try { await api('/api/dependents', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name})}); input.value = ''; await loadDependents(); toast('Pessoa cadastrada.'); } catch (error) { toast(error.message, true); } });
  $('#upload-form').addEventListener('submit', async event => { event.preventDefault(); const dependentId = $('#dependent-select').value; if (!dependentId) return showUploadError('Cadastre e selecione uma pessoa.'); if (!$('#vaccine').value) return showUploadError('Selecione a vacina ou o registro.'); if (!selectedFile) return showUploadError('Escolha um arquivo antes de enviar.'); const form = new FormData(); form.set('dependentId', dependentId); form.set('vaccine', $('#vaccine').value); form.set('doseDate', $('#dose-date').value); form.set('note', $('#family-note').value.trim()); form.set('file', selectedFile, selectedFile.name); const submit = $('#upload-form button[type=submit]'); submit.disabled = true; submit.textContent = 'Enviando…'; try { await api('/api/documents', {method:'POST', body:form}); $('#upload-form').reset(); setSelected(null); await loadDependents(); toast('Caderneta enviada. A equipe fará a análise.'); } catch (error) { showUploadError(error.message); } finally { submit.disabled = false; submit.innerHTML = 'Enviar para análise <span>→</span>'; } });
  $('#browse-file').addEventListener('click', () => $('#file-input').click()); $('#file-input').addEventListener('change', event => setSelected(event.target.files[0])); const zone = $('#dropzone'); zone.addEventListener('click', event => { if (!event.target.closest('.link-button')) $('#file-input').click(); }); zone.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); $('#file-input').click(); } }); zone.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('dragging'); }); zone.addEventListener('dragleave', () => zone.classList.remove('dragging')); zone.addEventListener('drop', event => { event.preventDefault(); zone.classList.remove('dragging'); setSelected(event.dataTransfer.files[0]); });
  loadDependents().catch(error => toast(error.message, true));
})();
