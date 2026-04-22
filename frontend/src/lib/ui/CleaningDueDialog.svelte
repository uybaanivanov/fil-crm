<script>
    let {
        open = false,
        defaultValue = '',
        errorText = null,
        title = 'Когда требуется уборка?',
        onSubmit,
        onCancel
    } = $props();

    let value = $state(defaultValue);
    let inputEl;

    $effect(() => {
        if (open) {
            value = defaultValue;
            queueMicrotask(() => inputEl?.focus());
        }
    });

    function submit() {
        if (!value) return;
        onSubmit?.(value);
    }

    function onKey(e) {
        if (e.key === 'Enter') { e.preventDefault(); submit(); }
        else if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
    }
</script>

{#if open}
    <div class="backdrop" onclick={onCancel} role="presentation"></div>
    <div class="dialog" role="dialog" aria-modal="true" aria-label={title}>
        <div class="title">{title}</div>
        <input
            bind:this={inputEl}
            bind:value
            type="datetime-local"
            class="input"
            onkeydown={onKey}
        />
        {#if errorText}<div class="err">{errorText}</div>{/if}
        <div class="actions">
            <button type="button" class="ghost" onclick={onCancel}>Отмена</button>
            <button type="button" class="primary" disabled={!value} onclick={submit}>Сохранить</button>
        </div>
    </div>
{/if}

<style>
    .backdrop {
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.4);
        z-index: 1000;
    }
    .dialog {
        position: fixed;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: min(360px, calc(100vw - 40px));
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 16px;
        z-index: 1001;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .title { font-size: 15px; font-weight: 600; color: var(--ink); }
    .input {
        width: 100%;
        box-sizing: border-box;
        padding: 10px 12px;
        font-size: 14px;
        font-family: inherit;
        border: 1px solid var(--border);
        border-radius: 6px;
        background: var(--bg);
        color: var(--ink);
    }
    .err {
        font-size: 12px;
        color: var(--danger);
    }
    .actions {
        display: flex; gap: 10px; justify-content: flex-end;
    }
    .primary, .ghost {
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 6px;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: transparent; color: var(--ink); border: 1px solid var(--border); }
</style>
