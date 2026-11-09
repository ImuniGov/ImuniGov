import { useEffect, useState } from 'react'
import { BellRing, Download, RefreshCw, Smartphone } from 'lucide-react'
import { Section } from './components'
import { disablePush, enablePush, registerPwa } from './pwa'

export default function PwaPanel({ family = false, act, busy }) {
  const [install, setInstall] = useState(null), [enabled, setEnabled] = useState(false), [ready, setReady] = useState(false), [update, setUpdate] = useState(null), [message, setMessage] = useState('')
  useEffect(() => {
    const installable = e => { e.preventDefault(); setInstall(e) }
    const installed = () => { setInstall(null); setMessage('Aplicativo instalado neste aparelho.') }
    window.addEventListener('beforeinstallprompt', installable); window.addEventListener('appinstalled', installed)
    registerPwa().then(async reg => { if (!reg) return; setReady(true); if (reg.waiting) setUpdate(reg.waiting); reg.addEventListener('updatefound', () => { const worker = reg.installing; worker?.addEventListener('statechange', () => { if (worker.state === 'installed' && navigator.serviceWorker.controller) setUpdate(worker) }) }); const subscription = await reg.pushManager?.getSubscription(); setEnabled(!!subscription) }).catch(() => setMessage('Não foi possível preparar o modo instalável. Tente atualizar a página.'))
    return () => { window.removeEventListener('beforeinstallprompt', installable); window.removeEventListener('appinstalled', installed) }
  }, [])
  async function installApp() { if (!install) { setMessage('Android/Chrome: menu ⋮ → Instalar app. iPhone/Safari: Compartilhar → Adicionar à Tela de Início.'); return }; await install.prompt(); const result = await install.userChoice; if (result.outcome === 'accepted') setInstall(null) }
  async function toggle() { const success = await act(() => enabled ? disablePush() : enablePush(), enabled ? 'Avisos desativados neste aparelho.' : 'Avisos ativados neste aparelho.'); if (success) setEnabled(!enabled) }
  return <Section title="Leve o cuidado com você" description="Instale o ImuniGuia e acompanhe pelo celular."><div className="pwa-panel"><span className="stat-icon mint"><Smartphone size={23} /></span><div><strong>Um app no seu aparelho</strong><p>{ready ? 'Modo instalável preparado. Dados da família são consultados com conexão segura.' : 'Use um navegador compatível para instalar o aplicativo.'}</p><div className="button-row"><button className="secondary" onClick={installApp}><Download size={16} /> Instalar aplicativo</button>{family && <button className="secondary" disabled={busy} onClick={toggle}><BellRing size={16} />{enabled ? 'Desativar avisos no aparelho' : 'Ativar avisos no aparelho'}</button>}{update && <button className="secondary" onClick={() => { navigator.serviceWorker.addEventListener('controllerchange', () => window.location.reload(), { once: true }); update.postMessage({ type: 'ACTIVATE_UPDATE' }) }}><RefreshCw size={16} /> Atualizar aplicativo</button>}</div>{family && <p className="small muted">Os avisos são opcionais. A tela bloqueada não mostra nomes nem vacinas. A entrega depende da permissão, conexão e suporte do aparelho.</p>}{message && <p className="notice-box" role="status">{message}</p>}</div></div></Section>
}
