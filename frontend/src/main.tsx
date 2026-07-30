import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Teams SDK init — uncomment when Teams integration is enabled
// import * as microsoftTeams from "@microsoft/teams-js";
// microsoftTeams.initialize();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
