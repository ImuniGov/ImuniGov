import { useCallback, useEffect, useState } from "react";
import { api, send } from "./api";
import { Field } from "./components";
import { formatDate } from "./format";

export default function PrivacyRights({ act, busy, onError, onPrivacyChange }) {
  const [items, setItems] = useState([]),
    [acceptances, setAcceptances] = useState([]);
  const refresh = useCallback(async () => {
    const result = await api("/api/v1/privacy/requests");
    setItems(result.items);
    setAcceptances(result.acceptances);
  }, []);
  useEffect(() => {
    Promise.resolve().then(refresh).catch(onError);
  }, [refresh, onError]);
  async function submit(e) {
    e.preventDefault();
    const form = e.currentTarget,
      body = Object.fromEntries(new FormData(form));
    if (
      await act(
        () => send("/api/v1/privacy/requests", body),
        "Solicitação recebida. Acompanhe a resposta nesta área.",
      )
    ) {
      form.reset();
      await refresh();
      if (body.kind === "revogacao") onPrivacyChange?.();
    }
  }
  return (
    <div className="rights-form">
      <h3>Seus dados e seus direitos</h3>
      <p>
        Você pode pedir acesso, correção, exclusão ou revogação da autorização.
        O responsável analisará o pedido e informará eventuais dados que
        precisem ser conservados por lei.
      </p>
      <details>
        <summary>Fazer uma solicitação sobre meus dados</summary>
        <form onSubmit={submit}>
          <fieldset disabled={busy}>
            <Field label="O que você precisa?">
              <select name="kind" required>
                <option value="acesso">Acessar meus dados</option>
                <option value="correcao">Corrigir informações</option>
                <option value="eliminacao">Solicitar exclusão</option>
                <option value="revogacao">
                  Revogar autorização e pausar acompanhamento
                </option>
                <option value="informacao">
                  Saber como meus dados são usados
                </option>
                <option value="outro">Outro pedido</option>
              </select>
            </Field>
            <Field label="Descreva seu pedido">
              <textarea
                name="message"
                required
                minLength={3}
                maxLength={1000}
                rows={3}
              />
            </Field>
            <p className="small muted">
              Não envie senha ou documentos pessoais neste campo.
            </p>
            <button className="secondary" type="submit">
              Enviar solicitação
            </button>
          </fieldset>
        </form>
      </details>
      {items.map((i) => (
        <div className="feedback-entry" key={i.id}>
          <strong>
            Pedido {i.id.slice(0, 8)} ·{" "}
            {i.status === "respondida" ? "Respondido" : "Recebido"}
          </strong>
          <p>{i.message}</p>
          {i.response && (
            <p>
              <strong>Resposta:</strong> {i.response}
            </p>
          )}
          <small>{formatDate(i.created_at)}</small>
        </div>
      ))}
      <details>
        <summary>Consultar meus aceites</summary>
        {acceptances.length ? (
          acceptances.map((i) => (
            <p key={i.id}>
              Termos e autorização para dados de saúde · versão {i.version} ·{" "}
              {formatDate(i.accepted_at)}
            </p>
          ))
        ) : (
          <p>
            Esta conta é anterior ao novo termo. Nenhum aceite foi criado em seu
            nome.
          </p>
        )}
      </details>
    </div>
  );
}
