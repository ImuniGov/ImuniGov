import { useEffect, useState } from "react";
import { api } from "./api";
import { Badge, Section } from "./components";
import { formatDate } from "./format";

export default function FamilyReturns({
  selected,
  resend,
  onError,
  onlyRefused = false,
}) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api("/api/v1/family/feedback")
      .then((r) => setItems(r.items))
      .catch(onError);
  }, [onError]);
  const visible = items.filter(
    (i) =>
      (!selected || i.dependentId === selected) &&
      (!onlyRefused || ["rejeitado", "recusado"].includes(i.status)),
  );
  if (!visible.length) return null;
  return (
    <Section title="Retornos da UBS">
      <div className="feedback-list">
        {visible.map((i) => (
          <article
            className={`feedback-entry ${["rejeitado", "recusado"].includes(i.status) ? "refused" : ""}`}
            key={i.id}
          >
            <h3>
              {i.dependent} · {i.label}
            </h3>
            <Badge status={i.status} />
            <p>
              <strong>Retorno da equipe:</strong> {i.reason}
            </p>
            {i.nextStep && (
              <p>
                <strong>O que fazer agora:</strong> {i.nextStep}
              </p>
            )}
            <p className="small muted">
              {i.reviewers.map((r) => r.name).join(", ")} · {formatDate(i.at)}
            </p>
            {["rejeitado", "recusado"].includes(i.status) && (
              <button
                className="secondary"
                onClick={() => resend(i.dependentId)}
              >
                Enviar outra caderneta
              </button>
            )}
          </article>
        ))}
      </div>
    </Section>
  );
}
