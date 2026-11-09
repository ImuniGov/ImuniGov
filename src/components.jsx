import { useContext, useEffect, useRef } from 'react'
import { X, Plus, ArrowUpRight, FileCheck2 } from 'lucide-react'

import { FeedbackContext } from './feedback'
import { labels } from './format'
export function Badge({ status }) { return <span className={`badge ${status}`}>{labels[status] || status}</span> }
export function Empty({ title = 'Tudo tranquilo por aqui', children, action }) { return <div className="empty"><FileCheck2 size={34} strokeWidth={1.4} /><h3>{title}</h3><p>{children}</p>{action}</div> }
export function Section({ title, description, action, children, className = '' }) { return <section className={`panel ${className}`}><div className="section-heading"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>{children}</section> }
export function Field({ label, children, ...props }) { return <label className="field"><span>{label}</span>{children || <input {...props} />}</label> }
export function AddButton({ children, ...props }) { return <button className="primary" {...props}><Plus size={17} />{children}</button> }
export function Modal({ title, onClose, children }) {
  const ref = useRef(null)
  const feedback = useContext(FeedbackContext)
  useEffect(() => { const d = ref.current; d.showModal(); const close = e => { e.preventDefault(); onClose() }; d.addEventListener('cancel', close); return () => { d.removeEventListener('cancel', close); d.close() } }, [onClose])
  return <dialog ref={ref} className="modal"><div className="modal-title"><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Fechar"><X size={22} /></button></div>{feedback && <p className={feedback.error ? "form-error" : "notice-box"} role={feedback.error ? "alert" : "status"}>{feedback.text}</p>}{children}</dialog>
}
export function Privacy({ onClose }) { return <Modal title="Seus dados, com cuidado" onClose={onClose}><div className="prose"><p>O ImuniGuia reúne informações para apoiar a conferência de cadernetas e o acompanhamento pela equipe de saúde.</p><h3>O que guardamos</h3><p>Nome e e-mail da conta; nome e nascimento dos dependentes; arquivos enviados; registros, decisões, orientações e contatos da equipe. A senha fica protegida por hash e não pode ser consultada.</p><h3>Quem pode acessar</h3><p>A família acessa os próprios dependentes. A UBS confere os registros da unidade. O ACS recebe apenas identificação, contato e motivo de acompanhamento, sem arquivos clínicos.</p><h3>Controle e retenção</h3><p>Você pode exportar seus dados na área Minha conta. Pedidos de correção ou exclusão de histórico devem ser encaminhados à equipe responsável pela instância. Registros de conferência têm histórico de auditoria; não são apagados por operações comuns.</p><p>Esta instalação é destinada à demonstração com dados sintéticos. O responsável pela implantação deve definir finalidade, fundamento, prazos de retenção e canal de atendimento antes de receber dados reais.</p><p className="muted">Aviso de privacidade • versão 08/11/2026</p></div></Modal> }
export function OpenFile({ document }) { return <a className="text-link" href={document.fileUrl} target="_blank" rel="noreferrer">Abrir original <ArrowUpRight size={15} /></a> }
