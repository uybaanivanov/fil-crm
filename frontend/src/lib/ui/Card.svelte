<script>
    let { pad = 16, style = '', children } = $props();
</script>

<div class="card" style:padding="{pad}px" style={style}>
    {@render children?.()}
</div>

<style>
    .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
</style>
