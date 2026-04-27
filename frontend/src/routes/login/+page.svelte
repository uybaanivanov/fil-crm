<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError, isDevPickerAvailable } from '$lib/api.js';
    import { setUser } from '$lib/auth.js';
    import { DEMO } from '$lib/demo.js';

    let devAvailable = $state(false);
    let username = $state('');
    let password = $state('');
    let showPass = $state(false);
    let busy = $state(false);
    let error = $state(null);

    onMount(async () => {
        if (DEMO) {
            goto('/dev_auth');
            return;
        }
        devAvailable = await isDevPickerAvailable();
    });

    async function submit(e) {
        e.preventDefault();
        if (!username.trim() || !password) {
            error = 'Введи логин и пароль'; return;
        }
        busy = true; error = null;
        try {
            const u = await api.post('/auth/login', { username: username.trim(), password }, { auth: false });
            setUser(u);
            goto(u.role === 'maid' ? '/cleaning' : '/');
        } catch (e) {
            error = e instanceof ApiError ? e.message : 'Ошибка сети';
        } finally {
            busy = false;
        }
    }
</script>

<div class="page">
    <div class="brand">
        <div class="logo">f</div>
        <span class="word">fil<span class="dash">-</span>crm</span>
    </div>

    <h1 class="greeting">С возвращением<span class="dot-accent">.</span></h1>
    <p class="sub">Войдите, чтобы управлять квартирами, бронями и уборкой.</p>

    <form onsubmit={submit}>
        <label class="field-label" for="login-username">Логин</label>
        <input id="login-username" type="text" bind:value={username} class="field" autocomplete="username" />

        <label class="field-label" for="login-pass">Пароль</label>
        <div class="pass-wrap">
            <input
                id="login-pass"
                type={showPass ? 'text' : 'password'}
                bind:value={password}
                class="field pass-input"
                placeholder="••••••••"
                autocomplete="current-password"
            />
            <button type="button" class="show" onclick={() => (showPass = !showPass)}>
                {showPass ? 'Скрыть' : 'Показать'}
            </button>
        </div>

        {#if error}<div class="login-err">{error}</div>{/if}

        <button type="submit" class="primary-btn" disabled={busy}>
            {busy ? 'Входим…' : 'Войти →'}
        </button>
    </form>

    {#if devAvailable}
        <button class="dev-link" onclick={() => goto('/dev_auth')} type="button">
            → Dev picker (без пароля)
        </button>
    {/if}

    <div class="version">v2.1.0 · Якутск</div>
</div>

<style>
    .page {
        min-height: 100vh;
        padding: 40px 28px 20px;
        display: flex;
        flex-direction: column;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 44px;
    }
    .logo {
        width: 22px;
        height: 22px;
        background: var(--ink);
        color: var(--bg);
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-size: 11px;
        font-weight: 700;
    }
    .word { font-family: var(--font-mono); font-size: 15px; font-weight: 500; }
    .dash { color: var(--accent); }
    .greeting {
        font-family: var(--font-serif);
        font-size: 38px;
        line-height: 1;
        letter-spacing: -0.6px;
        color: var(--ink);
        margin: 0 0 10px;
        font-weight: 400;
    }
    .dot-accent { color: var(--accent); }
    .sub {
        font-size: 14px;
        color: var(--muted);
        margin: 0 0 36px;
    }
    .field-label {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        font-weight: 500;
        display: block;
        margin-bottom: 8px;
    }
    .field {
        height: 48px;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 14px;
        background: var(--card);
        color: var(--ink);
        font-size: 15px;
        margin-bottom: 14px;
    }
    .pass-wrap {
        position: relative;
        margin-bottom: 12px;
    }
    .pass-input {
        border: 1.5px solid var(--accent);
        padding-right: 70px;
        margin-bottom: 0;
    }
    .show {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        color: var(--accent);
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
    }
    .login-err {
        font-size: 13px;
        color: #c33;
        margin-bottom: 16px;
    }
    .primary-btn {
        height: 50px;
        background: var(--accent);
        border: none;
        border-radius: 6px;
        color: #fff;
        font-size: 15px;
        font-weight: 600;
        width: 100%;
        cursor: pointer;
    }
    .dev-link {
        margin-top: 16px;
        background: transparent;
        border: 1px dashed var(--border);
        color: var(--faint);
        font-family: var(--font-mono);
        font-size: 12px;
        padding: 10px;
        cursor: pointer;
        border-radius: 6px;
    }
    .version {
        margin-top: auto;
        text-align: center;
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding-top: 24px;
    }
</style>
