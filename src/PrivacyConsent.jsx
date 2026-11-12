import { useEffect, useState } from "react";
import { api, send } from "./api";
import { Privacy } from "./components";

export default function PrivacyConsent({ onAccepted, route }) {
  const [notice, setNotice] = useState(null);
  const reading = route.parts[0] === "termos-de-uso";
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    api("/api/v1/privacy/notice")
      .then(setNotice)
      .catch((e) => setError(e.message));
  }, []);
  async function submit(e) {
    e.preventDefault();
    const form = e.currentTarget,
      fields = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const result = await send("/api/v1/privacy/accept", {
        consent: fields.get("consent") === "on",
        healthConsent: fields.get("healthConsent") === "on",
        adultDeclaration: fields.get("adultDeclaration") === "on",
        termsVersion: notice.version,
        privacyHash: notice.hash,
      });
      onAccepted(result.user);
    } catch (e) {
      setError(e.message);
      if (e.status === 409) {
        form.reset();
        setNotice(await api("/api/v1/privacy/notice"));
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="notice-box" aria-labelledby="consent-heading">
      <h2 id="consent-heading">O acompanhamento digital está pausado</h2>
      <p>
        Para retomar, aceite os termos atuais e autorize o uso dos dados de
        saúde. Seus dados e pedidos continuam em Minha conta. O atendimento pelo
        SUS independe desta autorização.
      </p>
      <button
        className="text-link"
        onClick={() => route.open(["termos-de-uso"])}
      >
        Ler termos e aviso de privacidade
      </button>
      <form onSubmit={submit}>
        <fieldset disabled={busy || !notice}>
          <label className="checkbox">
            <input type="checkbox" name="consent" required />
            <span>
              Li e aceito os termos de uso, versão {notice?.version || "…"}.
            </span>
          </label>
          <label className="checkbox">
            <input type="checkbox" name="healthConsent" required />
            <span>
              Autorizo especificamente o uso dos dados de saúde para organizar
              as cadernetas, realizar a leitura automática e permitir a
              conferência pela equipe, conforme o aviso.
            </span>
          </label>
          <label className="checkbox">
            <input type="checkbox" name="adultDeclaration" required />
            <span>
              Tenho 18 anos ou mais e cadastrei apenas meus dados ou de pessoas
              que posso legalmente representar.
            </span>
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" type="submit">
            {busy ? "Registrando…" : "Autorizar e retomar acompanhamento"}
          </button>
        </fieldset>
      </form>
      {reading && <Privacy onClose={route.close} />}
    </section>
  );
}
