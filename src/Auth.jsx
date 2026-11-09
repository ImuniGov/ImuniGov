import { useEffect, useState } from "react";
import { ArrowRight, ShieldCheck, Check } from "lucide-react";
import { api, setCsrf } from "./api";
import { Field, Privacy } from "./components";

export default function Auth({ onLogin }) {
  const [register, setRegister] = useState(false),
    [privacy, setPrivacy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    api("/api/v1/privacy/notice")
      .then(setNotice)
      .catch((err) => setError(err.message));
  }, []);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(e.currentTarget);
    const body = {
      email: form.get("email"),
      password: form.get("password"),
      ...(register
        ? {
            name: form.get("name"),
            consent: form.get("consent") === "on",
            healthConsent: form.get("healthConsent") === "on",
            adultDeclaration: form.get("adultDeclaration") === "on",
            termsVersion: notice?.version,
            privacyHash: notice?.hash,
          }
        : {}),
    };
    try {
      const result = await api(
        `/api/v1/auth/${register ? "register" : "login"}`,
        { method: "POST", body: JSON.stringify(body) },
      );
      setCsrf(result.csrf);
      onLogin(result.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <div className="auth-story">
        <a className="brand" href="/">
          <span className="brand-icon">✳</span>
          <span>
            imuni<span className="brand-light">guia</span>
          </span>
        </a>
        <div className="story-copy">
          <span className="eyebrow light">ACOMPANHAMENTO DA VACINAÇÃO</span>
          <h1>A caderneta da família, organizada.</h1>
          <p>
            Envie uma foto ou PDF. A equipe da UBS confere as informações e
            orienta os próximos passos.
          </p>
          <div className="story-pills">
            <span>
              <Check size={16} /> Acompanhamento da família
            </span>
            <span>
              <Check size={16} /> Conferência pela equipe de saúde
            </span>
          </div>
        </div>
      </div>
      <main className="auth-main">
        <div className="auth-card">
          <span className="eyebrow">IMUNIGUIA</span>
          <h2>{register ? "Criar conta de família" : "Entrar no ImuniGuia"}</h2>
          <p className="muted">
            {register
              ? "Crie sua conta de família para começar o acompanhamento."
              : "Acesse as cadernetas, as próximas doses e os retornos da UBS."}
          </p>
          <form onSubmit={submit}>
            <fieldset disabled={busy}>
              {register && (
                <Field
                  label="Seu nome"
                  name="name"
                  autoComplete="name"
                  minLength={2}
                  maxLength={80}
                  required
                />
              )}
              <Field
                label="E-mail"
                type="email"
                name="email"
                autoComplete="email"
                maxLength={254}
                placeholder="voce@exemplo.com"
                required
              />
              <Field
                label="Senha"
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                minLength={register ? 12 : 1}
                maxLength={128}
                placeholder={
                  register ? "Pelo menos 12 caracteres" : "Sua senha"
                }
                required
              />
              {register && (
                <div className="consent-fields">
                  <p>
                    <button
                      type="button"
                      className="inline-link"
                      onClick={() => setPrivacy(true)}
                    >
                      Ler os termos de uso e o aviso de privacidade
                    </button>
                  </p>
                  <p className="small">
                    Responsável: {notice?.controller || "carregando…"}. Versão{" "}
                    {notice?.version || "…"}.
                  </p>
                  <label className="checkbox">
                    <input name="consent" type="checkbox" required />
                    <span>Li e aceito os termos de uso.</span>
                  </label>
                  <label className="checkbox">
                    <input name="healthConsent" type="checkbox" required />
                    <span>
                      Autorizo o tratamento dos dados de saúde para organizar
                      cadernetas, realizar a leitura automática e permitir a
                      conferência pela equipe de saúde, conforme o aviso.
                    </span>
                  </label>
                  <label className="checkbox">
                    <input name="adultDeclaration" type="checkbox" required />
                    <span>
                      Tenho 18 anos ou mais. Cadastrarei apenas meus dados ou os
                      de pessoas que posso legalmente representar.
                    </span>
                  </label>
                  <p className="small muted">
                    Os avisos no aparelho são opcionais. O atendimento pelo SUS
                    não depende deste cadastro.
                  </p>
                </div>
              )}
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button
                className="primary full"
                type="submit"
                disabled={register && !notice}
              >
                {busy
                  ? "Aguarde…"
                  : register
                    ? "Criar minha conta"
                    : "Entrar na minha conta"}
                <ArrowRight size={18} />
              </button>
            </fieldset>
          </form>
          <p className="switch-auth">
            {register ? "Já tem uma conta?" : "É sua primeira visita?"}{" "}
            <button
              className="inline-link"
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "Entrar" : "Criar conta de família"}
            </button>
          </p>
          <div className="auth-trust">
            <ShieldCheck size={18} />
            <span>Seu acesso é privado e protegido.</span>
          </div>
          <p className="small muted">
            Equipe de saúde: solicite sua conta ao administrador da unidade.
          </p>
        </div>
        <footer>
          ImuniGuia • Cuidado em cada etapa{" "}
          <button className="inline-link" onClick={() => setPrivacy(true)}>
            Privacidade
          </button>
        </footer>
      </main>
      {privacy && <Privacy onClose={() => setPrivacy(false)} />}
    </div>
  );
}
