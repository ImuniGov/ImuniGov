import { api, send } from "./api";
let registrationPromise;
export function registerPwa() {
  if (!("serviceWorker" in navigator) || !window.isSecureContext)
    return Promise.resolve(null);
  if (!registrationPromise)
    registrationPromise = navigator.serviceWorker.register("/sw.js", {
      scope: "/",
    });
  return registrationPromise;
}
export async function enablePush() {
  if (
    !("Notification" in window) ||
    !("PushManager" in window) ||
    !window.isSecureContext
  )
    throw new Error(
      "Este navegador não oferece avisos neste modo. Em iPhone, adicione o app à Tela de Início e abra por ele.",
    );
  const permission = await Notification.requestPermission();
  if (permission !== "granted")
    throw new Error(
      "Avisos não autorizados. Você continua recebendo as atualizações dentro do aplicativo.",
    );
  await registerPwa();
  const registration = await navigator.serviceWorker.ready;
  const { publicKey } = await api("/api/v1/push/config");
  const key = Uint8Array.from(
    atob(
      publicKey
        .replace(/-/g, "+")
        .replace(/_/g, "/")
        .padEnd(Math.ceil(publicKey.length / 4) * 4, "="),
    ),
    (c) => c.charCodeAt(0),
  );
  const subscription =
    (await registration.pushManager.getSubscription()) ||
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: key,
    }));
  await send("/api/v1/push/subscriptions", subscription.toJSON());
}
export async function disablePush() {
  if (!("serviceWorker" in navigator)) return;
  const registration = await navigator.serviceWorker.getRegistration();
  const subscription = await registration?.pushManager?.getSubscription();
  if (subscription) {
    try {
      await send("/api/v1/push/unsubscribe", {
        endpoint: subscription.endpoint,
      });
    } finally {
      await subscription.unsubscribe();
    }
  }
}
