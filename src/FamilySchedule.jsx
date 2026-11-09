import { useState } from "react";
import { ArrowRight, CalendarClock, Clock3 } from "lucide-react";
import { Empty, Field, Section } from "./components";
import { formatDate } from "./format";

export function ScheduleSummary({ schedule, open }) {
  const close = schedule.items.filter(
    (i) => i.daysUntil >= 0 && i.daysUntil <= 30,
  );
  const overdue = schedule.items.filter((i) => i.daysUntil < 0);
  return (
    <section className="schedule-banner">
      <span className="stat-icon peach">
        <CalendarClock size={25} />
      </span>
      <div>
        <h2>
          {close.length
            ? `${close.length} data(s) se aproximando`
            : overdue.length
              ? "Há datas para conferir com a UBS"
              : "De olho nas próximas doses"}
        </h2>
        <p>
          {close.length
            ? `${close[0].dependent} • ${close[0].vaccine}, dose ${close[0].dose} • ${formatDate(close[0].dueDate)}${close.length > 1 ? " e outras datas da família." : "."}`
            : overdue.length
              ? `${overdue.length} data(s) recomendada(s) já passaram no histórico disponível. Confira com a equipe.`
              : "Consulte a agenda por pessoa e acompanhe as datas recomendadas."}
        </p>
      </div>
      <button className="text-link" onClick={open}>
        Ver agenda <ArrowRight size={16} />
      </button>
    </section>
  );
}

export default function FamilySchedule({ schedule, people, openHistory }) {
  const [person, setPerson] = useState("todos"),
    [status, setStatus] = useState("todos");
  const items = schedule.items.filter(
    (i) =>
      (person === "todos" || i.dependentId === person) &&
      (status === "todos" || i.status === status),
  );
  return (
    <>
      <Section
        title="Próximas doses da família"
        description="Datas de rotina e datas individualizadas pela UBS."
      >
        <div className="table-toolbar">
          <Field label="Pessoa da família">
            <select value={person} onChange={(e) => setPerson(e.target.value)}>
              <option value="todos">Toda a família</option>
              {people.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quando">
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="todos">Todas as datas</option>
              <option value="proxima">Nos próximos 30 dias</option>
              <option value="atrasada">Data recomendada já passou</option>
              <option value="prevista">Mais adiante</option>
            </select>
          </Field>
        </div>
        {!schedule.coverage.valid && (
          <p className="form-error agenda-message" role="alert">
            As regras automáticas precisam de atualização para a data atual.
            Datas individualizadas pela UBS continuam visíveis.
          </p>
        )}
        {items.length ? (
          <div className="schedule-list">
            {items.map((i) => (
              <article
                className={`schedule-item ${i.status}`}
                key={i.dependentId + i.ruleId}
              >
                <div className="date-tile">
                  <strong>{i.dueDate.slice(8)}</strong>
                  <span>
                    {new Intl.DateTimeFormat("pt-BR", {
                      month: "short",
                      timeZone: "UTC",
                    }).format(new Date(i.dueDate + "T12:00:00Z"))}
                  </span>
                </div>
                <div className="schedule-copy">
                  <span className="eyebrow">{i.dependent}</span>
                  <h3>
                    {i.vaccine} <span>• Dose {i.dose}</span>
                  </h3>
                  <p>
                    <Clock3 size={13} />
                    {i.daysUntil === 0
                      ? "Data recomendada: hoje"
                      : i.daysUntil > 0
                        ? `Em ${i.daysUntil} dia(s) • ${formatDate(i.dueDate)}`
                        : `Data recomendada há ${-i.daysUntil} dia(s) • ${formatDate(i.dueDate)}`}
                  </p>
                  {i.sourceType === "ubs" && (
                    <small>Data definida pela UBS • {i.note}</small>
                  )}
                  {i.hasCandidate && (
                    <small>Existe informação a conferir pela UBS.</small>
                  )}
                </div>
                <div className="schedule-side">
                  <span
                    className={`badge ${i.status === "proxima" ? "a_conferir" : i.status === "atrasada" ? "rejeitado" : ""}`}
                  >
                    {i.status === "proxima"
                      ? "Próxima data"
                      : i.status === "atrasada"
                        ? "Conferir com a UBS"
                        : "Prevista"}
                  </span>
                  <button
                    className="text-link"
                    onClick={() => openHistory(i.dependentId)}
                  >
                    Ver acompanhamento <ArrowRight size={14} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty title="Nenhuma data neste filtro">
            A agenda cobre apenas as regras configuradas. A ausência de avisos
            não comprova situação vacinal completa.
          </Empty>
        )}
      </Section>
      <details className="notice-box">
        <summary>Como estas datas são calculadas?</summary>
        <strong>O que significa “data recomendada”?</strong>
        <p>
          É a data prevista no esquema de rotina, calculada pela idade e pelos
          registros confirmados. Não é a validade de uma vacina ou de um lote. A
          equipe deve conferir doses já recebidas, intervalos, condições
          especiais e orientar o próximo passo.
        </p>
        <p>
          Vacinas avaliadas automaticamente:{" "}
          {schedule.coverage.vaccines.join(", ") || "não disponível"}. Versão:{" "}
          {schedule.coverage.version || "não configurada"}. Outras vacinas
          continuam dependendo da avaliação da UBS.
        </p>
        {schedule.coverage.source && (
          <p>
            <a href={schedule.coverage.source} target="_blank" rel="noreferrer">
              Consultar a fonte do Ministério da Saúde
            </a>
          </p>
        )}
      </details>
    </>
  );
}
