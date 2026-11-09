import React from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

function App() {
  const [health, setHealth] = React.useState('Conectando…')
  React.useEffect(() => { fetch('/api/health').then(r => r.json()).then(r => setHealth(r.ok ? 'Serviço disponível' : 'Serviço indisponível')).catch(() => setHealth('Não foi possível conectar à API')) }, [])
  return <main className="welcome"><span className="eyebrow">IMUNIGUIA</span><h1>Cuidar começa<br />com acompanhar.</h1><p>Um lugar para a família e a equipe de saúde acompanharem a vacinação.</p><p role="status">{health}</p></main>
}
createRoot(document.getElementById('root')).render(<App />)
