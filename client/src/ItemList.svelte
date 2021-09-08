<script>
	const md = window.markdownit()
 	export let items = []
</script>

<section>
	{#if items && items.length > 0}
		<h2>Incentive rewards and messages</h2>
		{#each items as item }
			<article>{@html md.render(item)}</article>
		{/each}
	{:else}
		<h1>🏝</h1>
		<br>
		<h4>Nothing waiting for you.</h4>
		<br>
		<p>If you were expecting to find something here, head over to the <a href="https://vega.xyz/discord">Vega Discord server</a> and the friendly project team will try to get to the bottom of it.</p>
	{/if}
</section>