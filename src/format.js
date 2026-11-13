export const vaccines = [
  "BCG",
  "Hepatite B",
  "Pentavalente",
  "Poliomielite VIP",
  "Pneumocócica 10",
  "Rotavírus humano",
  "Meningocócica C",
  "Febre amarela",
  "Tríplice viral",
  "Hepatite A",
  "Tetraviral",
  "DTP",
  "Varicela",
  "Outro registro",
];
export const labels = {
  pendente: "Aguardando conferência",
  aprovado: "Arquivo conferido",
  rejeitado: "Devolvido para ajuste",
  a_conferir: "A conferir",
  validado: "Dose confirmada",
  recusado: "Registro de dose recusado",
  aberta: "Possível pendência",
  resolvida: "Resolvida",
  queued: "Na fila de leitura",
  processing: "Leitura em andamento",
  completed: "Leitura concluída",
  unreadable: "Precisa de leitura manual",
  failed: "Falha na leitura",
};
export const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat("pt-BR", {
        timeZone: value.length === 10 ? "UTC" : undefined,
      }).format(new Date(value.length === 10 ? value + "T12:00:00Z" : value))
    : "Não informada";
export const today = () => new Date().toLocaleDateString("en-CA");

const familiarNames = {
  "poliomielite vip": "Paralisia infantil (VIP)",
  poliomielite: "Paralisia infantil (poliomielite)",
  "tríplice viral": "Sarampo, caxumba e rubéola (tríplice viral)",
  varicela: "Catapora (varicela)",
  "rotavírus humano": "Rotavírus",
  dtp: "Difteria, tétano e coqueluche (DTP)",
};

export function vaccineLabel(name) {
  const key = name?.trim().toLowerCase();
  return Object.hasOwn(familiarNames, key) ? familiarNames[key] : name;
}

export function nextPendingByVaccine(items) {
  const first = new Map();
  for (const item of items) {
    if (item.status !== "aberta") continue;
    const key = item.vaccine.trim().normalize("NFC").toLowerCase();
    const previous = first.get(key);
    if (!previous || Number(item.dose) < Number(previous.dose)) {
      first.set(key, item);
    }
  }
  return [...first.values()].sort((a, b) =>
    vaccineLabel(a.vaccine).localeCompare(vaccineLabel(b.vaccine), "pt-BR"),
  );
}
