import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// StrictMode deshabilitado en dev: provoca un doble-mount del useEffect que
// abre el EventSource del stream SSE, abortándolo antes de que onopen dispare
// y dejando el estado en "disconnected". Producción nunca usó StrictMode aquí.
createRoot(document.getElementById('root')!).render(<App />)
