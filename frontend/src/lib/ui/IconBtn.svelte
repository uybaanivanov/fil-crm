<script>
    let {
        d,
        bg = 'transparent',
        color = 'var(--ink2)',
        size = 36,
        border = true,
        onclick = null,
        title = ''
    } = $props();
</script>

<button
    class="icon-btn"
    style:width="{size}px"
    style:height="{size}px"
    style:border-radius="{size/2}px"
    style:background={bg}
    style:border={(border && bg === 'transparent') ? '1px solid var(--border)' : 'none'}
    title={title}
    onclick={onclick}
    type="button"
>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <path d={d} />
    </svg>
</button>

<style>
    .icon-btn {
        padding: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        cursor: pointer;
    }
    .icon-btn:hover { opacity: 0.85; }
</style>
