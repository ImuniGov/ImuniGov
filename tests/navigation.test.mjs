import assert from "node:assert/strict";
import test from "node:test";
import { profilePath, profileRoute, profileSlug } from "../src/navigation.js";

const family = { role: "familia", name: "Ágata da Conceição" };
const agent = { role: "acs", name: "João Agente" };

function parse(user, address, state = null) {
  const { pathname, searchParams } = new URL(address, "https://example.test");
  return profileRoute(user, { path: pathname, query: searchParams, state });
}

test("gera e restaura rota de tela, formulário e filtros", () => {
  assert.equal(profileSlug(family.name), "agata-da-conceicao");
  assert.equal(profileSlug("    "), "perfil");
  assert.equal(profileSlug("João / Ávila"), "joao-avila");
  const url = profilePath(
    family,
    "schedule",
    ["filtros"],
    new URLSearchParams({
      mes: "2026-11",
      dia: "2026-11-20",
    }),
  );
  assert.equal(
    url,
    "/familia/agata-da-conceicao/calendario-de-vacinacao/filtros?mes=2026-11&dia=2026-11-20",
  );
  assert.equal(parse(family, url).query.get("dia"), "2026-11-20");

  const contact = profilePath(agent, "outreach", [
    "ver-contato",
    "id-sintetico",
    "registrar",
  ]);
  assert.deepEqual(parse(agent, contact).parts, [
    "ver-contato",
    "id-sintetico",
    "registrar",
  ]);
});

test("só resolve telas do perfil autenticado", () => {
  const state = { search: "Nome privado" };
  for (const url of [
    profilePath(family, "documents", ["ver-caderneta", "id"]),
    profilePath(agent, "review", ["conferir-caderneta", "id"]),
    "/acs/outro-agente/contatos-com-familias/ver-contato/id",
  ]) {
    const route = parse(agent, url, state);
    assert.equal(route.allowed, false);
    assert.equal(route.tab, "home");
    assert.deepEqual(route.parts, []);
    assert.equal(route.state, null);
  }
});

test("avisos antigos continuam abrindo a tela de avisos", () => {
  assert.equal(parse(family, "/?view=notifications").tab, "notifications");
  assert.equal(
    profilePath(family, "notifications"),
    "/familia/agata-da-conceicao/avisos",
  );
});
