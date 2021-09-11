<script>
	import api from './api.js'
	import Itemlist from './ItemList.svelte'
	import Admin from './Admin.svelte'

	let items
	let authUrl
	let screenName = localStorage.getItem('screen_name')
	let isAdminUser
	let inAdminMode
	let serverPublicKey
	let adminToken
	let loginDenied
	let templates = null

	if (window.location.hash == '#logout') {
		logout()
	}

	if (window.location.hash == '#denied') {
		loginDenied = true
		logout()
	}

	async function getApiData() {
		try {
			({ screenName, admin: isAdminUser } = await api.getUser())
			if (isAdminUser && window.location.hash === '#admin') {
				inAdminMode = true
			}
			if (inAdminMode) {
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
		if (inAdminMode && templates === null) {
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
			<h1>Fairground incentives 🎡</h1>
			{#if screenName} 
				<p>	
					<a on:click|preventDefault={logout} href="#logout">Log out @{screenName}</a> / <a href="#switch-account" on:click|preventDefault={switchAccount}>change account</a>
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
			<p>Sign in with Twitter to access your Fairground incentives claim links. You must use the same Twitter account that you used to register with Vega Fairground.</p>
			{#if authUrl}
				<p>👉 <a href={authUrl}>Connect my Twitter account</a></p>
			{/if}
		</section>
	{:else if items !== undefined && !inAdminMode}
		<Itemlist {items} />
	{:else if items !== undefined && inAdminMode}
		<Admin {serverPublicKey} {adminToken} {generateAdminToken} {clearTemplateCache} {templates} />
	{/if}
	<footer><section><p>&copy; 2021 Gobalsky Labs Ltd. Made with 💛 and 🦔 by the Vega project team. <a href="https://vega.xyz/privacy/">Privacy</a>.</p></section></footer>
</main>

<style>
</style>
