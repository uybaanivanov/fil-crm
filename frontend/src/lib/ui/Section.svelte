<script>
    let { title, action = null, children, style = '' } = $props();
</script>

<div class="section" style={style}>
    <div class="head">
        <span class="eyebrow">{title}</span>
        {#if action}<span class="action">{action}</span>{/if}
    </div>
    {@render children?.()}
</div>

<style>
    .section { margin-bottom: 14px; }
    .head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        padding: 0 20px 8px;
    }
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        font-weight: 500;
    }
    .action {
        font-size: 12px;
        color: var(--accent);
        font-weight: 500;
    }
</style>
