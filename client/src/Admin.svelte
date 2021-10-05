<script>
import { trusted } from "svelte/internal";


	export let serverPublicKey
	export let adminToken
	export let generateAdminToken
	export let clearTemplateCache
	export let templates
	export let updateTemplate
	
	let templateData = {}
	for (let t of templates || []) {
		templateData[t.id] = {
			id: t.id,
			type: t.type,
			editing: false,
			original: t.content,
			edited: t.content.slice(),
			changed() { return this.original !== this.edited },
			actionText() {
				if (!this.editing) return 'edit'
				else if (!this.changed()) return 'cancel'
				else return 'save'
			}
		}
	}

	async function cancelEdit(e) {
		const templateId = e.target.dataset.templateId
		const td = templateData[templateId]
		if (td.editing) {
			td.edited = td.original.slice()
			td.editing = false
			templateData[templateId] = td
		}
	}

	async function editTemplate(e) {
		const templateId = e.target.dataset.templateId
		const td = templateData[templateId]
		if (td.actionText() === 'save') {
			try {
				const res = await updateTemplate(td.id, td.edited)
				if (res) {
					td.original = td.edited.slice()
					td.editing = !td.editing
				}
				else {
					alert(`Did NOT save template, check template ID (${td.id}) exists`)
				}
			}
			catch (e) {
				alert('Error saving template\n\n' + e.toString())
			}
		}
		else {
			td.editing = !td.editing
		}
		templateData[td.id] = td
	}
</script>

<section>
	<h2>Admin tools</h2>
	<h3>Server public key</h3>
	<p>Items are encrypted at rest and must be encrypted to this ed25519 public key before uploading. Unencrypted items will be rejected by the server.</p>
	<pre>{serverPublicKey}</pre>
	<h3>Admin API token</h3>
	<p>Using the API to manage items requires an authentication token which can be generated here. For security, these generally have a short lifespan. </p>
	{#if adminToken}
		<details>
			<summary>View secret admin token</summary>
			<pre>{ adminToken }</pre>
		</details>
	{:else}
		<p><button on:click={generateAdminToken}>Generate API token</button></p>
	{/if}
	<br>
	<h3>Content</h3>
	{#each Object.values(templateData) as td}
		<details>
			<summary>{td.id} <span style="font-weight: normal;">({td.type} template)</span>
				<span class="editlink">
					<a href="#edit/{td.id}" on:click|preventDefault={editTemplate} data-template-id={td.id}>{td.actionText()}</a>&nbsp;
					{#if td.actionText() ===  'save'}<a href="#cancel/{td.id}" on:click|preventDefault={cancelEdit} data-template-id={td.id}>cancel</a>{/if}
				</span>
			</summary>
			{#if td.editing}
				<textarea bind:value={td.edited}></textarea>
			{:else}
				<pre contenteditable="false">{td.original}</pre>
			{/if}
		</details>
	{/each}
	<p><button on:click={clearTemplateCache}>Clear template cache</button></p>
</section>