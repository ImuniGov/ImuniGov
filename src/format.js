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
  validado: "Registro confirmado",
  recusado: "Registro recusado",
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
