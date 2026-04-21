<script>
    let { onclick = null, title = 'Добавить' } = $props();
</script>

<button class="add-btn" onclick={onclick} title={title} type="button" aria-label={title}>
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round">
        <path d="M12 5v14M5 12h14" />
    </svg>
</button>

<style>
    .add-btn {
        width: 40px;
        height: 40px;
        border-radius: 20px;
        background: var(--accent);
        border: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        padding: 0;
    }
    .add-btn:hover { background: var(--accent2); }
</style>
