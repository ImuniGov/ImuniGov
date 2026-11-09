import { useCallback, useEffect, useState } from "react";
import { Camera, Check, FileUp, RefreshCw, X } from "lucide-react";
import { api, send } from "./api";
import DosePlans from "./DosePlans";
import FamilyReturns from "./FamilyReturns";
import { Badge, Empty, Field, Modal, OpenFile, Section } from "./components";

import { useVaccineCatalog } from "./useVaccineCatalog";
import { formatDate, today } from "./format";

export function UploadForm({ people, selected, onClose, act, busy }) {
  const { names: vaccines } = useVaccineCatalog();
  const [file, setFile] = useState(null),
    [preview, setPreview] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    Promise.resolve().then(() => setPreview(url));
    return () => URL.revokeObjectURL(url);
  }, [file]);
  function choose(value) {
    setError("");
    if (
      value &&
      (!["image/jpeg", "image/png", "image/webp", "application/pdf"].includes(
        value.type,
      ) ||
        value.size > 10 * 1024 * 1024 ||
        !value.size)
    ) {
      setError("Escolha JPG, PNG, WEBP ou PDF, até 10 MB.");
      setFile(null);
      setPreview("");
      return;
    }
    setFile(value);
    if (!value) setPreview("");
  }
  async function submit(e) {
    e.preventDefault();
    if (!file) {
      setError("Escolha um arquivo para enviar.");
      return;
    }
    const form = new FormData(e.currentTarget);
    form.set("file", file);
    if (
      await act(
        () => api("/api/documents", { method: "POST", body: form }),
        "Caderneta enviada. A UBS fará a conferência.",
      )
    )
      onClose();
  }
  return (
    <Modal title="Enviar caderneta" onClose={onClose}>
      {!people.length ? (
        <Empty title="Cadastre uma pessoa primeiro">
          Volte à sua família e adicione a pessoa da caderneta.
        </Empty>
      ) : (
        <form onSubmit={submit}>
          <fieldset disabled={busy}>
            <p className="muted">
              Uma foto nítida ajuda a equipe. Confira o arquivo antes de enviar.
            </p>
            <Field label="De quem é a caderneta?">
              <select name="dependentId" defaultValue={selected} required>
                {people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <div className="form-grid">
              <Field label="Vacina ou tipo de registro">
                <select name="vaccine" required>
                  <option value="">Selecione</option>
                  {vaccines.map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
              <Field
                label="Data do registro (opcional)"
                type="date"
                name="doseDate"
                max={today()}
              />
            </div>
            <Field label="Observação (opcional)">
              <textarea
                name="note"
                rows={2}
                maxLength={500}
                placeholder="Algo que ajude na conferência"
              />
            </Field>
            <div
              className="dropzone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                choose(e.dataTransfer.files[0]);
              }}
            >
              <FileUp size={30} />
              <strong>Escolha um arquivo ou arraste até aqui</strong>
              <span>
                JPG, PNG, WEBP ou PDF • até 10 MB • PDF com até 10 páginas
              </span>
              <div className="button-row">
                <label className="secondary file-button">
                  Selecionar arquivo
                  <input
                    aria-label="Selecionar caderneta"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(e) => choose(e.target.files[0])}
                  />
                </label>
                <label className="secondary file-button">
                  <Camera size={16} /> Usar câmera
                  <input
                    aria-label="Capturar caderneta pela câmera"
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={(e) => choose(e.target.files[0])}
                  />
                </label>
              </div>
            </div>
            {preview && (
              <div className="file-preview">
                <div>
                  <strong>{file.name}</strong>
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => choose(null)}
                    aria-label="Remover arquivo"
                  >
                    <X size={18} />
                  </button>
                </div>
                {file.type === "application/pdf" ? (
                  <iframe title="Pré-visualização do PDF" src={preview} />
                ) : (
                  <img
                    src={preview}
                    alt="Pré-visualização da caderneta selecionada"
                  />
                )}
              </div>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <p className="small muted">
              O envio não confirma doses. As informações passam pela conferência
              da equipe.
            </p>
            <div className="modal-actions">
              <button type="button" className="secondary" onClick={onClose}>
                Cancelar
              </button>
              <button className="primary" type="submit" disabled={!file}>
                {busy ? "Enviando…" : "Confirmar envio"}
              </button>
            </div>
          </fieldset>
        </form>
      )}
    </Modal>
  );
}

export function DocumentReview({
  document,
  user,
  onClose,
  act,
  busy,
  onError,
}) {
  const { names: vaccines } = useVaccineCatalog();
  const [current, setCurrent] = useState(document),
    [records, setRecords] = useState([]),
    [job, setJob] = useState(null),
    [audit, setAudit] = useState([]),
    [priorVotes, setPriorVotes] = useState([]),
    [note, setNote] = useState(""),
    [guidance, setGuidance] = useState(""),
    [independent, setIndependent] = useState(false);
  const refresh = useCallback(async () => {
    const [d, r, p, a, h] = await Promise.all([
      api("/api/documents/" + document.id),
      api(`/api/v1/documents/${document.id}/extractions`),
      api(`/api/v1/documents/${document.id}/processing`),
      api("/api/audit?documentId=" + document.id),
      user.role === "familia"
        ? api(`/api/v1/documents/${document.id}/review-history`)
        : Promise.resolve({ items: [] }),
    ]);
    setCurrent(d.item);
    setRecords(r.items);
    setJob(p.item);
    setAudit(a.items);
    setPriorVotes(h.items);
  }, [document.id, user.role]);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
    const timer = setInterval(() => refresh().catch(onError), 8000);
    return () => clearInterval(timer);
  }, [refresh, onError]);
  async function decide(decision) {
    if (
      decision === "rejeitado" &&
      (note.trim().length < 3 || guidance.trim().length < 3)
    ) {
      onError(new Error("Informe o motivo e a orientação para novo envio."));
      return;
    }
    if (
      await act(
        () =>
          send(`/api/documents/${document.id}/decision`, {
            decision,
            note,
            guidance,
            independenceConfirmed: independent,
            reviewRound: current.review.round,
          }),
        "Conferência do arquivo registrada.",
      )
    )
      await refresh();
  }
  async function candidate(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.dose = Number(data.dose);
    if (
      await act(
        () => send(`/api/v1/documents/${document.id}/candidates`, data),
        "Registro adicionado como a conferir.",
      )
    ) {
      form.reset();
      await refresh();
    }
  }
  async function recordDecision(record, decision) {
    if (note.trim().length < 3) {
      onError(
        new Error(
          "Escreva uma justificativa de pelo menos 3 caracteres antes de decidir o registro.",
        ),
      );
      return;
    }
    if (
      await act(
        () =>
          send(`/api/v1/vaccinations/${record.id}/decision`, {
            decision,
            note,
            guidance,
            independenceConfirmed: independent,
            reviewRound: current.review.round,
          }),
        "Decisão do registro salva.",
      )
    )
      await refresh();
  }
  return (
    <Modal title="Conferir caderneta" onClose={onClose}>
      <div className="review-summary">
        <div>
          <strong>{current.dependent}</strong>
          <p>
            {current.fileName} • {formatDate(current.createdAt)}
          </p>
        </div>
        <Badge status={current.status} />
      </div>
      <OpenFile document={current} />
      {current.contentType.startsWith("image/") ? (
        <img
          className="evidence-image"
          src={current.fileUrl}
          alt="Caderneta enviada para conferência"
        />
      ) : (
        <iframe
          className="evidence-pdf"
          title="Caderneta PDF"
          src={current.fileUrl}
        />
      )}
      <p className="small muted">
        Informado no envio: {current.vaccine} • {formatDate(current.doseDate)}
      </p>
      {current.familyNote && (
        <p className="notice-box">
          Observação da família: {current.familyNote}
        </p>
      )}
      {job && (
        <div className="processing-box">
          <div>
            <Badge status={job.status} />
            <small>{job.attempts} tentativa(s)</small>
          </div>
          {job.error && <p>{job.error}</p>}
          {user.role === "ubs" &&
            ["failed", "unreadable"].includes(job.status) && (
              <button
                className="text-link"
                disabled={busy}
                onClick={async () => {
                  if (
                    await act(
                      () => send(`/api/v1/documents/${document.id}/retry`, {}),
                      "Nova leitura agendada.",
                    )
                  )
                    await refresh();
                }}
              >
                <RefreshCw size={15} /> Repetir leitura
              </button>
            )}
        </div>
      )}
      {current.review?.round > 1 && (
        <p className="review-state">
          Rodada {current.review.round}: a conferência foi reiniciada após uma
          alteração de equipe. Os votos anteriores foram preservados e não
          contam para esta rodada.
        </p>
      )}
      {user.role === "ubs" && (
        <div className="review-state">
          <p>Esta caderneta precisa de três aprovações independentes.</p>
          {current.review?.waitingForTeam && (
            <p role="status">
              Aguardando equipe completa. As restrições geográficas serão
              mantidas.
            </p>
          )}
          <label className="checkbox">
            <input
              type="checkbox"
              checked={independent}
              onChange={(e) => setIndependent(e.target.checked)}
            />
            <span>
              Não tenho vínculo pessoal ou conflito de interesse neste caso e
              farei minha própria conferência.
            </span>
          </label>
          <details>
            <summary>Tenho um impedimento para conferir</summary>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const data = Object.fromEntries(new FormData(e.currentTarget));
                if (
                  await act(
                    () =>
                      send(`/api/v1/documents/${document.id}/impediment`, data),
                    "Impedimento registrado. A caderneta voltará ao sorteio.",
                  )
                )
                  onClose();
              }}
            >
              <Field label="Motivo do impedimento">
                <textarea
                  name="reason"
                  required
                  minLength={3}
                  maxLength={500}
                />
              </Field>
              <button className="secondary" disabled={busy}>
                Registrar impedimento
              </button>
            </form>
          </details>
        </div>
      )}
      {user.role === "ubs" && (
        <>
          <Field label="Motivo da decisão">
            <textarea
              maxLength={300}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Explique o que você conferiu ou o motivo da recusa."
              rows={3}
            />
          </Field>
          <Field label="O que a família deve fazer">
            <textarea
              maxLength={500}
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
              rows={2}
              placeholder="Obrigatório ao devolver o arquivo ou recusar uma dose."
            />
          </Field>
        </>
      )}
      {current.review?.myVote && (
        <p className="review-state">
          {current.status === "pendente"
            ? "Seu voto foi registrado. A conclusão depende das outras conferências independentes."
            : "Sua decisão foi registrada."}
        </p>
      )}
      {user.role === "ubs" &&
        current.status === "pendente" &&
        !current.review?.myVote && (
          <div className="button-row">
            <button
              className="secondary danger-text"
              disabled={busy || !independent || current.review?.waitingForTeam}
              onClick={() => decide("rejeitado")}
            >
              Devolver para ajuste
            </button>
            <button
              className="primary"
              disabled={busy || !independent || current.review?.waitingForTeam}
              onClick={() => decide("aprovado")}
            >
              <Check size={16} /> Conferir arquivo
            </button>
          </div>
        )}
      {current.reviewGuidance && (
        <div className="notice-box">
          <strong>O que fazer agora</strong>
          <p>{current.reviewGuidance}</p>
        </div>
      )}
      {current.reviewedAt && (
        <div className="notice-box">
          <strong>
            {current.reviewer} • {formatDate(current.reviewedAt)}
          </strong>
          <p>{current.reviewNote}</p>
        </div>
      )}
      <h3 className="subheading">Doses encontradas no arquivo</h3>
      <p className="small muted">
        Aprovar o arquivo não confirma doses. Cada registro é conferido
        separadamente.
      </p>
      {records.length ? (
        records.map((r) => (
          <article className="record-card" key={r.id}>
            <div>
              <strong>
                {r.vaccine} • Dose {r.dose}
              </strong>
              <small>
                {formatDate(r.dose_date)} •{" "}
                {r.origin === "ocr"
                  ? "Leitura assistida"
                  : "Transcrição da UBS"}
                {r.confidence ? ` • Leitura automática: ${r.confidence}%` : ""}
              </small>
            </div>
            <Badge status={r.status} />
            {r.review_note && <p>{r.review_note}</p>}
            {r.review_guidance && (
              <p>
                <strong>O que fazer:</strong> {r.review_guidance}
              </p>
            )}
            {r.review?.myVote && <p>Seu voto está registrado.</p>}
            {user.role === "ubs" &&
              r.status === "a_conferir" &&
              !r.review?.myVote && (
                <div className="button-row">
                  <button
                    className="secondary danger-text"
                    disabled={busy || !independent}
                    onClick={() => recordDecision(r, "recusado")}
                  >
                    Recusar registro
                  </button>
                  <button
                    className="secondary"
                    disabled={
                      busy || !independent || current.status !== "aprovado"
                    }
                    onClick={() => recordDecision(r, "validado")}
                  >
                    Confirmar registro
                  </button>
                </div>
              )}
          </article>
        ))
      ) : (
        <p className="muted">
          Nenhuma dose identificada ainda. A UBS pode transcrever o que estiver
          legível no original.
        </p>
      )}
      {user.role === "ubs" && (
        <details className="transcription">
          <summary>Digitar uma dose do arquivo</summary>
          <form onSubmit={candidate}>
            <fieldset disabled={busy}>
              <Field label="Vacina">
                <select name="vaccine" required>
                  {vaccines.map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
              <div className="form-grid">
                <Field
                  label="Número da dose"
                  name="dose"
                  type="number"
                  min="1"
                  max="10"
                  defaultValue="1"
                  required
                />
                <Field
                  label="Data da dose"
                  name="doseDate"
                  type="date"
                  min="1900-01-01"
                  max={today()}
                  required
                />
              </div>
              <button className="secondary" type="submit">
                Adicionar como a conferir
              </button>
            </fieldset>
          </form>
        </details>
      )}
      {priorVotes.length > 0 && (
        <details className="audit">
          <summary>Conferências de rodadas anteriores</summary>
          <p>
            Estes votos foram preservados e não contam para a rodada atual.
            Doses concluídas anteriormente mantêm seu histórico próprio.
          </p>
          {priorVotes.map((v) => (
            <article className="feedback-entry" key={v.id}>
              <strong>
                Rodada {v.review_round} ·{" "}
                {v.target_type === "document"
                  ? "Arquivo"
                  : `${v.vaccine} · Dose ${v.dose}`}
              </strong>
              <p>
                {v.professional} · {formatDate(v.created_at)} ·{" "}
                {v.decision === "aprovar" ? "Aprovou" : "Recusou"}
              </p>
              <p>{v.note}</p>
              {v.guidance && (
                <p>
                  <strong>Orientação registrada:</strong> {v.guidance}
                </p>
              )}
            </article>
          ))}
        </details>
      )}
      <details className="audit">
        <summary>Histórico da conferência ({audit.length})</summary>
        {audit.map((a) => (
          <p key={a.id}>
            <strong>{a.event.replaceAll("_", " ")}</strong>
            <small>
              {formatDate(a.created_at)}
              {a.details && ` • ${a.details}`}
            </small>
          </p>
        ))}
      </details>
    </Modal>
  );
}

export function FamilyHistory({
  people,
  selected,
  onSelect,
  resend,
  user,
  act,
  busy,
  onError,
}) {
  const [records, setRecords] = useState([]),
    [pendings, setPendings] = useState([]),
    [guidance, setGuidance] = useState([]),
    [loading, setLoading] = useState(false);
  const refresh = useCallback(async () => {
    if (!selected) return;
    setLoading(true);
    try {
      const result = await Promise.all(
        ["vaccinations", "pendings", "guidance"].map((path) =>
          api(`/api/v1/dependents/${selected}/${path}`),
        ),
      );
      setRecords(result[0].items);
      setPendings(result[1].items);
      setGuidance(result[2].items);
    } finally {
      setLoading(false);
    }
  }, [selected]);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
  }, [refresh, onError]);
  async function addGuidance(e, pending) {
    e.preventDefault();
    const f = e.currentTarget;
    const form = new FormData(f);
    if (
      await act(
        () =>
          send(`/api/v1/pendings/${pending.id}/guidance`, {
            text: form.get("text"),
            released: form.get("released") === "on",
          }),
        "Orientação registrada.",
      )
    ) {
      f.reset();
      await refresh();
    }
  }
  return (
    <>
      <div className="person-selector">
        <Field label="Pessoa acompanhada">
          <select
            value={selected}
            onChange={(e) => onSelect(e.target.value)}
            aria-label="Selecionar pessoa para histórico"
          >
            <option value="">Selecione uma pessoa</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
        {user.role === "ubs" && selected && (
          <button
            className="secondary"
            disabled={busy}
            onClick={async () => {
              if (
                await act(
                  () => send(`/api/v1/dependents/${selected}/recalculate`, {}),
                  "Avaliação atualizada.",
                )
              )
                await refresh();
            }}
          >
            <RefreshCw size={16} /> Atualizar avaliação
          </button>
        )}
      </div>
      {user.role === "familia" && (
        <FamilyReturns selected={selected} onError={onError} resend={resend} />
      )}
      <DosePlans
        selected={selected}
        user={user}
        act={act}
        busy={busy}
        onError={onError}
      />
      <div className="notice-box">
        <ShieldScope />
      </div>
      {!selected ? (
        <Section title="Vacinas e orientações">
          <Empty title="Selecione uma pessoa">
            As informações ficam organizadas por pessoa.
          </Empty>
        </Section>
      ) : loading ? (
        <div className="loading-inline" role="status">
          Carregando acompanhamento…
        </div>
      ) : (
        <>
          <Section
            title="Vacinas registradas"
            description="Origem, dose e situação de cada registro."
          >
            {records.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>VACINA / DOSE</th>
                      <th>DATA</th>
                      <th>ORIGEM</th>
                      <th>SITUAÇÃO</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <strong>{r.vaccine}</strong>
                          <small>Dose {r.dose}</small>
                        </td>
                        <td>{formatDate(r.dose_date)}</td>
                        <td>
                          {r.origin === "ocr"
                            ? "Leitura assistida"
                            : "Transcrição UBS"}
                          {r.document_id && (
                            <a
                              className="text-link small"
                              href={`/api/documents/${r.document_id}/file`}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Ver evidência
                            </a>
                          )}
                        </td>
                        <td>
                          <Badge status={r.status} />
                          {r.review_note && <small>{r.review_note}</small>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty title="Histórico aguardando registros">
                Envie uma caderneta para a equipe conferir as informações.
              </Empty>
            )}
          </Section>
          <Section
            title="Doses para conferir com a UBS"
            description="O histórico pode estar incompleto. A UBS deve conferir antes de indicar uma vacina."
          >
            {pendings.length ? (
              <div className="pending-list">
                {pendings.map((p) => (
                  <article key={p.id}>
                    <div className="section-heading">
                      <div>
                        <h3>
                          {p.vaccine} • Dose {p.dose}
                        </h3>
                        <p>{p.reason}</p>
                      </div>
                      <Badge status={p.status} />
                    </div>
                    <small className="muted">
                      Regra {p.rule_id} • versão {p.rule_version} •{" "}
                      {formatDate(p.updated_at)}
                    </small>
                    {user.role === "ubs" && (
                      <details className="transcription">
                        <summary>Orientar a família</summary>
                        <form onSubmit={(e) => addGuidance(e, p)}>
                          <fieldset disabled={busy}>
                            <Field label="Orientação da UBS">
                              <textarea
                                name="text"
                                minLength={3}
                                maxLength={1000}
                                rows={3}
                                required
                              />
                            </Field>
                            <label className="checkbox">
                              <input
                                type="checkbox"
                                name="released"
                                defaultChecked
                              />
                              <span>Liberar para a família</span>
                            </label>
                            <button className="secondary" type="submit">
                              Salvar orientação
                            </button>
                          </fieldset>
                        </form>
                      </details>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <Empty title="Nenhuma pendência nas vacinas avaliadas">
                Isso não comprova situação vacinal completa. A UBS deve conferir
                as demais vacinas e condições individuais.
              </Empty>
            )}
          </Section>
          <Section
            title="Orientações da equipe"
            description="Histórico das orientações liberadas pela UBS."
          >
            {guidance.length ? (
              guidance.map((g) => (
                <article className="guidance-card" key={g.id}>
                  <span className="eyebrow">
                    ORIENTAÇÃO UBS{!g.released && " • RASCUNHO"}
                  </span>
                  <p>{g.text}</p>
                  <small>
                    {formatDate(g.created_at)} • Profissional{" "}
                    {g.author_id.slice(0, 8)}
                  </small>
                </article>
              ))
            ) : (
              <Empty title="Nenhuma orientação liberada">
                Quando a equipe registrar uma orientação, ela aparecerá aqui.
              </Empty>
            )}
          </Section>
        </>
      )}
    </>
  );
}

function ShieldScope() {
  return (
    <>
      <strong>Sobre a avaliação automática</strong>
      <p>
        Este MVP avalia BCG, pentavalente e poliomielite VIP, segundo o recorte
        de regras de 2026. Outras vacinas, esquemas especiais e condições
        individuais precisam de avaliação da UBS. Registros “a conferir” não
        contam como doses confirmadas.{" "}
        <a
          href="https://www.gov.br/saude/pt-br/vacinacao/calendario"
          target="_blank"
          rel="noreferrer"
        >
          Consultar calendário do Ministério da Saúde
        </a>
        .
      </p>
    </>
  );
}

export function Outreach({ user, act, busy, onError }) {
  const [cases, setCases] = useState([]),
    [selected, setSelected] = useState(null),
    [actions, setActions] = useState([]),
    [q, setQ] = useState(""),
    [priority, setPriority] = useState("todas"),
    [status, setStatus] = useState("aberta");
  const refresh = useCallback(async () => {
    const r = await api(`/api/v1/acs/cases?status=${status}`);
    setCases(r.items);
  }, [status]);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
  }, [refresh, onError]);
  const loadActions = useCallback(async () => {
    if (selected)
      setActions((await api(`/api/v1/acs/cases/${selected.id}/actions`)).items);
  }, [selected]);
  useEffect(() => {
    Promise.resolve().then(loadActions).catch(onError);
  }, [loadActions, onError]);
  async function contact(e) {
    e.preventDefault();
    const f = e.currentTarget;
    if (
      await act(
        () =>
          send(
            `/api/v1/acs/cases/${selected.id}/actions`,
            Object.fromEntries(new FormData(f)),
          ),
        "Contato registrado.",
      )
    ) {
      f.reset();
      await loadActions();
      await refresh();
    }
  }
  const shown = cases.filter(
    (c) =>
      `${c.dependent} ${c.guardian}`.toLowerCase().includes(q.toLowerCase()) &&
      (priority === "todas" || c.priority === priority),
  );
  return (
    <>
      <Section
        title="Famílias para acompanhamento"
        description="Os casos mais antigos aparecem primeiro. A fila expõe apenas o necessário para contato."
      >
        <div className="table-toolbar">
          <Field
            label="Buscar pessoa ou responsável"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar nome"
          />
          <Field label="Prioridade">
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="todas">Todas</option>
              <option value="alta">Alta • 30 dias ou mais</option>
              <option value="normal">Normal</option>
            </select>
          </Field>
          <Field label="Situação">
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="aberta">Casos ativos</option>
              <option value="resolvida">Histórico de resolvidos</option>
            </select>
          </Field>
        </div>
        {shown.length ? (
          <div className="outreach-list">
            {shown.map((c) => (
              <button
                key={c.id}
                className="outreach-row"
                onClick={() => setSelected(c)}
              >
                <span className="person-avatar">{c.dependent.charAt(0)}</span>
                <span>
                  <strong>{c.dependent}</strong>
                  <small>Responsável: {c.guardian}</small>
                  <small>{c.reason}</small>
                </span>
                <span
                  className={`badge ${c.priority === "alta" ? "rejeitado" : "a_conferir"}`}
                >
                  {c.priority === "alta" ? "Alta prioridade" : "Acompanhar"}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <Empty title="Nenhum caso neste filtro">
            Os casos resolvidos saem da fila ativa e continuam no histórico.
          </Empty>
        )}
      </Section>
      {selected && (
        <Modal
          title="Acompanhamento da família"
          onClose={() => setSelected(null)}
        >
          <h3>{selected.dependent}</h3>
          <p className="muted">Responsável: {selected.guardian}</p>
          <p>Contato: {selected.contact || "Não informado"}</p>
          <p className="notice-box">{selected.reason}</p>
          {user.role === "acs" && status === "aberta" && (
            <form onSubmit={contact}>
              <fieldset disabled={busy}>
                <div className="form-grid">
                  <Field label="Tipo de contato">
                    <select name="kind">
                      <option value="telefone">Telefone</option>
                      <option value="visita">Visita</option>
                      <option value="mensagem">Mensagem</option>
                      <option value="sem_contato">Tentativa sem contato</option>
                    </select>
                  </Field>
                  <Field
                    label="Data do contato"
                    type="date"
                    name="contactDate"
                    max={today()}
                    defaultValue={today()}
                    required
                  />
                </div>
                <Field label="Nota do acompanhamento">
                  <textarea
                    name="note"
                    minLength={3}
                    maxLength={500}
                    rows={3}
                    required
                  />
                </Field>
                <button className="primary" type="submit">
                  {busy ? "Registrando…" : "Registrar contato"}
                </button>
              </fieldset>
            </form>
          )}
          <h3 className="subheading">Histórico de ações</h3>
          {actions.length ? (
            actions.map((a) => (
              <article className="guidance-card" key={a.id}>
                <strong>
                  {a.kind.replaceAll("_", " ")} • {formatDate(a.contact_date)}
                </strong>
                <p>{a.note}</p>
                <small>
                  {a.author_name || "Agente comunitário"} •{" "}
                  {formatDate(a.created_at)}
                </small>
              </article>
            ))
          ) : (
            <p className="muted">Ainda não há contatos registrados.</p>
          )}
        </Modal>
      )}
    </>
  );
}
