<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { isDevPickerAvailable } from '$lib/api.js';

    let devAvailable = $state(false);
    let email = $state('aisen@fil-crm.ru');
    let password = $state('');
    let showPass = $state(false);

    onMount(async () => {
        devAvailable = await isDevPickerAvailable();
    });

    function submit(e) {
        e.preventDefault();
        // Декоративный экран — ничего не делаем.
        // В проде здесь был бы POST /auth/login.
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
        <label class="field-label">Телефон или e-mail</label>
        <input type="email" bind:value={email} class="field" />

        <label class="field-label">Пароль</label>
        <div class="pass-wrap">
            <input
                type={showPass ? 'text' : 'password'}
                bind:value={password}
                class="field pass-input"
                placeholder="••••••••"
            />
            <button type="button" class="show" onclick={() => (showPass = !showPass)}>
                {showPass ? 'Скрыть' : 'Показать'}
            </button>
        </div>

        <a href="#" class="forgot">Забыли пароль?</a>

        <button type="submit" class="primary-btn">Войти →</button>
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
    .forgot {
        display: block;
        font-size: 13px;
        color: var(--accent);
        font-weight: 500;
        margin-bottom: 24px;
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
