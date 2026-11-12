import { useCallback, useEffect, useState } from "react";

const screens = {
  home: "inicio",
  family: "minha-familia",
  schedule: "calendario-de-vacinacao",
  documents: "cadernetas",
  history: "vacinas-e-orientacoes",
  review: "fila-de-conferencia",
  outreach: "contatos-com-familias",
  notifications: "avisos",
  account: "minha-conta",
};

const roleScreens = {
  familia: ["family", "schedule", "documents", "history"],
  ubs: ["review", "history", "outreach"],
  acs: ["outreach"],
};

const commonScreens = ["home", "notifications", "account"];
const screenKeys = Object.keys(screens);

export function profileSlug(name) {
  return (
    name
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, "-")
      .replace(/^-|-$/g, "") || "perfil"
  );
}

export function readLocation(browser = window) {
  return {
    path: browser.location.pathname,
    query: new URLSearchParams(browser.location.search),
    state: browser.history.state,
  };
}

export function profileRoute(user, location) {
  const [, role, name, screen, ...parts] = location.path.split("/");
  const matches =
    role === user.role && name === encodeURIComponent(profileSlug(user.name));
  const tab = screenKeys.find((key) => screens[key] === screen);
  const allowed =
    matches && [...commonScreens, ...roleScreens[user.role]].includes(tab);
  return {
    tab: allowed
      ? tab
      : location.query.get("view") === "notifications"
        ? "notifications"
        : "home",
    parts: allowed ? parts.filter(Boolean) : [],
    query: allowed ? location.query : new URLSearchParams(),
    state: allowed ? location.state : null,
    allowed,
  };
}

export function profilePath(
  user,
  tab,
  parts = [],
  query = new URLSearchParams(),
) {
  const path = [user.role, profileSlug(user.name), screens[tab], ...parts]
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
  const suffix = query.toString();
  return "/" + path + (suffix ? "?" + suffix : "");
}

export function useLocation() {
  const [location, setLocation] = useState(() => readLocation());
  useEffect(() => {
    const update = () => setLocation(readLocation());
    window.addEventListener("popstate", update);
    return () => window.removeEventListener("popstate", update);
  }, []);
  const go = useCallback((path, { replace = false, state = null } = {}) => {
    const current = window.location.pathname + window.location.search;
    if (path === current && state === window.history.state) return;
    window.history[replace || path === current ? "replaceState" : "pushState"](
      state,
      "",
      path,
    );
    setLocation(readLocation());
  }, []);
  return [location, go];
}
