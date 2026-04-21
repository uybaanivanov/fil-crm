import { getUser } from './auth.js';

const BASE = 'http://localhost:8000';

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `HTTP ${status}`);
        this.status = status;
        this.detail = detail;
    }
}

async function request(method, path, body, { auth = true } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
        const user = getUser();
        if (user) headers['X-User-Id'] = String(user.id);
    }
    const res = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body)
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, data.detail || `HTTP ${res.status}`);
    return data;
}

export const api = {
    get:    (path, opts)       => request('GET',    path, undefined, opts),
    post:   (path, body, opts) => request('POST',   path, body,      opts),
    patch:  (path, body, opts) => request('PATCH',  path, body,      opts),
    delete: (path, opts)       => request('DELETE', path, undefined, opts)
};
