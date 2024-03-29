<script>
	import { md } from './md.js'
	import api from './api.js'
	import { content } from './content.js'
	import Itemlist from './ItemList.svelte'
	import Admin from './Admin.svelte'
	import UserCheck from './UserCheck.svelte'

	let items
	let authUrl
	let screenName = localStorage.getItem('screen_name')
	let isAdminUser
	let adminIsEditor
	let inAdminMode
	let adminToken
	let loginDenied
	let templates = null

	function checkLocationHash() {
		if (window.location.hash == '#logout') {
			logout()
		}
		else if (window.location.hash == '#denied') {
			loginDenied = true
			logout()
		}
		else if (window.location.hash == '#switch-account') {
			switchAccount()
		}
	}

	window.addEventListener('hashchange', checkLocationHash)
	// checkLocationHash()

	async function getApiData() {
		try {
			({ screenName, admin: isAdminUser, editor: adminIsEditor } = await api.getUser())
			if (isAdminUser && window.location.hash === '#admin') {
				inAdminMode = true
			}
			if (adminIsEditor) {
				console.log('editor');
				templates = await api.getTemplates()
			}
			if (screenName) {
				localStorage.setItem('screen_name', screenName)
			}
			items = await api.getItems()
			serverPublicKey = await api.getPublicKey()
		}
		catch (e) {
			if (e.message === 'unauthorised') {
				localStorage.removeItem('screen_name')
				screenName = null
				authUrl = await api.auth()	
			}
		}
	}

	async function logout() {
		await api.logout()
		authUrl = await api.auth()
		screenName = null
		items = null
	}

	async function switchAccount() {
		await api.logout()
		authUrl = await api.auth(true)
		screenName = null
		items = null
	}

	async function toggleAdminMode() {
		inAdminMode = !inAdminMode
		window.location.hash = inAdminMode ? '#admin' : '#'
		if (inAdminMode && adminIsEditor && templates === null) {
			templates = await api.getTemplates() 
		}
	}

	async function generateAdminToken() {
		if (!inAdminMode) return null
		try {
			adminToken = await api.getAdminToken()
		}
		catch {
			await getApiData()
			return null
		}
	}

	async function clearTemplateCache() {
		if (!inAdminMode) return null
		try {
			await api.clearTemplateCache()
		}
		catch {
			await getApiData()
			return null
		}
	}

	getApiData()

</script>

<main>
	<header>
		<nav>
			{@html md.render($content['site-title'])}
			{#if screenName} 
				<p>	
					<a on:click|preventDefault={logout} href="#logout">Log out @{screenName}</a> / <a href="#switch-account">change account</a>
					{#if isAdminUser}
					/ <a href={inAdminMode ? '#home' : '#admin'} on:click|preventDefault={toggleAdminMode}>{inAdminMode ? 'home' : 'admin'}</a>
					{/if}
				</p>
			{/if}
		</nav>
	</header>
	{#if !screenName || authUrl}
		<section>
			{#if loginDenied}
				<p class="warning">Login failed or cancelled, try again.</p>
			{/if}
			{@html md.render($content['site-home-logged-out'])}
			{#if authUrl}
				<p>👉 <a href={authUrl}>Connect my Twitter account</a></p>
			{:else}
				<p>😿 Server failed to initialise authentication. Contact an admin.</p>
			{/if}
		</section>
	{:else if items !== undefined && !inAdminMode}
		<Itemlist {items} />
	{:else if items !== undefined && inAdminMode}
		<h2>Admin tools</h2>
		<UserCheck checkUserItems={api.checkUserItems} />
		{#if adminIsEditor}
			<Admin {adminToken} {generateAdminToken} {clearTemplateCache} {templates} updateTemplate={api.updateTemplate} />
		{/if}
	{/if}
	<footer><section>{@html md.render($content['site-footer'])}</section></footer>
</main>

<style>
</style>
