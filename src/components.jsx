import { useContext, useEffect, useId, useRef, useState } from "react";
import { X, Plus, ArrowUpRight } from "lucide-react";

import { FeedbackContext } from "./feedback";
import { api } from "./api";
import { labels } from "./format";
export function Badge({ status }) {
  return <span className={`badge ${status}`}>{labels[status] || status}</span>;
}
export function Empty({ title = "Tudo tranquilo por aqui", children, action }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function Section({
  title,
  description,
  action,
  children,
  className = "",
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Field({ label, children, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children || <input {...props} />}
    </label>
  );
}
export function AddButton({ children, ...props }) {
  return (
    <button className="primary" {...props}>
      <Plus size={17} />
      {children}
    </button>
  );
}
export function Modal({ title, onClose, children }) {
  const ref = useRef(null);
  const headingId = useId();
  const feedback = useContext(FeedbackContext);
  useEffect(() => {
    const d = ref.current;
    d.showModal();
    const close = (e) => {
      e.preventDefault();
      onClose();
    };
    d.addEventListener("cancel", close);
    return () => {
      d.removeEventListener("cancel", close);
      d.close();
    };
  }, [onClose]);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={headingId}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="modal-title">
        <h2 id={headingId}>{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="Fechar">
          <X size={22} />
        </button>
      </div>
      {feedback && (
        <p
          className={feedback.error ? "form-error" : "notice-box"}
          role={feedback.error ? "alert" : "status"}
        >
          {feedback.text}
        </p>
      )}
      {children}
    </dialog>
  );
}
export function Privacy({ onClose }) {
  const [notice, setNotice] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    api("/api/v1/privacy/notice")
      .then(setNotice)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <Modal title="Termos de uso e privacidade" onClose={onClose}>
      <div className="prose">
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {!notice && !error && <p role="status">Carregando o texto…</p>}
        {notice && (
          <>
            <p className="small">
              Versão {notice.version} · Responsável: {notice.controller}
            </p>
            <p>{notice.summary}</p>
            <p>
              Contato: <a href={`mailto:${notice.contact}`}>{notice.contact}</a>
            </p>
            {notice.sections.map((s) => (
              <section key={s.title}>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </section>
            ))}
            <h3>Referências</h3>
            <ul>
              {notice.sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title}
                  </a>
                </li>
              ))}
            </ul>
            <p className="small muted">
              O aceite será solicitado separadamente no cadastro.
            </p>
          </>
        )}
        <button className="secondary" onClick={onClose}>
          Voltar
        </button>
      </div>
    </Modal>
  );
}
export function OpenFile({ document }) {
  return (
    <a
      className="text-link"
      href={document.fileUrl}
      target="_blank"
      rel="noreferrer"
    >
      Abrir original <ArrowUpRight size={15} />
    </a>
  );
}
