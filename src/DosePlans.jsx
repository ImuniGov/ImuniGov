import { useCallback, useEffect, useState } from "react";
import { api, send } from "./api";
import { Empty, Field, RouteDetails, Section } from "./components";
import { useVaccineCatalog } from "./useVaccineCatalog";
import { formatDate, vaccineLabel } from "./format";

export default function DosePlans({
  selected,
  user,
  act,
  busy,
  onError,
  route,
}) {
  const [plans, setPlans] = useState([]);
  const { names: vaccines, catalog } = useVaccineCatalog();
  const refresh = useCallback(async () => {
    if (selected)
      setPlans((await api(`/api/v1/dependents/${selected}/dose-plans`)).items);
  }, [selected]);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
  }, [refresh, onError]);
  async function create(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.dose = Number(data.dose);
    if (
      await act(
        () => send(`/api/v1/dependents/${selected}/dose-plans`, data),
        "Data de acompanhamento registrada.",
      )
    ) {
      form.reset();
      await refresh();
    }
  }
  async function cancel(e, plan) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget));
    if (
      await act(
        () => send(`/api/v1/dose-plans/${plan.id}/cancel`, data),
        "Data cancelada, com histórico preservado.",
      )
    )
      await refresh();
  }
  if (!selected) return null;
  return (
    <Section title="Datas definidas pela UBS">
      {plans.length ? (
        plans.map((plan) => (
          <article className="guidance-card" key={plan.id}>
            <div className="section-heading plan-heading">
              <div>
                <h3>
                  {vaccineLabel(plan.vaccine)} • Dose {plan.dose}
                </h3>
                <p>{formatDate(plan.due_date)} • Definida pela UBS</p>
              </div>
              <span
                className={`badge ${plan.status === "ativa" ? "a_conferir" : plan.status === "concluida" ? "validado" : ""}`}
              >
                {plan.status === "ativa"
                  ? "Acompanhar"
                  : plan.status === "concluida"
                    ? "Registro confirmado"
                    : "Cancelada"}
              </span>
            </div>
            <p>{plan.note}</p>
            {user.role === "ubs" && plan.status === "ativa" && (
              <RouteDetails
                route={route}
                parent={["pessoa", selected]}
                path={["pessoa", selected, "cancelar-data", plan.id]}
                title="Cancelar ou substituir esta data"
              >
                <form onSubmit={(e) => cancel(e, plan)}>
                  <fieldset disabled={busy}>
                    <Field label="Motivo do cancelamento">
                      <textarea
                        name="note"
                        minLength={3}
                        maxLength={500}
                        required
                        rows={2}
                      />
                    </Field>
                    <button className="secondary danger-text" type="submit">
                      Cancelar esta data
                    </button>
                  </fieldset>
                </form>
              </RouteDetails>
            )}
          </article>
        ))
      ) : (
        <Empty title="Nenhuma data individual registrada">
          As datas de rotina continuam na agenda da família. A UBS pode
          complementar o acompanhamento.
        </Empty>
      )}
      {user.role === "ubs" && (
        <RouteDetails
          className="plan-create"
          route={route}
          parent={["pessoa", selected]}
          path={["pessoa", selected, "definir-proxima-data"]}
          title="Definir uma próxima data"
        >
          <form onSubmit={create}>
            <fieldset disabled={busy}>
              <Field label="Vacina">
                <input
                  name="vaccine"
                  list="plan-vaccines"
                  minLength={2}
                  maxLength={80}
                  placeholder="Selecione ou escreva a vacina"
                  required
                />
                <datalist id="plan-vaccines">
                  {vaccines
                    .filter((v) => v !== "Outro registro")
                    .map((v) => (
                      <option value={v} key={v} />
                    ))}
                </datalist>
              </Field>
              {catalog && (
                <p className="small muted">
                  Nomes de vacinas:{" "}
                  <a href={catalog.source} target="_blank" rel="noreferrer">
                    catálogo público da RNDS
                  </a>
                  , versão {catalog.version}. O catálogo identifica vacinas; a
                  data é definida pela UBS.
                </p>
              )}
              <div className="form-grid">
                <Field
                  label="Número da próxima dose"
                  type="number"
                  name="dose"
                  min="1"
                  max="10"
                  defaultValue="1"
                  required
                />
                <Field
                  label="Data recomendada pela UBS"
                  type="date"
                  name="dueDate"
                  min="1900-01-01"
                  required
                />
              </div>
              <Field label="Orientação sobre esta data">
                <textarea
                  name="note"
                  rows={3}
                  minLength={3}
                  maxLength={500}
                  required
                />
              </Field>
              <button className="primary" type="submit">
                Salvar próxima data
              </button>
            </fieldset>
          </form>
        </RouteDetails>
      )}
    </Section>
  );
}
