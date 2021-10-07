<script>
	export let checkUserItems
	
	let checkUserId = ''
	let checkResults = []
	
	async function doCheck() {
		checkResults = ['Querying items for: ' + checkUserId]
		checkResults = await checkUserItems(checkUserId)
		if (checkResults.length === 0) {
			checkResults = ['No items for: ' + checkUserId]
		}
	}
</script>

<section>
	<h3>Item check</h3>
	<p>Enter a user ID or screen name below to check what items are stored for that user.</p>
	<p><input bind:value={checkUserId}>&nbsp;&nbsp;<button on:click={doCheck}>Check items</button></p>
	{#each checkResults as lr}
		<pre>{typeof lr === 'string' ? lr : JSON.stringify(lr)}</pre>
	{/each}
</section>