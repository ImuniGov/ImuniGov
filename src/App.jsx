import { useCallback, useEffect, useRef, useState } from "react";
import {
  CalendarClock,
  ArrowRight,
  Bell,
  ChevronRight,
  ClipboardCheck,
  FileText,
  Heart,
  Home,
  LogOut,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import Auth from "./Auth";
import FamilyReturns from "./FamilyReturns";
import PrivacyConsent from "./PrivacyConsent";
import PrivacyRights from "./PrivacyRights";
import FamilySchedule, { ScheduleSummary } from "./FamilySchedule";
import PwaPanel from "./PwaPanel";
import { disablePush } from "./pwa";
import { FeedbackContext } from "./feedback";
import { api, send, setCsrf } from "./api";
import {
  AddButton,
  Badge,
  Empty,
  Field,
  Modal,
  Privacy,
  Section,
} from "./components";
import { formatDate, today, vaccineLabel } from "./format";
import { profilePath, profileRoute, useLocation } from "./navigation";
import {
  UploadForm,
  DocumentReview,
  FamilyHistory,
  Outreach,
  AgentGuide,
} from "./Workspaces";

const roles = {
  familia: "Família",
  ubs: "Equipe da UBS",
  acs: "Agente comunitário",
};
const tabs = {
  home: "Visão geral",
  family: "Minha família",
  schedule: "Calendário de vacinação",
  documents: "Cadernetas",
  history: "Vacinas e orientações",
  review: "Conferir cadernetas",
  outreach: "Contatos com famílias",
  notifications: "Avisos",
  account: "Minha conta",
};

export default function App() {
  const [user, setUser] = useState(null);
  const [starting, setStarting] = useState(true);
  const [location, go] = useLocation();
  const page = user ? profileRoute(user, location) : null;
  const tab = page?.tab;
  const allowed = page?.allowed;
  const [people, setPeople] = useState([]),
    [documents, setDocuments] = useState([]),
    [notes, setNotes] = useState([]);
  const [schedule, setSchedule] = useState({
    items: [],
    coverage: { valid: true, vaccines: [] },
  });
  const [cases, setCases] = useState([]);
  const [loadedFor, setLoadedFor] = useState(null);
  const [nextReview, setNextReview] = useState(null);
  const currentUser = useRef(null);
  const changeUser = useCallback((next) => {
    currentUser.current = next;
    setUser(next);
    setPeople([]);
    setDocuments([]);
    setNotes([]);
    setCases([]);
    setLoadedFor(null);
    setNextReview(null);
    setSchedule({ items: [], coverage: { valid: true, vaccines: [] } });
  }, []);
  const [toast, setToast] = useState(null),
    [busy, setBusy] = useState(false),
    [menu, setMenu] = useState(false);
  const showError = useCallback(
    (err) => setToast({ text: err.message || String(err), error: true }),
    [setToast],
  );
  useEffect(() => {
    let alive = true;
    api("/api/v1/me")
      .then((r) => {
        if (alive) {
          setCsrf(r.csrf);
          changeUser(r.user);
        }
      })
      .catch((err) => {
        if (err.status !== 401 && alive) showError(err);
      })
      .finally(() => {
        if (alive) setStarting(false);
      });
    const expired = () => {
      changeUser(null);
      setToast({ text: "Sua sessão terminou. Entre novamente.", error: true });
    };
    window.addEventListener("session-expired", expired);
    return () => {
      alive = false;
      window.removeEventListener("session-expired", expired);
    };
  }, [showError, changeUser]);
  const reload = useCallback(async () => {
    if (!user) return;
    const result = await Promise.all([
      user.role !== "acs"
        ? api("/api/dependents")
        : Promise.resolve({ items: [] }),
      user.role !== "acs"
        ? api("/api/documents")
        : Promise.resolve({ items: [] }),
      api("/api/v1/notifications"),
      user.role === "familia"
        ? api("/api/v1/family/schedule")
        : Promise.resolve(null),
      user.role === "acs"
        ? api("/api/v1/acs/cases")
        : Promise.resolve({ items: [] }),
      user.role === "ubs"
        ? api("/api/v1/review/next")
        : Promise.resolve({ item: null }),
    ]).catch((error) => {
      if (currentUser.current?.id !== user.id) return null;
      throw error;
    });
    if (!result || currentUser.current?.id !== user.id) return;
    setPeople(result[0].items);
    setDocuments(result[1].items);
    setNotes(result[2].items);
    if (result[3]) setSchedule(result[3]);
    setCases(result[4].items);
    setNextReview(result[5].item);
    setLoadedFor(user.id);
  }, [user]);
  useEffect(() => {
    Promise.resolve().then(reload).catch(showError);
  }, [reload, showError]);
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(() => reload().catch(showError), 15000);
    return () => clearInterval(interval);
  }, [user, reload, showError]);
  useEffect(() => {
    if (!toast || toast.error) return;
    const timer = setTimeout(() => setToast(null), 5500);
    return () => clearTimeout(timer);
  }, [toast]);
  async function act(action, message, refresh = true) {
    if (busy) return;
    setBusy(true);
    try {
      await action();
      if (refresh) await reload();
      if (message) setToast({ text: message });
      return true;
    } catch (err) {
      showError(err);
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    await act(
      async () => {
        await disablePush().catch(() => {});
        await send("/api/v1/auth/logout", {});
        setCsrf("");
        changeUser(null);
        setPeople([]);
        setDocuments([]);
        setNotes([]);
        go("/entrar", { replace: true });
        setMenu(false);
      },
      undefined,
      false,
    );
  }
  useEffect(() => {
    if (user && !allowed) {
      go(profilePath(user, tab), { replace: true });
    } else if (
      !starting &&
      !user &&
      location.path === "/" &&
      !location.query.has("view")
    ) {
      go("/entrar", { replace: true });
    }
  }, [user, allowed, tab, go, starting, location]);

  const navigate = (key, parts = []) => {
    go(profilePath(user, key, parts));
    setMenu(false);
    document.getElementById("conteudo")?.focus();
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const [action, id, step] = page?.parts || [];
  const selectedId =
    (action === "pessoa" ? id : page?.query.get("pessoa")) || "";
  const selected =
    people.find((p) => p.id === selectedId)?.id ||
    (action === "pessoa" ? "" : people[0]?.id || "");
  const search =
    page?.state?.owner === user?.id ? page?.state?.search || "" : "";
  function open(
    parts,
    { query = page.query, replace = false, state = page.state } = {},
  ) {
    go(profilePath(user, tab, parts, query), { replace, state });
  }
  const route = page && {
    ...page,
    open,
    search,
    setFilter(key, value, fallback) {
      const query = new URLSearchParams(page.query);
      if (value === fallback) query.delete(key);
      else query.set(key, value);
      open([search ? "busca" : query.size ? "filtros" : ""], { query });
    },
    setSearch(value) {
      open([value ? "busca" : page.query.size ? "filtros" : ""], {
        state: { owner: user.id, search: value },
        replace: action === "busca",
      });
    },
    close() {
      open(
        search
          ? ["busca"]
          : tab === "history" && selected
            ? ["pessoa", selected]
            : page.query.size
              ? ["filtros"]
              : [],
        { replace: true },
      );
    },
  };
  const filter = route?.query.get("situacao") || "todos";
  const follow = (key) => (event) => {
    if (
      event.button ||
      event.ctrlKey ||
      event.metaKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    navigate(key);
  };
  const openHistory = (id) => navigate("history", ["pessoa", id]);
  const upload = (id) => {
    const query = new URLSearchParams(page.query);
    if (tab === "history" && selected) query.set("pessoa", selected);
    open(["enviar-caderneta", id], { query });
  };
  const person = people.find((p) => p.id === id);
  const queueRoute = tab === "review" && action === "conferir-caderneta";
  const archiveRoute = tab === "review" && action === "ver-conferencia";
  const documentRoute =
    queueRoute ||
    archiveRoute ||
    (tab === "documents" && action === "ver-caderneta");
  const archive =
    user?.role === "ubs"
      ? documents.filter(
          (item) =>
            item.status !== "pendente" ||
            item.review?.myVote ||
            item.reviewHold,
        )
      : [];
  const currentDocument =
    documentRoute &&
    (queueRoute
      ? nextReview?.id === id && documents.find((item) => item.id === id)
      : (archiveRoute ? archive : documents).find((item) => item.id === id));
  async function startReview() {
    await act(
      async () => {
        const { item } = await api("/api/v1/review/next");
        setNextReview(item);
        navigate(
          "review",
          item ? ["conferir-caderneta", item.id, item.step] : [],
        );
      },
      undefined,
      false,
    );
  }
  async function afterVote() {
    try {
      const { item } = await api("/api/v1/review/next");
      setNextReview(item);
      if (item?.id === id)
        route.open([action, id, item.step], { replace: true });
      else route.close();
    } catch (error) {
      showError(error);
    }
  }
  const unread = notes.filter((n) => !n.read).length;
  const pending = documents.filter((d) => d.status === "pendente").length;
  const shown = documents.filter(
    (d) =>
      (filter === "todos" || d.status === filter) &&
      `${d.dependent} ${d.fileName}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  if (starting)
    return (
      <div className="loading-screen">
        <span className="brand-icon">✳</span>
        <p>Carregando sua conta…</p>
      </div>
    );
  if (!user)
    return (
      <>
        <Auth
          location={location}
          go={go}
          onLogin={(u) => {
            changeUser(u);
            setToast(null);
          }}
        />
        {toast && (
          <div className="toast error" role="alert">
            {toast.text}
            <button onClick={() => setToast(null)} aria-label="Fechar aviso">
              <X size={18} />
            </button>
          </div>
        )}
      </>
    );
  const nav = [
    ["home", Home],
    ...(user.role === "familia"
      ? [
          ["family", Users],
          ["schedule", CalendarClock],
          ["documents", FileText],
          ["history", Heart],
        ]
      : user.role === "ubs"
        ? [
            ["review", ClipboardCheck],
            ["history", Heart],
            ["outreach", Users],
          ]
        : [["outreach", Users]]),
    ["notifications", Bell],
  ];
  return (
    <FeedbackContext.Provider value={toast}>
      <div className="app-shell">
        <a className="skip-link" href="#conteudo">
          Ir para o conteúdo
        </a>
        {menu && (
          <button
            className="menu-backdrop"
            aria-label="Fechar navegação"
            onClick={() => setMenu(false)}
          />
        )}
        <aside className={`sidebar ${menu ? "open" : ""}`}>
          <a
            className="brand"
            href={profilePath(user, "home")}
            onClick={follow("home")}
          >
            <span className="brand-icon">✳</span>
            <span>
              imuni<span className="brand-light">guia</span>
            </span>
          </a>
          <span className="sidebar-label">ACOMPANHAMENTO</span>
          <nav aria-label="Navegação principal">
            {nav.map(([key, Icon]) => (
              <a
                key={key}
                href={profilePath(user, key)}
                aria-current={tab === key ? "page" : undefined}
                className={tab === key ? "active" : ""}
                onClick={follow(key)}
              >
                <Icon size={19} />
                <span>{tabs[key]}</span>
                {key === "notifications" && unread > 0 && (
                  <b className="nav-count">{unread}</b>
                )}
                {key === "review" && pending > 0 && (
                  <b className="nav-count">{pending}</b>
                )}
              </a>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <a
              href={profilePath(user, "account")}
              aria-current={tab === "account" ? "page" : undefined}
              className={tab === "account" ? "active" : ""}
              onClick={follow("account")}
            >
              <Settings size={18} /> Minha conta
            </a>
            <button onClick={logout} disabled={busy}>
              <LogOut size={18} /> Sair
            </button>
            <span className="version">ImuniGuia • Homologação</span>
          </div>
        </aside>
        <div className="app-body">
          <header className="topbar">
            <div className="breadcrumb">
              <button
                className="icon-button mobile-menu"
                aria-label="Abrir navegação"
                aria-expanded={menu}
                onClick={() => setMenu(!menu)}
              >
                <Menu size={22} />
              </button>
              <span>ImuniGuia</span>
              <ChevronRight size={14} />
              <strong>{tabs[tab]}</strong>
            </div>
            <div className="header-actions">
              <button
                className="notification-button"
                aria-label={`Avisos: ${unread} não lidas`}
                onClick={() => navigate("notifications")}
              >
                <Bell size={19} />
                {unread > 0 && <i />}
              </button>
              <span className="avatar">{user.name.charAt(0)}</span>
              <div className="header-user">
                <strong>{user.name}</strong>
                <small>{roles[user.role]}</small>
              </div>
            </div>
          </header>
          <main className="main-content" id="conteudo" tabIndex={-1}>
            {user.role === "familia" && !user.privacy?.current && (
              <PrivacyConsent onAccepted={changeUser} route={route} />
            )}

            <div className="page-intro">
              <div>
                <h1>
                  {tab === "home"
                    ? `Olá, ${user.name.split(" ")[0]}.`
                    : tabs[tab]}
                </h1>
              </div>
              {user.role === "familia" && ["home", "family"].includes(tab) && (
                <AddButton onClick={() => route.open(["adicionar-pessoa"])}>
                  Adicionar pessoa
                </AddButton>
              )}
              {user.role === "familia" && tab === "documents" && (
                <AddButton onClick={() => upload()}>Enviar caderneta</AddButton>
              )}
            </div>
            <p className="demo-note">Demonstração · use dados fictícios</p>
            {tab === "home" && (
              <>
                {user.role === "familia" && (
                  <ScheduleSummary
                    schedule={schedule}
                    open={() => navigate("schedule")}
                  />
                )}
                {user.role === "familia" && (
                  <FamilyReturns
                    onlyRefused
                    onError={showError}
                    resend={upload}
                  />
                )}
                <div className="hero-card">
                  <div>
                    <h2>
                      {user.role === "familia"
                        ? "Cadernetas"
                        : user.role === "ubs"
                          ? "Fila de conferência"
                          : "Contatos com famílias"}
                    </h2>
                    <button
                      className="hero-button"
                      disabled={user.role === "ubs" && busy}
                      onClick={() =>
                        user.role === "familia"
                          ? documents.length
                            ? navigate("documents")
                            : route.open([
                                people.length
                                  ? "enviar-caderneta"
                                  : "adicionar-pessoa",
                              ])
                          : user.role === "ubs"
                            ? startReview()
                            : navigate("outreach")
                      }
                    >
                      {user.role === "familia"
                        ? documents.length
                          ? "Ver cadernetas"
                          : people.length
                            ? "Enviar caderneta"
                            : "Cadastrar pessoa"
                        : user.role === "ubs"
                          ? "Começar a conferir"
                          : "Ver contatos"}
                      <ArrowRight size={17} />
                    </button>
                  </div>
                </div>
                <details className="secondary-panel desktop-only">
                  <summary>Resumo</summary>
                  <div className="stats-grid">
                    {(user.role === "acs"
                      ? [
                          ["Casos ativos", cases.length, Users, "mint"],
                          [
                            "Alta prioridade",
                            cases.filter((c) => c.priority === "alta").length,
                            CalendarClock,
                            "peach",
                          ],
                          ["Novos avisos", unread, Bell, "lilac"],
                        ]
                      : [
                          [
                            user.role === "familia"
                              ? "Pessoas"
                              : "Pessoas na fila",
                            people.length,
                            Users,
                            "mint",
                          ],
                          ["Aguardando", pending, FileText, "peach"],
                          [
                            "Conferidos",
                            documents.filter((d) => d.status === "aprovado")
                              .length,
                            ClipboardCheck,
                            "blue",
                          ],
                          ["Novos avisos", unread, Bell, "lilac"],
                        ]
                    ).map(([title, count]) => (
                      <div className="stat-card" key={title}>
                        <span>{title}</span>
                        <strong>{count}</strong>
                      </div>
                    ))}
                  </div>
                </details>
                {user.role === "acs" ? (
                  <AgentGuide />
                ) : (
                  <div className="home-grid">
                    <Section
                      title={
                        user.role === "familia"
                          ? "Sua família"
                          : "Pessoas na fila"
                      }
                      action={
                        <button
                          className="text-link"
                          onClick={() =>
                            navigate(
                              user.role === "familia"
                                ? "family"
                                : user.role === "ubs"
                                  ? "review"
                                  : "outreach",
                            )
                          }
                        >
                          Ver tudo <ArrowRight size={15} />
                        </button>
                      }
                    >
                      {people.length ? (
                        <div className="person-list">
                          {people.slice(0, 4).map((p) => (
                            <button
                              className="person-row"
                              key={p.id}
                              onClick={() => openHistory(p.id)}
                            >
                              <span className="person-avatar">
                                {p.name.charAt(0)}
                              </span>
                              <span>
                                <strong>{p.name}</strong>
                              </span>
                              <ChevronRight size={18} />
                            </button>
                          ))}
                        </div>
                      ) : (
                        <Empty
                          title={
                            user.role === "ubs"
                              ? "Nenhuma caderneta atribuída"
                              : "Nenhuma pessoa cadastrada"
                          }
                          action={
                            <button
                              className="text-link"
                              onClick={() =>
                                user.role === "familia"
                                  ? route.open(["adicionar-pessoa"])
                                  : navigate("review")
                              }
                            >
                              {user.role === "familia"
                                ? "Cadastrar primeira pessoa"
                                : "Ver minha fila"}{" "}
                              <ArrowRight size={15} />
                            </button>
                          }
                        />
                      )}
                    </Section>
                    <details className="secondary-panel desktop-only">
                      <summary>
                        {user.role === "ubs"
                          ? "Como conferir"
                          : "Como funciona"}
                      </summary>
                      <ol className="task-list">
                        {(user.role === "ubs"
                          ? [
                              "Abra uma caderneta da fila.",
                              "Registre sua decisão sobre o arquivo.",
                              "Confira as doses.",
                            ]
                          : [
                              "Envie uma foto ou PDF.",
                              "Três profissionais conferem o arquivo e as doses.",
                              "Acompanhe o retorno da unidade.",
                            ]
                        ).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ol>
                    </details>
                  </div>
                )}
              </>
            )}
            {tab === "schedule" && user.role === "familia" && (
              <FamilySchedule
                schedule={schedule}
                people={people}
                openHistory={openHistory}
                route={route}
              />
            )}
            {tab === "family" && (
              <Section title="Pessoas cadastradas">
                {people.length ? (
                  <div className="family-grid">
                    {people.map((p) => (
                      <article className="family-card" key={p.id}>
                        <span className="person-avatar large">
                          {p.name.charAt(0)}
                        </span>
                        <h3>{p.name}</h3>
                        <p>Nascimento: {formatDate(p.birthDate)}</p>
                        <small>
                          {p.document_count} arquivo(s) enviado(s) •{" "}
                          {p.representationVerified
                            ? "Responsável verificado"
                            : "Responsável informado"}
                        </small>
                        <div className="button-row">
                          <button
                            className="secondary"
                            onClick={() => openHistory(p.id)}
                          >
                            Acompanhar <ArrowRight size={15} />
                          </button>
                          <button
                            className="text-link"
                            onClick={() => route.open(["editar-pessoa", p.id])}
                          >
                            Editar
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <Empty title="Nenhuma pessoa cadastrada">
                    Use “Adicionar pessoa” para cadastrar você ou um dependente.
                  </Empty>
                )}
              </Section>
            )}
            {tab === "review" && (
              <>
                <Section title="Próxima caderneta">
                  <div className="queue-action">
                    {loadedFor !== user.id ? (
                      <p role="status">Carregando…</p>
                    ) : nextReview ? (
                      <button
                        className="primary"
                        disabled={busy}
                        onClick={startReview}
                      >
                        Começar a conferir <ArrowRight size={17} />
                      </button>
                    ) : (
                      <p>Nenhuma caderneta disponível agora.</p>
                    )}
                  </div>
                </Section>
                {archive.length > 0 && (
                  <details className="secondary-panel">
                    <summary>Conferências anteriores</summary>
                    <ul className="review-archive">
                      {archive.map((entry) => (
                        <li key={entry.id}>
                          <button
                            className="person-row"
                            onClick={() =>
                              route.open([
                                "ver-conferencia",
                                entry.id,
                                "historico",
                              ])
                            }
                          >
                            <span>
                              <strong>{entry.dependent}</strong>
                              <small>{formatDate(entry.createdAt)}</small>
                            </span>
                            <Badge status={entry.status} />
                            <ChevronRight size={16} />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </>
            )}
            {tab === "documents" && (
              <Section title="Cadernetas enviadas" className="document-panel">
                <div className="table-toolbar">
                  <Field label="Situação">
                    <select
                      value={filter}
                      onChange={(e) =>
                        route.setFilter("situacao", e.target.value, "todos")
                      }
                    >
                      <option value="todos">Todas</option>
                      <option value="pendente">Aguardando</option>
                      <option value="aprovado">Conferidas</option>
                      <option value="rejeitado">Devolvidas</option>
                    </select>
                  </Field>
                  <label className="search">
                    <Search size={17} />
                    <input
                      aria-label="Buscar arquivos"
                      placeholder="Buscar arquivo"
                      value={search}
                      onChange={(e) => route.setSearch(e.target.value)}
                    />
                  </label>
                </div>
                {shown.length ? (
                  <div className="table-wrap document-table">
                    <table role="table" aria-label="Cadernetas">
                      <thead>
                        <tr>
                          <th scope="col">ARQUIVO / PESSOA</th>
                          <th scope="col">REGISTRO INFORMADO</th>
                          <th scope="col">RECEBIDO</th>
                          <th scope="col">SITUAÇÃO</th>
                          <th scope="col">AÇÕES</th>
                        </tr>
                      </thead>
                      <tbody role="rowgroup">
                        {shown.map((d) => (
                          <tr role="row" key={d.id}>
                            <td role="cell">
                              <div className="file-cell">
                                <span className="file-icon">
                                  <FileText size={21} />
                                </span>
                                <span>
                                  <strong>{d.fileName}</strong>
                                  <small>{d.dependent}</small>
                                </span>
                              </div>
                            </td>
                            <td role="cell" data-label="Vacina">
                              {vaccineLabel(d.vaccine)}
                            </td>
                            <td role="cell" data-label="Envio">
                              {formatDate(d.createdAt)}
                            </td>
                            <td role="cell">
                              <Badge status={d.status} />
                            </td>
                            <td role="cell">
                              <button
                                className="text-link"
                                onClick={() =>
                                  route.open(["ver-caderneta", d.id])
                                }
                              >
                                Detalhes
                                <ChevronRight size={16} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title={
                      search || filter !== "todos"
                        ? "Nenhum resultado neste filtro"
                        : "Ainda não há cadernetas"
                    }
                  >
                    {search || filter !== "todos"
                      ? "Tente outro nome ou situação."
                      : "Envie uma foto ou PDF da caderneta."}
                  </Empty>
                )}
              </Section>
            )}
            {tab === "history" && (
              <FamilyHistory
                resend={upload}
                key={selected}
                people={people}
                selected={selected}
                onSelect={openHistory}
                route={route}
                user={user}
                act={act}
                busy={busy}
                onError={showError}
              />
            )}
            {tab === "outreach" && (
              <Outreach
                route={route}
                user={user}
                act={act}
                busy={busy}
                onError={showError}
              />
            )}
            {tab === "notifications" && (
              <Section title="Seus avisos">
                {notes.length ? (
                  <div className="notification-list">
                    {notes.map((n) => (
                      <article className={n.read ? "read" : ""} key={n.id}>
                        <span className="stat-icon mint">
                          <Bell size={19} />
                        </span>
                        <div>
                          <strong>{n.message}</strong>
                          <small>
                            {formatDate(n.created_at)} •{" "}
                            {n.read ? "Lida" : "Nova"}
                          </small>
                        </div>
                        {!n.read && (
                          <button
                            className="text-link"
                            disabled={busy}
                            onClick={() =>
                              act(() =>
                                send(
                                  "/api/v1/notifications/" + n.id,
                                  { read: true },
                                  "PATCH",
                                ),
                              )
                            }
                          >
                            Marcar como lida
                          </button>
                        )}
                      </article>
                    ))}
                  </div>
                ) : (
                  <Empty title="Nenhuma novidade por enquanto">
                    As atualizações do seu acompanhamento aparecerão aqui.
                  </Empty>
                )}
              </Section>
            )}
            {tab === "account" && (
              <Section title="Seus dados">
                <dl className="account-details">
                  <dt>Nome</dt>
                  <dd>{user.name}</dd>
                  <dt>E-mail</dt>
                  <dd>{user.email}</dd>
                  <dt>Perfil</dt>
                  <dd>{roles[user.role]}</dd>
                </dl>
                <PrivacyRights
                  route={route}
                  act={act}
                  busy={busy}
                  onError={showError}
                  onPrivacyChange={() =>
                    api("/api/v1/me")
                      .then((r) => changeUser(r.user))
                      .catch(showError)
                  }
                />
                <div className="button-row">
                  <button
                    className="secondary"
                    onClick={() => route.open(["privacidade"])}
                  >
                    Ler aviso de privacidade
                  </button>
                  {user.role === "familia" && (
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() =>
                        act(async () => {
                          const data = await api("/api/v1/privacy/export");
                          const url = URL.createObjectURL(
                            new Blob([JSON.stringify(data, null, 2)], {
                              type: "application/json",
                            }),
                          );
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = "meus-dados-imuniguia.json";
                          a.click();
                          setTimeout(() => URL.revokeObjectURL(url), 1000);
                        }, "Exportação preparada.")
                      }
                    >
                      Exportar meus dados
                    </button>
                  )}
                </div>
                <p className="muted small">
                  Para correções de histórico ou avaliação de exclusão, procure
                  a equipe responsável pela instalação.
                </p>
              </Section>
            )}
            {tab === "home" && (
              <details className="secondary-panel">
                <summary>Instalar e receber avisos</summary>
                <PwaPanel
                  family={user.role === "familia"}
                  act={act}
                  busy={busy}
                />
              </details>
            )}
            {tab === "account" && (
              <PwaPanel
                family={user.role === "familia"}
                act={act}
                busy={busy}
              />
            )}
            <footer className="page-footer">
              <span>ImuniGuia</span>
              <span>
                <ShieldCheck size={14} /> Acesso protegido
              </span>
            </footer>
          </main>
        </div>
        <nav className="mobile-tabs" aria-label="Atalhos do aplicativo">
          {(user.role === "familia"
            ? [
                ["home", Home],
                ["schedule", CalendarClock],
                ["history", Heart],
                ["documents", FileText],
              ]
            : user.role === "ubs"
              ? [
                  ["home", Home],
                  ["review", ClipboardCheck],
                  ["history", Heart],
                  ["notifications", Bell],
                ]
              : [
                  ["home", Home],
                  ["outreach", Users],
                  ["notifications", Bell],
                ]
          ).map(([key, Icon]) => (
            <a
              key={key}
              href={profilePath(user, key)}
              aria-current={tab === key ? "page" : undefined}
              className={tab === key ? "active" : ""}
              onClick={follow(key)}
            >
              <Icon size={21} />
              <span>
                {key === "schedule"
                  ? "Calendário"
                  : key === "documents"
                    ? "Cadernetas"
                    : key === "review"
                      ? "Conferir"
                      : key === "history"
                        ? user.role === "familia"
                          ? "Vacinas"
                          : "Histórico"
                        : key === "home"
                          ? "Início"
                          : tabs[key]}
              </span>
            </a>
          ))}
        </nav>
        {toast && (
          <div
            className={`toast ${toast.error ? "error" : ""}`}
            role={toast.error ? "alert" : "status"}
            aria-live={toast.error ? "assertive" : "polite"}
          >
            {toast.text}
            <button onClick={() => setToast(null)} aria-label="Fechar aviso">
              <X size={18} />
            </button>
          </div>
        )}
        {user.role === "familia" &&
          ["home", "family"].includes(tab) &&
          (action === "adicionar-pessoa" ||
            (action === "editar-pessoa" && person)) && (
            <PersonForm
              key={id || action}
              person={action === "editar-pessoa" ? person : null}
              onClose={route.close}
              act={act}
              busy={busy}
            />
          )}
        {user.role === "familia" &&
          ["home", "documents", "history"].includes(tab) &&
          action === "enviar-caderneta" && (
            <UploadForm
              people={people}
              selected={person?.id || selected}
              onClose={route.close}
              act={act}
              busy={busy}
            />
          )}
        {documentRoute && !currentDocument && loadedFor === user.id && (
          <Modal title="Caderneta indisponível" onClose={route.close}>
            <p>
              {queueRoute
                ? "Use Começar a conferir para abrir a primeira caderneta da fila."
                : "Confira se a caderneta aparece na sua lista."}
            </p>
          </Modal>
        )}
        {currentDocument && (
          <DocumentReview
            key={id}
            document={currentDocument}
            user={user}
            step={step}
            readOnly={archiveRoute}
            onProgress={afterVote}
            route={route}
            onStep={(next) => route.open([action, id, next], { replace: true })}
            onClose={route.close}
            act={act}
            busy={busy}
            onError={showError}
          />
        )}
        {tab === "account" && action === "privacidade" && (
          <Privacy onClose={route.close} />
        )}
      </div>
    </FeedbackContext.Provider>
  );
}

function PersonForm({ person, onClose, act, busy }) {
  async function submit(e) {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(e.currentTarget));
    values.representationConfirmed = values.representationConfirmed === "on";
    if (
      await act(
        () =>
          send(
            "/api/dependents" + (person ? "/" + person.id : ""),
            values,
            person ? "PATCH" : "POST",
          ),
        person ? "Dados atualizados." : "Pessoa adicionada à sua família.",
      )
    )
      onClose();
  }
  return (
    <Modal
      title={person ? "Editar pessoa" : "Adicionar pessoa"}
      onClose={onClose}
    >
      <form onSubmit={submit}>
        <fieldset disabled={busy}>
          <p className="muted">
            Cadastre seus dados ou os de alguém que você pode legalmente
            representar.
          </p>
          <Field
            label="Nome completo"
            name="name"
            defaultValue={person?.name}
            minLength={2}
            maxLength={80}
            required
          />
          <Field
            label="Data de nascimento"
            type="date"
            name="birthDate"
            defaultValue={person?.birthDate || ""}
            min="1900-01-01"
            max={today()}
            required
          />
          <label className="checkbox">
            <input type="checkbox" name="representationConfirmed" required />
            <span>
              Confirmo que estes dados são meus ou que posso representar esta
              pessoa. Para crianças e adolescentes, sou responsável legal e ajo
              em seu melhor interesse.
            </span>
          </label>
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={onClose}>
              Cancelar
            </button>
            <button className="primary" type="submit">
              {busy ? "Salvando…" : "Salvar pessoa"}
            </button>
          </div>
        </fieldset>
      </form>
    </Modal>
  );
}
