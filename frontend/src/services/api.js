import axios from 'axios'

/**
 * Base URL resolution:
 * - In development (Vite): relative /api/* is proxied to http://localhost:8000 via vite.config.js
 * - In Docker (nginx):     relative /api/* is proxied to http://backend:8000 via nginx.conf
 * - VITE_API_URL env var overrides for non-standard deployments (e.g. Cloud Run with custom domain)
 */
const BASE_URL = import.meta.env.VITE_API_URL || 'https://pandemic-backend-tyn3bi3fna-uc.a.run.app'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 90000,   // Agent analysis can take up to ~15s for 5 SEIR runs
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  res => res,
  err => {
    const detail = err.response?.data?.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map(d => d.msg ?? JSON.stringify(d)).join('; ')
        : err.message
    console.error('[API Error]', err.config?.url, message)
    return Promise.reject({ ...err, friendlyMessage: message })
  }
)

export const regionService = {
  getAll:       ()   => api.get('/api/regions').then(r => r.data),
  getById:      (id) => api.get(`/api/regions/${id}`).then(r => r.data),
  getHistorical:(id) => api.get(`/api/regions/${id}/historical`).then(r => r.data),
}

export const simulationService = {
  run:           (payload) => api.post('/api/simulate', payload).then(r => r.data),
  getParameters: (id)      => api.get(`/api/simulate/parameters/${id}`).then(r => r.data),
  interventions: ()        => api.get('/api/simulate/interventions').then(r => r.data),
}

export const scenarioService = {
  run:           (payload) => api.post('/api/scenario', payload).then(r => r.data),
  getInterventions: ()     => api.get('/api/scenario/interventions').then(r => r.data),
}

export const agentService = {
  analyze: (payload) => api.post('/api/agents/analyze', payload).then(r => r.data),
  status:  ()        => api.get('/api/agents/status').then(r => r.data),
}

export const recommendService = {
  get: (payload) => api.post('/api/recommend', payload).then(r => r.data),
}

export const predictService = {
  run: (payload) => api.post('/api/predict', payload).then(r => r.data),
}

export const mcpAgentService = {
  run:    (query) => api.post('/api/mcp-agent', { query }).then(r => r.data),
  schema: ()      => api.get('/api/mcp-agent/schema').then(r => r.data),
}

export const api_health_check = () => api.get('/health').then(r => r.data)

export default api
