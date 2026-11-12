import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, ChevronRight, FileUp, RefreshCw, X } from "lucide-react";
import { api, send } from "./api";
import DosePlans from "./DosePlans";
import FamilyReturns from "./FamilyReturns";
import {
  Badge,
  Empty,
  Field,
  Modal,
  OpenFile,
  RouteDetails,
  Section,
} from "./components";

import { useVaccineCatalog } from "./useVaccineCatalog";
import { formatDate, today, vaccineLabel } from "./format";

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
                    <option key={v} value={v}>
                      {vaccineLabel(v)}
                    </option>
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
              <strong>Foto ou PDF</strong>
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

const reviewSteps = [
  ["arquivo", "Arquivo"],
  ["decisao", "Decisão"],
  ["doses", "Doses"],
  ["historico", "Histórico"],
];

function ReviewDecision({ options, onSubmit, busy, record = false }) {
  const [decision, setDecision] = useState("");
  const refused = decision === "rejeitado" || decision === "recusado";
  return (
    <form
      className="review-decision"
      onSubmit={(event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(event.currentTarget));
        onSubmit(decision, data.note.trim(), data.guidance.trim());
      }}
    >
      <fieldset disabled={busy}>
        <Field label="Sua decisão">
          <select
            required
            value={decision}
            onChange={(event) => setDecision(event.target.value)}
          >
            <option value="">Selecione</option>
            {options.map(([value, label, disabled]) => (
              <option key={value} value={value} disabled={disabled}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        {decision && (
          <>
            <Field
              label={
                record || refused ? "Motivo da decisão" : "Motivo (opcional)"
              }
            >
              <textarea
                name="note"
                rows={2}
                required={record || refused}
                minLength={3}
                maxLength={300}
              />
            </Field>
            <Field
              label={
                refused
                  ? "O que a família deve fazer"
                  : "Orientação para a família (opcional)"
              }
            >
              <textarea
                name="guidance"
                rows={2}
                required={refused}
                minLength={3}
                maxLength={500}
              />
            </Field>
          </>
        )}
        <button className="primary" type="submit" disabled={!decision}>
          {busy ? "Salvando…" : "Registrar decisão"}
        </button>
      </fieldset>
    </form>
  );
}

export function DocumentReview({
  document,
  user,
  onClose,
  act,
  busy,
  onError,
  step,
  route,
  onStep,
}) {
  const guided = user.role === "ubs";
  const activeStep = Math.max(
    0,
    reviewSteps.findIndex(([id]) => id === step),
  );
  const heading = useRef(null);
  function move(index) {
    onStep(reviewSteps[index][0]);
    requestAnimationFrame(() => {
      heading.current?.focus({ preventScroll: true });
      heading.current?.closest("dialog")?.scrollTo({ top: 0 });
    });
  }
  const { names: vaccines } = useVaccineCatalog();
  const [current, setCurrent] = useState(document),
    [records, setRecords] = useState([]),
    [pendings, setPendings] = useState([]),
    [job, setJob] = useState(null),
    [audit, setAudit] = useState([]),
    [priorVotes, setPriorVotes] = useState([]),
    [confirmedRound, setConfirmedRound] = useState(null);
  const independent = confirmedRound === current.review?.round;
  const refresh = useCallback(async () => {
    const [d, r, pend, p, a, h] = await Promise.all([
      api("/api/documents/" + document.id),
      api(`/api/v1/documents/${document.id}/extractions`),
      api(`/api/v1/dependents/${document.dependentId}/pendings`),
      api(`/api/v1/documents/${document.id}/processing`),
      api("/api/audit?documentId=" + document.id),
      user.role === "familia"
        ? api(`/api/v1/documents/${document.id}/review-history`)
        : Promise.resolve({ items: [] }),
    ]);
    setCurrent(d.item);
    setRecords(r.items);
    setPendings(pend.items);
    setJob(p.item);
    setAudit(a.items);
    setPriorVotes(h.items);
  }, [document.id, document.dependentId, user.role]);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
    const timer = setInterval(() => refresh().catch(onError), 8000);
    return () => clearInterval(timer);
  }, [refresh, onError]);
  async function decide(decision, note, guidance) {
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
        decision === "rejeitado"
          ? "Arquivo devolvido para ajuste da família."
          : "Conferência do arquivo registrada.",
      )
    ) {
      if (decision === "rejeitado") {
        onClose();
        return;
      }
      await refresh();
      onStep("doses");
    }
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
  async function recordDecision(record, decision, note, guidance) {
    if (note.length < 3 || (decision === "recusado" && guidance.length < 3)) {
      onError(
        new Error("Informe o motivo e, se recusar a dose, oriente a família."),
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
    ) {
      await refresh();
      onStep("doses");
    }
  }
  const onHold = Boolean(current.reviewHold || current.review?.onHold);
  const canVoteDocument =
    user.role === "ubs" &&
    current.status === "pendente" &&
    !onHold &&
    !current.review?.myVote;
  const canVoteAnyRecord =
    user.role === "ubs" &&
    current.status !== "rejeitado" &&
    !onHold &&
    records.some((r) => r.status === "a_conferir" && !r.review?.myVote);
  const canActUbs = canVoteDocument || canVoteAnyRecord;
  const wizardPath = route.parts.slice(0, 2);
  const canSubmit = independent && !current.review?.waitingForTeam && !busy;
  return (
    <Modal
      title={guided ? "Conferir caderneta" : "Detalhes da caderneta"}
      onClose={onClose}
    >
      <div className="review-summary">
        <strong>{current.dependent}</strong>
        <Badge status={current.status} />
      </div>
      {guided && (
        <nav className="review-steps" aria-label="Etapas da conferência">
          <ol>
            {reviewSteps.map(([id, label], index) => (
              <li key={id}>
                <button
                  type="button"
                  aria-current={index === activeStep ? "step" : undefined}
                  disabled={busy}
                  onClick={() => move(index)}
                >
                  <span aria-hidden="true">{index + 1}</span>
                  {label}
                </button>
              </li>
            ))}
          </ol>
        </nav>
      )}
      {guided && (
        <h3 className="review-heading" tabIndex={-1} ref={heading}>
          {reviewSteps[activeStep][1]}
        </h3>
      )}
      <div hidden={guided && activeStep !== 0}>
        <div className="review-file">
          <small>
            {current.fileName} · {formatDate(current.createdAt)}
          </small>
          <OpenFile document={current} />
        </div>
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
          Informado no envio: {vaccineLabel(current.vaccine)} •{" "}
          {formatDate(current.doseDate)}
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
              {job.attempts > 0 && <small>Tentativas: {job.attempts}</small>}
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
                        () =>
                          send(`/api/v1/documents/${document.id}/retry`, {}),
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
      </div>
      {onHold && (
        <p className="form-error" role="alert">
          Conferência pausada. A administração vai analisar o impedimento.
        </p>
      )}
      {current.review?.round > 1 && (
        <p className="review-state">
          Rodada {current.review.round}. Os votos anteriores estão no histórico.
        </p>
      )}
      {guided && current.status !== "rejeitado" && (
        <div
          className="review-independence"
          hidden={activeStep !== 1 && activeStep !== 2}
        >
          {current.review?.waitingForTeam && (
            <p className="review-state" role="status">
              Aguardando equipe de três revisores.
            </p>
          )}
          {canActUbs && (
            <label className="checkbox">
              <input
                type="checkbox"
                checked={independent}
                onChange={(e) =>
                  setConfirmedRound(
                    e.target.checked ? current.review?.round : null,
                  )
                }
              />
              <span>
                Vou conferir sem vínculo pessoal ou conflito de interesse.
              </span>
            </label>
          )}
          {!onHold && (
            <RouteDetails
              route={route}
              parent={[...wizardPath, step || "decisao"]}
              path={[...wizardPath, step || "decisao", "informar-impedimento"]}
              title="Informar impedimento"
            >
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const data = Object.fromEntries(
                    new FormData(e.currentTarget),
                  );
                  if (
                    await act(() =>
                      send(`/api/v1/documents/${document.id}/impediment`, data),
                    )
                  ) {
                    onClose();
                  }
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
                <p className="small muted">
                  Se você já registrou voto neste caso, a conferência será
                  suspensa para análise administrativa, preservando o histórico.
                </p>
                <button className="secondary" disabled={busy}>
                  Registrar impedimento
                </button>
              </form>
            </RouteDetails>
          )}
        </div>
      )}
      <div hidden={guided && activeStep !== 1}>
        {current.review?.myVote && (
          <p className="review-state">
            {current.status === "pendente"
              ? "Voto salvo. Aguardando os outros revisores."
              : "Decisão salva."}
          </p>
        )}
        {canVoteDocument && (
          <ReviewDecision
            key={current.review?.round}
            options={[
              ["aprovado", "Aprovar o arquivo"],
              ["rejeitado", "Devolver para ajuste"],
            ]}
            onSubmit={decide}
            busy={!canSubmit}
          />
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
      </div>
      <div hidden={guided && activeStep !== 2}>
        {!guided && (
          <h3 className="subheading">Doses encontradas no arquivo</h3>
        )}
        <p className="small muted">
          {guided
            ? "Confira cada dose separadamente."
            : "A UBS confere cada dose."}
        </p>
        {records.length ? (
          records.map((r) => (
            <article className="record-card" key={r.id}>
              <div>
                <strong>
                  {vaccineLabel(r.vaccine)} • Dose {r.dose}
                </strong>
                <small>
                  {formatDate(r.dose_date)} •{" "}
                  {r.origin === "ocr"
                    ? "Leitura automática"
                    : "Digitada pela equipe"}
                  {r.confidence
                    ? ` • Leitura automática: ${r.confidence}%`
                    : ""}
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
              {guided &&
                current.status !== "rejeitado" &&
                r.status === "a_conferir" &&
                !onHold &&
                !r.review?.myVote && (
                  <RouteDetails
                    route={route}
                    parent={[...wizardPath, "doses"]}
                    path={[...wizardPath, "doses", "conferir-dose", r.id]}
                    title="Conferir esta dose"
                  >
                    {current.status !== "aprovado" && (
                      <p className="small muted">
                        Confirme a dose após a aprovação do arquivo.
                      </p>
                    )}
                    <ReviewDecision
                      record
                      key={current.review?.round}
                      options={[
                        [
                          "validado",
                          "Confirmar dose",
                          current.status !== "aprovado",
                        ],
                        ["recusado", "Recusar registro"],
                      ]}
                      onSubmit={(decision, note, guidance) =>
                        recordDecision(r, decision, note, guidance)
                      }
                      busy={!canSubmit}
                    />
                  </RouteDetails>
                )}
            </article>
          ))
        ) : (
          <p className="muted">Nenhuma dose encontrada.</p>
        )}
        {user.role === "ubs" && current.status !== "rejeitado" && !onHold && (
          <RouteDetails
            className="transcription"
            route={route}
            parent={[...wizardPath, "doses"]}
            path={[...wizardPath, "doses", "digitar-dose"]}
            title="Digitar uma dose do arquivo"
          >
            <form onSubmit={candidate}>
              <fieldset disabled={busy}>
                <Field label="Vacina">
                  <select name="vaccine" required>
                    {vaccines.map((v) => (
                      <option key={v} value={v}>
                        {vaccineLabel(v)}
                      </option>
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
          </RouteDetails>
        )}
      </div>
      <div hidden={guided && activeStep !== 3}>
        <h3 className="subheading">Doses sinalizadas pelo sistema</h3>
        {pendings.filter((p) => p.status === "aberta").length ? (
          <div className="pending-list">
            {pendings
              .filter((p) => p.status === "aberta")
              .map((p) => (
                <article className="record-card" key={p.id}>
                  <div>
                    <strong>
                      {vaccineLabel(p.vaccine)} • Dose {p.dose}
                    </strong>
                    <details>
                      <summary>Motivo e regra</summary>
                      <p>{p.reason}</p>
                      <small>
                        Regra {p.rule_id} ({p.rule_version})
                      </small>
                    </details>
                  </div>
                  <Badge status={p.status} />
                </article>
              ))}
          </div>
        ) : (
          <p className="muted">Nenhuma dose sinalizada.</p>
        )}
        {pendings.some((p) => p.status === "resolvida") && (
          <details className="audit">
            <summary>
              Histórico de pendências resolvidas desta pessoa (
              {pendings.filter((p) => p.status === "resolvida").length})
            </summary>
            {pendings
              .filter((p) => p.status === "resolvida")
              .map((p) => (
                <article className="feedback-entry" key={p.id}>
                  <strong>
                    {vaccineLabel(p.vaccine)} • Dose {p.dose} • Resolvida após
                    conferência UBS
                  </strong>
                  <p>
                    <strong>Motivo anterior (resolvido):</strong>{" "}
                    {p.historical_reason || p.reason}
                  </p>
                  <small>
                    Regra {p.rule_id} ({p.rule_version}) •{" "}
                    {formatDate(p.updated_at)}
                  </small>
                </article>
              ))}
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
                    : `${vaccineLabel(v.vaccine)} · Dose ${v.dose}`}
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
      </div>
      <div className="modal-actions review-actions">
        {guided && activeStep > 0 && (
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={() => move(activeStep - 1)}
          >
            Voltar
          </button>
        )}
        {guided && activeStep < reviewSteps.length - 1 ? (
          <button
            className="primary"
            type="button"
            disabled={busy}
            onClick={() => move(activeStep + 1)}
          >
            Continuar
          </button>
        ) : (
          <button className="secondary" type="button" onClick={onClose}>
            Fechar
          </button>
        )}
      </div>
    </Modal>
  );
}

export function FamilyHistory({
  people,
  selected,
  onSelect,
  route,
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
        route={route}
        selected={selected}
        user={user}
        act={act}
        busy={busy}
        onError={onError}
      />
      <details className="notice-box">
        <summary>Quais vacinas o sistema acompanha?</summary>
        <ShieldScope />
      </details>
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
                      <th scope="col">VACINA / DOSE</th>
                      <th scope="col">DATA</th>
                      <th scope="col">ORIGEM</th>
                      <th scope="col">SITUAÇÃO</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <strong>{vaccineLabel(r.vaccine)}</strong>
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
            description="O sistema sugere quais doses conferir com a unidade de saúde."
          >
            {pendings.filter((p) => p.status === "aberta").length ? (
              <div className="pending-list">
                {pendings
                  .filter((p) => p.status === "aberta")
                  .map((p) => (
                    <article key={p.id}>
                      <div className="section-heading">
                        <div>
                          <span className="eyebrow">
                            CÁLCULO AUTOMÁTICO • SUJEITO À CONFERÊNCIA DA UBS
                          </span>
                          <h3>
                            {vaccineLabel(p.vaccine)} • Dose {p.dose}
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
                        <RouteDetails
                          className="transcription"
                          route={route}
                          parent={["pessoa", selected]}
                          path={["pessoa", selected, "orientar-familia", p.id]}
                          title="Orientar a família"
                        >
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
                        </RouteDetails>
                      )}
                    </article>
                  ))}
              </div>
            ) : (
              <Empty title="Nenhuma pendência aberta nas vacinas avaliadas">
                Isso não comprova situação vacinal completa. A UBS deve conferir
                as demais vacinas e condições individuais.
              </Empty>
            )}
            {pendings.some((p) => p.status === "resolvida") && (
              <details className="audit">
                <summary>
                  Histórico de pendências resolvidas (
                  {pendings.filter((p) => p.status === "resolvida").length})
                </summary>
                <p className="small muted">
                  Pendências encerradas após confirmação profissional de dose
                  compatível. Os motivos abaixo referem-se apenas à situação
                  anterior à resolução.
                </p>
                {pendings
                  .filter((p) => p.status === "resolvida")
                  .map((p) => (
                    <article className="feedback-entry" key={p.id}>
                      <div className="section-heading">
                        <div>
                          <span className="eyebrow">
                            CONFERÊNCIA PROFISSIONAL CONCLUÍDA
                          </span>
                          <h3>
                            {vaccineLabel(p.vaccine)} • Dose {p.dose}
                          </h3>
                        </div>
                        <Badge status={p.status} />
                      </div>
                      <p>
                        <strong>Motivo anterior (resolvido):</strong>{" "}
                        {p.historical_reason || p.reason}
                      </p>
                      <small className="muted">
                        Regra {p.rule_id} • versão {p.rule_version} • Resolvida
                        em {formatDate(p.updated_at)}
                      </small>
                    </article>
                  ))}
              </details>
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
                    ORIENTAÇÃO UBS
                    {g.vaccine ? ` • ${g.vaccine} (DOSE ${g.dose})` : ""}
                    {!g.released && " • RASCUNHO"}
                  </span>
                  <p>{g.text}</p>
                  <small>
                    {formatDate(g.created_at)} •{" "}
                    {g.author_name || `Profissional ${g.author_id.slice(0, 8)}`}
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
      <p>
        O sistema acompanha algumas vacinas da infância. A unidade de saúde pode
        conferir outras vacinas, situações especiais e doses que ainda aguardam
        confirmação.{" "}
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

export function AgentGuide({ compact = false }) {
  const text = (
    <>
      <p>
        O agente comunitário de saúde (ACS) aproxima a família da unidade de
        saúde.
      </p>
      <ol className="task-list">
        <li>Comece pelos casos mais antigos.</li>
        <li>
          Ligue, mande mensagem ou visite. Oriente a família a procurar a
          unidade.
        </li>
        <li>Registre o contato ou a tentativa.</li>
      </ol>
      <p>A unidade confere a caderneta e as doses.</p>
    </>
  );
  return compact ? (
    <details className="notice-box">
      <summary>Como funciona o contato?</summary>
      {text}
    </details>
  ) : (
    <Section title="O que faz o ACS?" className="agent-guide">
      {text}
    </Section>
  );
}

export function Outreach({ user, act, busy, onError, route }) {
  const [list, setList] = useState(null);
  const [history, setHistory] = useState(null);
  const q = route.search;
  const priority = route.query.get("prioridade") || "todas";
  const status =
    route.query.get("situacao") === "resolvida" ? "resolvida" : "aberta";
  const [action, id, form] = route.parts;
  const cases = list?.status === status ? list.items : [];
  const selected =
    action === "ver-contato" ? cases.find((item) => item.id === id) : null;
  const selectedId = selected?.id;
  const actions = history?.id === selectedId ? history?.items || [] : [];
  const refresh = useCallback(async () => {
    const r = await api(`/api/v1/acs/cases?status=${status}`);
    setList({ status, items: r.items });
  }, [status]);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
  }, [refresh, onError]);
  const loadActions = useCallback(async () => {
    if (!selectedId) return;
    const result = await api(`/api/v1/acs/cases/${selectedId}/actions`);
    setHistory({ id: selectedId, items: result.items });
  }, [selectedId]);
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
      route.open(["ver-contato", selectedId], { replace: true });
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
      {user.role === "acs" && <AgentGuide compact />}
      <Section title="Famílias para contatar">
        <div className="table-toolbar">
          <Field
            label="Buscar por nome"
            value={q}
            onChange={(e) => route.setSearch(e.target.value)}
            placeholder="Pessoa ou responsável"
          />
          <details className="outreach-filters">
            <summary>
              Filtros
              {priority !== "todas" || status !== "aberta" ? " ativos" : ""}
            </summary>
            <div className="form-grid">
              <Field label="Prioridade">
                <select
                  value={priority}
                  onChange={(e) =>
                    route.setFilter("prioridade", e.target.value, "todas")
                  }
                >
                  <option value="todas">Todas</option>
                  <option value="alta">Alta (30 dias ou mais)</option>
                  <option value="normal">Normal</option>
                </select>
              </Field>
              <Field label="Situação">
                <select
                  value={status}
                  onChange={(e) =>
                    route.setFilter("situacao", e.target.value, "aberta")
                  }
                >
                  <option value="aberta">Ativos</option>
                  <option value="resolvida">Resolvidos</option>
                </select>
              </Field>
            </div>
          </details>
        </div>
        {shown.length ? (
          <div className="outreach-list">
            {shown.map((c) => (
              <button
                key={c.id}
                className="outreach-row"
                onClick={() => route.open(["ver-contato", c.id])}
              >
                <span className="person-avatar">{c.dependent.charAt(0)}</span>
                <span>
                  <strong>{c.dependent}</strong>
                  <small>Responsável: {c.guardian}</small>
                </span>
                {c.priority === "alta" && (
                  <span className="badge rejeitado">Prioridade alta</span>
                )}
                <ChevronRight aria-hidden="true" size={16} />
              </button>
            ))}
          </div>
        ) : (
          <Empty
            title={
              list?.status === status
                ? "Nenhum caso neste filtro"
                : "Carregando contatos…"
            }
          />
        )}
      </Section>
      {action === "ver-contato" && list?.status === status && !selected && (
        <Modal title="Contato indisponível" onClose={route.close}>
          <p>Consulte a lista de contatos ou o histórico.</p>
        </Modal>
      )}
      {selected && (
        <Modal title="Acompanhamento da família" onClose={route.close}>
          <h3>{selected.dependent}</h3>
          <p className="muted">Responsável: {selected.guardian}</p>
          <p>Contato: {selected.contact || "Não informado"}</p>
          <details className="contact-reason">
            <summary>Motivo do acompanhamento</summary>
            <p>{selected.reason}</p>
          </details>
          {user.role === "acs" &&
            status === "aberta" &&
            form !== "registrar" && (
              <button
                className="primary"
                onClick={() =>
                  route.open(["ver-contato", selectedId, "registrar"], {
                    replace: true,
                  })
                }
              >
                Registrar contato
              </button>
            )}
          {user.role === "acs" &&
            status === "aberta" &&
            form === "registrar" && (
              <form key={selectedId} onSubmit={contact}>
                <fieldset disabled={busy}>
                  <div className="form-grid">
                    <Field label="Tipo de contato">
                      <select name="kind">
                        <option value="telefone">Telefone</option>
                        <option value="visita">Visita</option>
                        <option value="mensagem">Mensagem</option>
                        <option value="sem_contato">
                          Tentativa sem contato
                        </option>
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
                  <Field label="Como foi o contato?">
                    <textarea
                      name="note"
                      minLength={3}
                      maxLength={500}
                      rows={3}
                      required
                    />
                  </Field>
                  <div className="button-row">
                    <button
                      className="secondary"
                      type="button"
                      onClick={() =>
                        route.open(["ver-contato", selectedId], {
                          replace: true,
                        })
                      }
                    >
                      Cancelar
                    </button>
                    <button className="primary" type="submit">
                      {busy ? "Registrando…" : "Salvar contato"}
                    </button>
                  </div>
                </fieldset>
              </form>
            )}
          <h3 className="subheading">Contatos anteriores</h3>
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
