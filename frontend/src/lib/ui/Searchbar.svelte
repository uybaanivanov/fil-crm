<script>
    let { placeholder = 'Поиск…', value = $bindable(''), oninput = null } = $props();
</script>

<label class="searchbar">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--faint)" stroke-width="1.8">
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
    </svg>
    <input
        type="search"
        {placeholder}
        bind:value
        oninput={oninput}
    />
</label>

<style>
    .searchbar {
        height: 40px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
    }
    input {
        flex: 1;
        border: none;
        padding: 0;
        background: transparent;
        color: var(--ink);
        width: 100%;
    }
    input:focus-visible { outline: none; }
    input::placeholder { color: var(--faint); }
</style>
