import {
  ArrowRight,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Empty, Field, Section } from "./components";
import { formatDate, today, vaccineLabel } from "./format";

const monthName = new Intl.DateTimeFormat("pt-BR", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const shortMonth = new Intl.DateTimeFormat("pt-BR", {
  month: "short",
  timeZone: "UTC",
});

const statuses = {
  proxima: "Nos próximos 30 dias",
  atrasada: "Data já passou",
  prevista: "Mais adiante",
};

export function ScheduleSummary({ schedule, open }) {
  const next = schedule.items.find((item) => item.daysUntil >= 0);
  const overdue = schedule.items.some((item) => item.daysUntil < 0);
  return (
    <section className="schedule-banner">
      <span className="stat-icon peach">
        <CalendarClock size={25} />
      </span>
      <div>
        <h2>
          {next
            ? "Próxima dose"
            : overdue
              ? "Datas para conferir"
              : "Calendário de vacinação"}
        </h2>
        {next && (
          <p>
            {next.dependent} · {vaccineLabel(next.vaccine)} ·{" "}
            {formatDate(next.dueDate)}
          </p>
        )}
        {!next && overdue && <p>Veja as datas que já passaram.</p>}
      </div>
      <button className="text-link" onClick={open}>
        Ver calendário <ArrowRight size={16} />
      </button>
    </section>
  );
}

export default function FamilySchedule({
  schedule,
  people,
  openHistory,
  route,
}) {
  const currentMonth = today().slice(0, 7);
  const person = route.query.get("pessoa") || "todos";
  const status = route.query.get("quando") || "todos";
  const monthParam = route.query.get("mes");
  const month =
    monthParam === "todos" || /^\d{4}-(0[1-9]|1[0-2])$/.test(monthParam)
      ? monthParam
      : currentMonth;
  const visible = schedule.items.filter(
    (item) =>
      (person === "todos" || item.dependentId === person) &&
      (status === "todos" || item.status === status),
  );
  const monthItems = visible.filter(
    (item) => month === "todos" || item.dueDate.startsWith(month),
  );
  const dayParam = route.query.get("dia");
  const day =
    /^\d{4}-\d{2}-(0[1-9]|[12]\d|3[01])$/.test(dayParam) &&
    dayParam.startsWith(month + "-")
      ? dayParam
      : "";
  const items = day
    ? monthItems.filter((item) => item.dueDate === day)
    : monthItems;
  const groups = new Map();
  for (const item of items) {
    const key = item.dueDate.slice(0, 7);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  const overdue = schedule.items.some(
    (item) =>
      item.daysUntil < 0 && (person === "todos" || item.dependentId === person),
  );
  function moveMonth(offset) {
    const date = new Date(
      (month === "todos" ? currentMonth : month) + "-01T12:00:00Z",
    );
    date.setUTCMonth(date.getUTCMonth() + offset);
    route.setFilter("mes", date.toISOString().slice(0, 7), currentMonth);
  }
  return (
    <>
      <Section title="Datas recomendadas" className="vaccination-calendar">
        <div className="calendar-filters">
          <Field label="Pessoa">
            <select
              value={person}
              onChange={(event) =>
                route.setFilter("pessoa", event.target.value, "todos")
              }
            >
              <option value="todos">Todos</option>
              {people.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quando">
            <select
              value={status}
              onChange={(event) =>
                route.setFilter("quando", event.target.value, "todos")
              }
            >
              <option value="todos">Todas</option>
              <option value="proxima">Até 30 dias</option>
              <option value="atrasada">Passadas</option>
              <option value="prevista">Mais tarde</option>
            </select>
          </Field>
        </div>
        {!schedule.coverage.valid && (
          <p className="form-error" role="alert">
            As datas automáticas precisam de atualização. As datas marcadas pela
            unidade continuam visíveis.
          </p>
        )}
        {overdue && status !== "atrasada" && (
          <div className="calendar-selection">
            <button
              className="text-link"
              onClick={() => {
                const query = new URLSearchParams(route.query);
                query.set("quando", "atrasada");
                query.set("mes", "todos");
                query.delete("dia");
                route.open(["filtros"], { query });
              }}
            >
              Datas que já passaram
            </button>
          </div>
        )}
        {overdue && status === "atrasada" && (
          <p className="calendar-tip">
            Já tomou uma dessas doses? Leve a caderneta à unidade de saúde para
            conferir.
          </p>
        )}
        <div className="calendar-controls">
          <div className="calendar-month">
            <button
              className="icon-button"
              type="button"
              aria-label="Mês anterior"
              onClick={() => moveMonth(-1)}
            >
              <ChevronLeft size={21} />
            </button>
            <strong aria-live="polite">
              {month === "todos"
                ? "Todos os meses"
                : monthName.format(new Date(month + "-01T12:00:00Z"))}
            </strong>
            <button
              className="icon-button"
              type="button"
              aria-label="Próximo mês"
              onClick={() => moveMonth(1)}
            >
              <ChevronRight size={21} />
            </button>
          </div>
          <button
            className="text-link"
            type="button"
            onClick={() =>
              route.setFilter(
                "mes",
                month === "todos" ? currentMonth : "todos",
                currentMonth,
              )
            }
          >
            {month === "todos" ? "Voltar ao mês atual" : "Todos os meses"}
          </button>
        </div>
        {month !== "todos" && (
          <MonthGrid
            month={month}
            items={monthItems}
            selected={day}
            onSelect={(date) =>
              route.setFilter("dia", date === day ? "" : date, "")
            }
          />
        )}
        {day && (
          <div className="calendar-selection">
            <strong>{formatDate(day)}</strong>
            <button
              className="text-link"
              onClick={() => route.setFilter("dia", "", "")}
            >
              Mostrar o mês todo
            </button>
          </div>
        )}
        {items.length ? (
          [...groups].map(([group, doses]) => (
            <section
              className="calendar-group"
              key={group}
              aria-label={monthName.format(new Date(group + "-01T12:00:00Z"))}
            >
              {month === "todos" && (
                <h3>{monthName.format(new Date(group + "-01T12:00:00Z"))}</h3>
              )}
              <div className="schedule-list">
                {doses.map((dose) => (
                  <article
                    className={`schedule-item ${dose.status}`}
                    key={dose.dependentId + dose.ruleId}
                  >
                    <time
                      className="date-tile"
                      dateTime={dose.dueDate}
                      aria-label={formatDate(dose.dueDate)}
                    >
                      <strong>{dose.dueDate.slice(8)}</strong>
                      <span>
                        {shortMonth.format(
                          new Date(dose.dueDate + "T12:00:00Z"),
                        )}
                      </span>
                    </time>
                    <div className="schedule-copy">
                      <p>{dose.dependent}</p>
                      <h3>{vaccineLabel(dose.vaccine)}</h3>
                      <p>
                        Dose {dose.dose}
                        {dose.sourceType === "ubs" && " · Data da UBS"}
                      </p>
                      {dose.note && <small>{dose.note}</small>}
                      {dose.hasCandidate && (
                        <small>Há um registro para a unidade conferir.</small>
                      )}
                    </div>
                    <div className="schedule-side">
                      <span
                        className={`badge ${dose.status === "proxima" ? "a_conferir" : dose.status === "atrasada" ? "rejeitado" : ""}`}
                      >
                        {dose.daysUntil === 0 ? "Hoje" : statuses[dose.status]}
                      </span>
                      <button
                        className="text-link"
                        onClick={() => openHistory(dose.dependentId)}
                      >
                        Ver vacinas <ArrowRight size={14} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))
        ) : (
          <Empty title="Nenhuma data neste período">
            Mude o mês ou os filtros para consultar outras datas.
          </Empty>
        )}
      </Section>
      <details className="notice-box">
        <summary>De onde vêm as datas?</summary>
        <p>
          A unidade de saúde pode marcar datas. O sistema também sugere datas
          para algumas vacinas, com base na idade e nas doses confirmadas. A
          unidade pode conferir se falta alguma dose.
        </p>
        <p>
          Vacinas com cálculo automático:{" "}
          {schedule.coverage.vaccines.map(vaccineLabel).join(", ") ||
            "lista indisponível"}
          . Versão {schedule.coverage.version || "indisponível"}.
        </p>
        {schedule.coverage.source && (
          <a href={schedule.coverage.source} target="_blank" rel="noreferrer">
            Calendário do Ministério da Saúde
          </a>
        )}
      </details>
    </>
  );
}

const weekdays = [
  ["D", "domingo"],
  ["S", "segunda-feira"],
  ["T", "terça-feira"],
  ["Q", "quarta-feira"],
  ["Q", "quinta-feira"],
  ["S", "sexta-feira"],
  ["S", "sábado"],
];

function MonthGrid({ month, items, selected, onSelect }) {
  const start = new Date(month + "-01T12:00:00Z");
  const end = new Date(start);
  end.setUTCMonth(end.getUTCMonth() + 1, 0);
  const datesWithDoses = new Set(items.map((item) => item.dueDate));
  const todayDate = today();
  return (
    <div className="month-grid" aria-label="Dias do mês">
      {weekdays.map(([label, name]) => (
        <abbr key={name} title={name}>
          {label}
        </abbr>
      ))}
      {Array.from({ length: start.getUTCDay() }, (_, index) => (
        <span aria-hidden="true" key={"empty-" + index} />
      ))}
      {Array.from({ length: end.getUTCDate() }, (_, index) => {
        const day = index + 1;
        const date = month + "-" + String(day).padStart(2, "0");
        return datesWithDoses.has(date) ? (
          <button
            type="button"
            key={date}
            aria-pressed={selected === date}
            aria-current={todayDate === date ? "date" : undefined}
            aria-label={formatDate(date) + ", ver doses"}
            onClick={() => onSelect(date)}
          >
            {day}
          </button>
        ) : (
          <span
            key={date}
            aria-current={todayDate === date ? "date" : undefined}
          >
            {day}
          </span>
        );
      })}
    </div>
  );
}
