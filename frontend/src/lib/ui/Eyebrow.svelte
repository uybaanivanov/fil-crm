<script>
    let { children } = $props();
</script>

<div class="eyebrow">{@render children?.()}</div>

<style>
    .eyebrow {
        font-family: var(--font-mono);
        font-size: 10px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--faint);
        font-weight: 500;
    }
</style>
