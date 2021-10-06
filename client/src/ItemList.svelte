<script>
	import { content } from './content.js'
	import { md } from './md.js'

	export let items = []
</script>

<section>
	{#if items && items.length > 0}
		{@html md.render($content['site-home-normal'])}
		{#each items as item }
			<article>{@html md.render(item)}</article>
		{/each}
	{:else}
		{@html md.render($content['site-home-empty'])}
	{/if}
</section>