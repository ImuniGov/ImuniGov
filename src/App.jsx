import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
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
import { formatDate, today } from "./format";
import {
  UploadForm,
  DocumentReview,
  FamilyHistory,
  Outreach,
} from "./Workspaces";

const roles = {
  familia: "Família",
  ubs: "Equipe da UBS",
  acs: "Agente comunitário",
};
const tabs = {
  home: "Visão geral",
  family: "Minha família",
  schedule: "Próximas doses",
  documents: "Cadernetas",
  history: "Vacinas e orientações",
  review: "Fila de conferência",
  outreach: "Contatos com famílias",
  notifications: "Avisos",
  account: "Minha conta",
};

export default function App() {
  const [user, setUser] = useState(null),
    [starting, setStarting] = useState(true),
    [tab, setTab] = useState(
      new URLSearchParams(window.location.search).get("view") ===
        "notifications"
        ? "notifications"
        : "home",
    );
  const [people, setPeople] = useState([]),
    [documents, setDocuments] = useState([]),
    [notes, setNotes] = useState([]);
  const [schedule, setSchedule] = useState({
    items: [],
    coverage: { valid: true, vaccines: [] },
  });
  const [cases, setCases] = useState([]);
  const currentUser = useRef(null);
  const changeUser = useCallback((next) => {
    currentUser.current = next;
    setUser(next);
    setPeople([]);
    setDocuments([]);
    setNotes([]);
    setCases([]);
    setSchedule({ items: [], coverage: { valid: true, vaccines: [] } });
  }, []);
  const [selected, setSelected] = useState(""),
    [filter, setFilter] = useState("todos"),
    [search, setSearch] = useState("");
  const [modal, setModal] = useState(null),
    [toast, setToast] = useState(null),
    [busy, setBusy] = useState(false),
    [menu, setMenu] = useState(false);
  const showError = useCallback(
    (err) => setToast({ text: err.message || String(err), error: true }),
    [],
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
    setSelected((old) =>
      result[0].items.some((p) => p.id === old)
        ? old
        : result[0].items[0]?.id || "",
    );
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
        setTab("home");
        setMenu(false);
      },
      undefined,
      false,
    );
  }
  const navigate = (key) => {
    setTab(key);
    setMenu(false);
    setSearch("");
    setFilter("todos");
    document.getElementById("conteudo")?.focus();
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const closeModal = useCallback(() => setModal(null), []);
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
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate("home");
            }}
          >
            <span className="brand-icon">✳</span>
            <span>
              imuni<span className="brand-light">guia</span>
            </span>
          </a>
          <span className="sidebar-label">ACOMPANHAMENTO</span>
          <nav aria-label="Navegação principal">
            {nav.map(([key, Icon]) => (
              <button
                key={key}
                aria-current={tab === key ? "page" : undefined}
                className={tab === key ? "active" : ""}
                onClick={() => navigate(key)}
              >
                <Icon size={19} />
                <span>{tabs[key]}</span>
                {key === "notifications" && unread > 0 && (
                  <b className="nav-count">{unread}</b>
                )}
                {key === "review" && pending > 0 && (
                  <b className="nav-count">{pending}</b>
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <button
              className={tab === "account" ? "active" : ""}
              onClick={() => navigate("account")}
            >
              <Settings size={18} /> Minha conta
            </button>
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
            <div className="page-intro">
              <div>
                <h1>
                  {tab === "home"
                    ? `Olá, ${user.name.split(" ")[0]}.`
                    : tabs[tab]}
                </h1>
                <p>
                  {tab === "home"
                    ? user.role === "familia"
                      ? "Veja as próximas datas e os retornos da UBS."
                      : "Acompanhe os arquivos e os contatos pendentes."
                    : tab === "review"
                      ? "Confira o arquivo antes de confirmar cada dose."
                      : tab === "outreach"
                        ? "Veja quem precisa de contato e registre o atendimento."
                        : "Consulte as informações e as ações disponíveis abaixo."}
                </p>
              </div>
              {user.role === "familia" && ["home", "family"].includes(tab) && (
                <AddButton onClick={() => setModal({ type: "person" })}>
                  Adicionar pessoa
                </AddButton>
              )}
              {user.role === "familia" && tab === "documents" && (
                <AddButton onClick={() => setModal({ type: "upload" })}>
                  Enviar caderneta
                </AddButton>
              )}
            </div>
            <div className="demo-note">
              <Activity size={16} />
              <span>
                Versão de testes • use dados fictícios para demonstração.
              </span>
            </div>
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
                    resend={(id) => {
                      setSelected(id);
                      setModal({ type: "upload" });
                    }}
                  />
                )}
                <div className="hero-card">
                  <div>
                    <span className="eyebrow light">PRÓXIMA AÇÃO</span>
                    <h2>
                      {user.role === "familia"
                        ? documents.length
                          ? "Acompanhe as cadernetas enviadas"
                          : "Envie uma caderneta para conferência"
                        : user.role === "ubs"
                          ? "Confira as cadernetas atribuídas a você"
                          : "Organize os contatos com as famílias"}
                    </h2>
                    <p>
                      {user.role === "familia"
                        ? "Envie a caderneta e acompanhe a conferência pela UBS."
                        : user.role === "ubs"
                          ? "Veja os arquivos, confira os dados e oriente a família."
                          : "Encontre os casos que precisam de contato e registre cada ação."}
                    </p>
                    <button
                      className="hero-button"
                      onClick={() =>
                        user.role === "familia"
                          ? documents.length
                            ? navigate("documents")
                            : setModal({
                                type: people.length ? "upload" : "person",
                              })
                          : navigate(
                              user.role === "ubs" ? "review" : "outreach",
                            )
                      }
                    >
                      {user.role === "familia"
                        ? documents.length
                          ? "Ver minhas cadernetas"
                          : "Enviar minha caderneta"
                        : user.role === "ubs"
                          ? "Abrir fila de conferência"
                          : "Ver busca ativa"}
                      <ArrowRight size={17} />
                    </button>
                  </div>
                </div>
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
                        [
                          "Famílias acompanhadas",
                          new Set(cases.map((c) => c.guardian)).size,
                          Heart,
                          "blue",
                        ],
                        ["Novas notificações", unread, Bell, "lilac"],
                      ]
                    : [
                        [
                          user.role === "familia"
                            ? "Pessoas acompanhadas"
                            : "Pessoas atribuídas à sua equipe",
                          people.length,
                          Users,
                          "mint",
                        ],
                        [
                          "Arquivos aguardando conferência",
                          pending,
                          FileText,
                          "peach",
                        ],
                        [
                          "Arquivos conferidos",
                          documents.filter((d) => d.status === "aprovado")
                            .length,
                          ClipboardCheck,
                          "blue",
                        ],
                        ["Novas notificações", unread, Bell, "lilac"],
                      ]
                  ).map(([title, count]) => (
                    <div className="stat-card" key={title}>
                      <span>{title}</span>
                      <strong>{count}</strong>
                    </div>
                  ))}
                </div>
                <div className="home-grid">
                  <Section
                    title={
                      user.role === "familia"
                        ? "Sua família"
                        : "Acompanhamento recente"
                    }
                    description="Pessoas e atividades mais recentes"
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
                    {user.role === "acs" ? (
                      <Empty title="Nenhum contato pendente">
                        Abra a busca ativa para consultar os casos da unidade.
                      </Empty>
                    ) : people.length ? (
                      <div className="person-list">
                        {people.slice(0, 4).map((p) => (
                          <button
                            className="person-row"
                            key={p.id}
                            onClick={() => {
                              setSelected(p.id);
                              navigate("history");
                            }}
                          >
                            <span className="person-avatar">
                              {p.name.charAt(0)}
                            </span>
                            <span>
                              <strong>{p.name}</strong>
                              <small>
                                Nascimento: {formatDate(p.birthDate)}
                              </small>
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
                                ? setModal({ type: "person" })
                                : navigate("review")
                            }
                          >
                            {user.role === "familia"
                              ? "Cadastrar primeira pessoa"
                              : "Ver minha fila"}{" "}
                            <ArrowRight size={15} />
                          </button>
                        }
                      >
                        {user.role === "familia"
                          ? "Adicione você ou um dependente para começar."
                          : "A atribuição depende do cadastro profissional verificado e de uma equipe geograficamente compatível."}
                      </Empty>
                    )}
                  </Section>
                  <Section title="Como funciona" className="how-it-works">
                    {[
                      [
                        "01",
                        "Envie a caderneta",
                        "Foto nítida ou PDF vinculado à pessoa certa.",
                      ],
                      [
                        "02",
                        "A equipe confere",
                        "Três profissionais conferem o arquivo e depois cada dose.",
                      ],
                      [
                        "03",
                        "Veja o retorno da UBS",
                        "Veja os registros, os motivos de recusa e o que fazer.",
                      ],
                    ].map(([n, title, text]) => (
                      <div className="step-row" key={n}>
                        <b>{n}</b>
                        <div>
                          <strong>{title}</strong>
                          <p>{text}</p>
                        </div>
                      </div>
                    ))}
                  </Section>
                </div>
              </>
            )}
            {tab === "schedule" && user.role === "familia" && (
              <FamilySchedule
                schedule={schedule}
                people={people}
                openHistory={(id) => {
                  setSelected(id);
                  navigate("history");
                }}
              />
            )}
            {tab === "family" && (
              <Section
                title="Pessoas que você acompanha"
                description="Cadastre somente os dados necessários para o cuidado."
              >
                {people.length ? (
                  <div className="family-grid">
                    {people.map((p) => (
                      <article className="family-card" key={p.id}>
                        <span className="person-avatar large">
                          {p.name.charAt(0)}
                        </span>
                        <h3>{p.name}</h3>
                        <p>Nascimento: {formatDate(p.birthDate)}</p>
                        <small>{p.document_count} arquivo(s) enviado(s)</small>
                        <div className="button-row">
                          <button
                            className="secondary"
                            onClick={() => {
                              setSelected(p.id);
                              navigate("history");
                            }}
                          >
                            Acompanhar <ArrowRight size={15} />
                          </button>
                          <button
                            className="text-link"
                            onClick={() =>
                              setModal({ type: "person", person: p })
                            }
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
            {["documents", "review"].includes(tab) && (
              <Section
                title={
                  user.role === "ubs"
                    ? "Arquivos para conferência"
                    : "Cadernetas enviadas"
                }
                description="O arquivo e cada dose passam por conferências separadas."
              >
                <div className="table-toolbar">
                  <div className="filters">
                    {[
                      ["todos", "Todos"],
                      ["pendente", "Aguardando"],
                      ["aprovado", "Conferidos"],
                      ["rejeitado", "Devolvidos"],
                    ].map(([key, label]) => (
                      <button
                        key={key}
                        className={filter === key ? "selected" : ""}
                        onClick={() => setFilter(key)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <label className="search">
                    <Search size={17} />
                    <input
                      aria-label="Buscar arquivos"
                      placeholder="Buscar pessoa ou arquivo"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </label>
                </div>
                {shown.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>ARQUIVO / PESSOA</th>
                          <th>REGISTRO INFORMADO</th>
                          <th>RECEBIDO</th>
                          <th>SITUAÇÃO</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {shown.map((d) => (
                          <tr key={d.id}>
                            <td>
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
                            <td>{d.vaccine}</td>
                            <td>{formatDate(d.createdAt)}</td>
                            <td>
                              <Badge status={d.status} />
                            </td>
                            <td>
                              <button
                                className="text-link"
                                onClick={() =>
                                  setModal({ type: "document", document: d })
                                }
                              >
                                {user.role === "ubs" ? "Conferir" : "Detalhes"}
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
                      : user.role === "familia"
                        ? "Envie uma foto ou PDF para iniciar a conferência."
                        : "Os novos envios aparecerão aqui para análise."}
                  </Empty>
                )}
              </Section>
            )}
            {tab === "history" && (
              <FamilyHistory
                resend={(id) => {
                  setSelected(id);
                  setModal({ type: "upload" });
                }}
                key={selected}
                people={people}
                selected={selected}
                onSelect={setSelected}
                user={user}
                act={act}
                busy={busy}
                onError={showError}
              />
            )}
            {tab === "outreach" && (
              <Outreach user={user} act={act} busy={busy} onError={showError} />
            )}
            {tab === "notifications" && (
              <Section
                title="Novidades do acompanhamento"
                description="Avisos sobre conferências, orientações e possíveis pendências."
              >
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
              <Section
                title="Seu acesso"
                description="Informações da sua conta e privacidade."
              >
                <dl className="account-details">
                  <dt>Nome</dt>
                  <dd>{user.name}</dd>
                  <dt>E-mail</dt>
                  <dd>{user.email}</dd>
                  <dt>Perfil</dt>
                  <dd>{roles[user.role]}</dd>
                </dl>
                <PrivacyRights act={act} busy={busy} onError={showError} />
                <div className="button-row">
                  <button
                    className="secondary"
                    onClick={() => setModal({ type: "privacy" })}
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
            {["home", "account"].includes(tab) && (
              <PwaPanel
                family={user.role === "familia"}
                act={act}
                busy={busy}
              />
            )}
            <footer className="page-footer">
              <span>ImuniGuia • Informação que aproxima o cuidado</span>
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
                ["documents", FileText],
                ["notifications", Bell],
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
            <button
              key={key}
              aria-current={tab === key ? "page" : undefined}
              className={tab === key ? "active" : ""}
              onClick={() => navigate(key)}
            >
              <Icon size={21} />
              <span>
                {key === "schedule"
                  ? "Próximas doses"
                  : key === "documents"
                    ? "Cadernetas"
                    : key === "review"
                      ? "Conferir"
                      : key === "history"
                        ? "Histórico"
                        : key === "home"
                          ? "Início"
                          : tabs[key]}
              </span>
            </button>
          ))}
        </nav>
        {toast && (
          <div
            className={`toast ${toast.error ? "error" : ""}`}
            role={toast.error ? "alert" : "status"}
          >
            {toast.text}
            <button onClick={() => setToast(null)} aria-label="Fechar aviso">
              <X size={18} />
            </button>
          </div>
        )}
        {modal?.type === "person" && (
          <PersonForm
            person={modal.person}
            onClose={closeModal}
            act={act}
            busy={busy}
          />
        )}
        {modal?.type === "upload" && (
          <UploadForm
            people={people}
            selected={selected}
            onClose={closeModal}
            act={act}
            busy={busy}
          />
        )}
        {modal?.type === "document" && (
          <DocumentReview
            document={modal.document}
            user={user}
            onClose={closeModal}
            act={act}
            busy={busy}
            onError={showError}
          />
        )}
        {modal?.type === "privacy" && <Privacy onClose={closeModal} />}
      </div>
    </FeedbackContext.Provider>
  );
}

function PersonForm({ person, onClose, act, busy }) {
  async function submit(e) {
    e.preventDefault();
    const values = Object.fromEntries(new FormData(e.currentTarget));
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
            <input type="checkbox" required />
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
