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
		{#if typeof lr === 'string' }
			<pre>{lr}</pre>
		{:else}
			<details>
				<summary>{lr.category} <span style="font-weight: normal;">(added {lr.created})</span></summary>
				<pre>{JSON.stringify(lr, 2)}</pre>
			</details>
		{/if}
	{/each}
</section>