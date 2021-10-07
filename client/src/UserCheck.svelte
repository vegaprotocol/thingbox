<script>
	export let checkUserItems
	
	let checkUserId = ''
	let checkResults = []
	let	checkUserInput
	
	async function doCheck() {
		checkResults = ['Querying items for: ' + checkUserId]
		checkResults = await checkUserItems(checkUserId)
		if (checkResults.length === 0) {
			checkResults = ['No items for: ' + checkUserId]
		}
		checkUserInput.focus()
		checkUserInput.select()
	}
</script>

<section>
	<h3>Item check</h3>
	<p>Enter a user ID or screen name below to check what items are stored for that user.</p>
	<form><p><input bind:this={checkUserInput} bind:value={checkUserId}>&nbsp;&nbsp;<button type="submit" on:click|preventDefault={doCheck}>Check items</button></p></form>
	{#each checkResults as lr}
		<pre>{typeof lr === 'string' ? lr : JSON.stringify(lr)}</pre>
	{/each}
</section>