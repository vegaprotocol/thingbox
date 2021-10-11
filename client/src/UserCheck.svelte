<script>
	export let checkUserItems
	
	let checkUserId = ''
	let checkResults = []
	let	checkUserInput
	
	async function doCheck() {
		if (checkUserId.trim() === '') return
		checkResults = ['Querying items for: ' + checkUserId]
		try {
			checkResults = await checkUserItems(checkUserId)
			if (checkResults.filter(x => typeof x !== 'string').length === 0) {
				checkResults.push('No results for: ' + checkUserId)
			}
		} 
		catch(e) {
			checkResults = ['Error checking items: ' + e.toString()]
		}
		checkUserInput.focus()
		checkUserInput.select()
	}
</script>

<section>
	<h3>Item check</h3>
	<p>Enter a user ID or screen name to check what items are stored for that user.</p>
	<form><p><input bind:this={checkUserInput} bind:value={checkUserId} on:focus={()=>checkUserInput.select()}>&nbsp;&nbsp;<button type="submit" on:click|preventDefault={doCheck}>Check</button></p></form>
	{#each checkResults as lr}
		{#if typeof lr === 'string' }
			<pre>{lr}</pre>
		{:else}
			<details>
				<summary>{lr.category} <span style="font-weight: normal;">(added {lr.created})</span></summary>
				<pre>{JSON.stringify(lr)}</pre>
			</details>
		{/if}
	{/each}
</section>