<script>
    let { name = '', size = 36, accent = null } = $props();
    const initials = $derived(
        (name || '?').split(' ').map(s => s[0]).filter(Boolean).slice(0, 2).join('').toUpperCase()
    );
</script>

<div
    class="avatar"
    style:width="{size}px"
    style:height="{size}px"
    style:border-radius="{size/2}px"
    style:font-size="{Math.round(size*0.33)}px"
    style:background={accent || 'var(--bg-subtle)'}
    style:color={accent ? '#fff' : 'var(--ink)'}
>
    {initials}
</div>

<style>
    .avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-family: var(--font-mono);
        font-weight: 600;
        flex-shrink: 0;
    }
</style>
