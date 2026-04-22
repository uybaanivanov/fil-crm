import { getUser } from './auth.js';

const BASE = import.meta.env.VITE_API_BASE ?? '/api';

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `HTTP ${status}`);
        this.status = status;
        this.detail = detail;
    }
}

async function request(method, path, body, { auth = true } = {}) {
    const isFormData = body instanceof FormData;
    const headers = isFormData ? {} : { 'Content-Type': 'application/json' };
    if (auth) {
        const user = getUser();
        if (user) headers['X-User-Id'] = String(user.id);
    }
    const res = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body)
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, data.detail || `HTTP ${res.status}`);
    return data;
}

export const api = {
    get:      (path, opts)           => request('GET',    path, undefined, opts),
    post:     (path, body, opts)     => request('POST',   path, body,      opts),
    postForm: (path, formData, opts) => request('POST',   path, formData,  opts),
    patch:    (path, body, opts)     => request('PATCH',  path, body,      opts),
    delete:   (path, opts)           => request('DELETE', path, undefined, opts)
};

// Helper: определить, жив ли dev-picker. Не бросает — возвращает bool.
export async function isDevPickerAvailable() {
    try {
        const res = await fetch(`${BASE}/dev_auth/users`);
        return res.ok;
    } catch {
        return false;
    }
}
