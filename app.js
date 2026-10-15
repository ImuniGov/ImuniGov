(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const prettySize = bytes => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  const prettyDate = (value, time = false) => value ? new Intl.DateTimeFormat('pt-BR', time ? {dateStyle:'short',timeStyle:'short'} : {dateStyle:'short'}).format(new Date(value)) : '—';
  const states = {pendente:['Aguardando análise','pendente'],aprovado:['Aprovado','aprovado'],rejeitado:['Devolvido para ajuste','rejeitado']};
  let documents = [];
  let dependents = [];
  let filter = 'todos';
  let query = '';
  let current = null;
  let currentDecision = '';
  let selectedFile = null;
  let toastTimer;

  async function api(url, options = {}) {
    let response;
    try { response = await fetch(url, {cache:'no-store', ...options}); }
    catch { throw new Error('Não foi possível acessar o servidor. Inicie a aplicação pelo arquivo INICIAR_IMUNIGUIA.bat.'); }
    const type = response.headers.get('content-type') || '';
    const body = type.includes('application/json') ? await response.json() : null;
    if (!response.ok) throw new Error(body?.error || `A operação falhou (${response.status}).`);
    return body;
  }

  function toast(message, error = false) {
    const el = $('#toast'); el.textContent = message; el.classList.toggle('error', error); el.classList.remove('hidden');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.add('hidden'), 4200);
  }
  function statusChip(status) {
    const [label, cls] = states[status] || states.pendente;
    return `<span class="status-chip status-${cls}"><i class="status-dot"></i>${label}</span>`;
  }
  function fileTypeLabel(type) { return type === 'application/pdf' ? 'PDF' : 'IMG'; }

  async function loadAll() {
    const [docs, people] = await Promise.all([api('/api/documents'), api('/api/dependents')]);
    documents = docs.items || [];
    dependents = people.items || [];
    renderStats(); renderDependents(); renderDocuments();
  }

  function renderStats() {
    const counts = documents.reduce((out, doc) => { out[doc.status] = (out[doc.status] || 0) + 1; return out; }, {});
    $('#count-pendente').textContent = counts.pendente || 0;
    $('#count-aprovado').textContent = counts.aprovado || 0;
    $('#count-rejeitado').textContent = counts.rejeitado || 0;
    $('#count-total').textContent = documents.length;
    $('#pending-count').textContent = counts.pendente || 0;
    $('#all-count').textContent = documents.length;
  }

  function renderDependents() {
    const select = $('#dependent-select');
    const previous = select.value;
    select.innerHTML = `<option value="">${dependents.length ? 'Selecione um dependente' : 'Cadastre um dependente primeiro'}</option>` + dependents.map(person => `<option value="${esc(person.id)}">${esc(person.name)}</option>`).join('');
    if (dependents.some(person => person.id === previous)) select.value = previous;
    const list = $('#dependent-list');
    if (!dependents.length) {
      list.innerHTML = '<p class="muted small">Nenhum dependente cadastrado ainda.</p>';
      return;
    }
    list.innerHTML = dependents.map(person => `<div class="dependent-row"><span class="dependent-avatar">${esc(person.name.trim().charAt(0).toUpperCase())}</span><div class="dependent-copy"><strong>${esc(person.name)}</strong><small>${person.document_count} documento${person.document_count === 1 ? '' : 's'} associado${person.document_count === 1 ? '' : 's'}</small></div><button class="delete-dependent" data-delete-dependent="${esc(person.id)}" title="Remover dependente" aria-label="Remover ${esc(person.name)}">×</button></div>`).join('');
  }

  function renderDocuments() {
    const rows = $('#document-rows');
    const filtered = documents.filter(doc => (filter === 'todos' || doc.status === filter) && `${doc.fileName} ${doc.dependent} ${doc.vaccine}`.toLocaleLowerCase('pt-BR').includes(query.toLocaleLowerCase('pt-BR')));
    $('#empty').classList.toggle('hidden', filtered.length !== 0);
    rows.innerHTML = filtered.map(doc => `<tr><td><div class="file-cell"><span class="file-icon">${fileTypeLabel(doc.contentType)}</span><div class="file-copy"><strong title="${esc(doc.fileName)}">${esc(doc.fileName)}</strong><small>${prettySize(doc.size)} · ${prettyDate(doc.createdAt,true)}</small></div></div></td><td>${esc(doc.dependent)}</td><td>${esc(doc.vaccine)}${doc.doseDate ? `<br><small>${prettyDate(`${doc.doseDate}T12:00:00`)}</small>` : ''}</td><td>${prettyDate(doc.createdAt)}</td><td>${statusChip(doc.status)}</td><td><button class="table-action" data-open="${esc(doc.id)}">${doc.status === 'pendente' ? 'Conferir' : 'Detalhes'}</button></td></tr>`).join('');
  }

  function setSelected(file) {
    selectedFile = null;
    $('#selected-file').classList.add('hidden');
    $('#selected-file').innerHTML = '';
    $('#dropzone').classList.remove('hidden');
    $('#upload-error').classList.add('hidden');
    if (!file) return;
    const allowed = ['image/jpeg','image/png','image/webp','application/pdf'];
    if (!allowed.includes(file.type)) { $('#file-input').value = ''; return uploadError('Selecione um arquivo JPG, PNG, WEBP ou PDF válido.'); }
    if (file.size > 10 * 1024 * 1024) { $('#file-input').value = ''; return uploadError('O arquivo ultrapassa o limite de 10 MB.'); }
    if (!file.size) { $('#file-input').value = ''; return uploadError('O arquivo está vazio.'); }
    selectedFile = file;
    $('#dropzone').classList.add('hidden');
    const target = $('#selected-file');
    target.innerHTML = `<span class="file-icon">${fileTypeLabel(file.type)}</span><strong>${esc(file.name)}</strong><small>${prettySize(file.size)}</small><button type="button" id="remove-file" class="remove-file" aria-label="Remover arquivo">×</button>`;
    target.classList.remove('hidden');
    $('#remove-file').addEventListener('click', () => { $('#file-input').value = ''; setSelected(null); });
  }
  function uploadError(message) { $('#upload-error').textContent = message; $('#upload-error').classList.remove('hidden'); }

  async function createDependent(event) {
    event.preventDefault();
    const input = $('#dependent-name');
    const name = input.value.trim();
    if (!name) return input.focus();
    try {
      await api('/api/dependents', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
      input.value = '';
      await loadAll();
      toast('Dependente cadastrado.');
    } catch (error) { toast(error.message, true); }
  }

  async function removeDependent(dependentId) {
    if (!window.confirm('Remover este dependente?')) return;
    try { await api(`/api/dependents/${encodeURIComponent(dependentId)}`, {method:'DELETE'}); await loadAll(); toast('Dependente removido.'); }
    catch (error) { toast(error.message, true); }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    const dependentId = $('#dependent-select').value;
    if (!dependentId) return uploadError('Cadastre e selecione um dependente.');
    if (!$('#vaccine').value) return uploadError('Selecione a vacina ou o registro.');
    if (!selectedFile) return uploadError('Escolha um arquivo antes de enviar.');
    const form = new FormData();
    form.set('dependentId', dependentId);
    form.set('vaccine', $('#vaccine').value);
    form.set('doseDate', $('#dose-date').value);
    form.set('note', $('#family-note').value.trim());
    form.set('file', selectedFile, selectedFile.name);
    const submit = $('#upload-form button[type=submit]');
    submit.disabled = true; submit.textContent = 'Enviando…';
    try {
      await api('/api/documents', {method:'POST',body:form});
      $('#upload-form').reset(); setSelected(null); await loadAll();
      document.querySelector('#documentos').scrollIntoView({behavior:'smooth'});
      toast('Arquivo enviado e salvo no servidor. Status: aguardando análise.');
    } catch (error) { uploadError(error.message); }
    finally { submit.disabled = false; submit.innerHTML = 'Enviar para análise <span>→</span>'; }
  }

  function openReview(documentId) {
    current = documents.find(doc => doc.id === documentId);
    if (!current) return;
    currentDecision = '';
    $('#review-title').textContent = current.status === 'pendente' ? 'Conferir arquivo' : 'Detalhes do documento';
    const fileUrl = `/api/documents/${encodeURIComponent(current.id)}/file`;
    const preview = current.contentType === 'application/pdf'
      ? `<iframe class="review-preview pdf" src="${fileUrl}" title="Arquivo PDF enviado"></iframe>`
      : `<img class="review-preview" src="${fileUrl}" alt="Imagem da caderneta enviada">`;
    $('#review-details').innerHTML = `${preview}<div class="review-meta"><div class="meta-box"><small>Dependente</small><strong>${esc(current.dependent)}</strong></div><div class="meta-box"><small>Vacina ou registro</small><strong>${esc(current.vaccine)}${current.doseDate ? ` · ${prettyDate(`${current.doseDate}T12:00:00`)}` : ''}</strong></div><div class="meta-box"><small>Arquivo</small><strong>${esc(current.fileName)} · ${prettySize(current.size)}</strong></div><div class="meta-box"><small>Recebido em</small><strong>${prettyDate(current.createdAt,true)}</strong></div>${current.familyNote ? `<div class="meta-box wide"><small>Observação do envio</small><strong>${esc(current.familyNote)}</strong></div>` : ''}${current.status !== 'pendente' ? `<div class="meta-box wide"><small>Decisão</small><strong>${statusChip(current.status)} · ${prettyDate(current.reviewedAt,true)}</strong></div><div class="meta-box"><small>Revisor informado</small><strong>${esc(current.reviewer)}</strong></div>${current.reviewNote ? `<div class="meta-box"><small>Orientação</small><strong>${esc(current.reviewNote)}</strong></div>` : ''}` : ''}</div>`;
    const pending = current.status === 'pendente';
    $('#decision-fields').classList.toggle('hidden', !pending);
    $('#read-only-actions').classList.toggle('hidden', pending);
    $('#reject-note-wrap').classList.add('hidden');
    $('#review-note').value = '';
    $('#reviewer').value = '';
    $('#decision-error').classList.add('hidden');
    $('#reject-button').classList.remove('hidden');
    $('#approve-button').classList.remove('hidden');
    $('#review-dialog').showModal();
  }

  async function submitDecision(decision) {
    const reviewer = $('#reviewer').value.trim();
    const note = $('#review-note').value.trim();
    if (!reviewer) { $('#decision-error').textContent = 'Informe o nome de quem está revisando.'; $('#decision-error').classList.remove('hidden'); $('#reviewer').focus(); return; }
    if (decision === 'rejeitado' && note.length < 5) { $('#decision-error').textContent = 'Escreva uma orientação de pelo menos 5 caracteres.'; $('#decision-error').classList.remove('hidden'); $('#review-note').focus(); return; }
    $('#decision-error').classList.add('hidden');
    const buttons = $$('#decision-fields button'); buttons.forEach(button => button.disabled = true);
    try {
      await api(`/api/documents/${encodeURIComponent(current.id)}/decision`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,reviewer,note})});
      $('#review-dialog').close(); await loadAll();
      toast(decision === 'aprovado' ? 'Arquivo aprovado e decisão registrada.' : 'Arquivo devolvido com justificativa.');
    } catch (error) { $('#decision-error').textContent = error.message; $('#decision-error').classList.remove('hidden'); }
    finally { buttons.forEach(button => button.disabled = false); }
  }

  function bindEvents() {
    $('#dependent-form').addEventListener('submit', createDependent);
    $('#upload-form').addEventListener('submit', uploadDocument);
    $('#browse-file').addEventListener('click', () => $('#file-input').click());
    $('#file-input').addEventListener('change', event => setSelected(event.target.files[0]));
    const zone = $('#dropzone');
    zone.addEventListener('click', event => { if (!event.target.closest('.link-button')) $('#file-input').click(); });
    zone.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); $('#file-input').click(); } });
    zone.addEventListener('dragover', event => { event.preventDefault(); zone.classList.add('dragging'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
    zone.addEventListener('drop', event => { event.preventDefault(); zone.classList.remove('dragging'); setSelected(event.dataTransfer.files[0]); });
    $$('.filter').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; $$('.filter').forEach(tab => tab.classList.toggle('active', tab === button)); renderDocuments(); }));
    $('#search').addEventListener('input', event => { query = event.target.value.trim(); renderDocuments(); });
    $('#document-rows').addEventListener('click', event => { const button = event.target.closest('[data-open]'); if (button) openReview(button.dataset.open); });
    $('#dependent-list').addEventListener('click', event => { const button = event.target.closest('[data-delete-dependent]'); if (button) removeDependent(button.dataset.deleteDependent); });
    $('#approve-button').addEventListener('click', () => submitDecision('aprovado'));
    $('#reject-button').addEventListener('click', () => {
      if (currentDecision !== 'rejeitado') { currentDecision = 'rejeitado'; $('#reject-note-wrap').classList.remove('hidden'); $('#reject-button').textContent = 'Confirmar devolução'; $('#approve-button').classList.add('hidden'); $('#review-note').focus(); return; }
      submitDecision('rejeitado');
    });
    $('#review-dialog').addEventListener('close', () => { current = null; currentDecision = ''; });
  }

  async function init() {
    bindEvents();
    try { await api('/api/health'); await loadAll(); }
    catch (error) { toast(error.message, true); }
  }
  init();
})();
