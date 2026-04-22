<!--
  Обёртка для редактируемого поля.
  Отображает метку сверху и слот с инпутом внутри; под инпутом
  рисуется пунктирная линия (обычная или primary для required).
-->
<script>
    let {
        label,
        required = false,
        error = null,
        hint = null,
        children,
    } = $props();
</script>

<label class="field" class:required class:has-error={!!error}>
    <span class="lbl">
        {label}
        {#if required}<span class="req">*</span>{/if}
    </span>
    <div class="slot">
        {@render children()}
    </div>
    {#if error}
        <span class="err">{error}</span>
    {:else if hint}
        <span class="hint">{hint}</span>
    {:else if required}
        <span class="hint">Обязательно для сохранения</span>
    {/if}
</label>

<style>
    .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 6px 0 4px;
        border-bottom: 1px dashed var(--border);
    }
    .field.required { border-bottom-color: var(--primary, var(--accent)); }
    .field.has-error { border-bottom-color: var(--danger, #c33); }
    .lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--faint);
    }
    .req { color: var(--primary, var(--accent)); margin-left: 2px; }
    .slot :global(input),
    .slot :global(select) {
        width: 100%;
        border: none;
        outline: none;
        background: transparent;
        font-size: 13px;
        color: var(--ink);
        padding: 2px 0;
    }
    .slot :global(input:focus),
    .slot :global(select:focus) {
        outline: none;
    }
    .hint {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .err {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--danger, #c33);
    }
</style>
