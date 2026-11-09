let csrf = ''
export function setCsrf(value) { csrf = value || '' }
export async function api(path, options = {}) {
  const headers = { ...options.headers }
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  if (options.method && options.method !== 'GET') headers['X-CSRF-Token'] = csrf
  let response
  try { response = await fetch(path, { credentials: 'same-origin', ...options, headers }) }
  catch { throw new Error('Não foi possível conectar. Verifique sua conexão e tente novamente.') }
  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error((body?.error || 'Não foi possível concluir a operação.') + (body?.fields?.length ? ` Campos: ${body.fields.join(', ')}.` : ''))
    error.status = response.status
    if (response.status === 401 && csrf && !path.includes('/auth/')) window.dispatchEvent(new Event('session-expired'))
    throw error
  }
  return body
}
export function send(path, body, method = 'POST') { return api(path, { method, body: JSON.stringify(body) }) }
