import json
from os import urandom, environ
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

import tweepy
import chevron
from cachetools import TTLCache, LRUCache
from base58 import b58encode, b58decode
from pydantic import BaseModel, BaseSettings
from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from thingbox import __version__ as version
from thingbox.db import DB, BackupConfig

TEMPLATE_GLOBALS = { 
	'include': lambda template_id, render: render(db.get_site_content(template_id).get(template_id, f'<mark>«Missing: {template_id}»</mark>')),
	'decimal_amount': lambda x, render: f'{float(render(x)) / 10 ** 18:.2f}',
	'iso_date': lambda x, render: datetime.fromisoformat(render(x).replace('Z', '+00:00')).strftime('%-d %B %Y'),
	'unix_date': lambda x, render: datetime.fromtimestamp(render(x)).strftime('%-d %B %Y')
}


class Config(BaseSettings):
	app_title: str
	app_base_url: str
	api_base_url: str
	twitter_api_key: str
	twitter_api_secret: str
	database_file: str
	private_key_b58: str
	backup_path: Optional[str] = None
	backup_interval: Optional[int] = None
	backup_tmp_path: Optional[str] = None
	backup_on_batch_close: bool = False
	auth_timeout: int = 303
	session_ttl: int = 3600
	admin_ttl: int = 900
	max_concurrent_auth_attempts: int = 8192
	max_concurrent_sessions: int = 65536
	max_admin_tokens: int = 32
	token_length_bytes: int = 32
	id_length_bytes: int = 16
	template_cache_size: int = 64
	static_files_path: Optional[str] = None

	@property
	def twitter_api_credentials(self):
		return dict(consumer_key=self.twitter_api_key, consumer_secret=self.twitter_api_secret)


environment = environ.get('THINGBOX_ENV', 'dev')
config = Config(_env_file=f'{environment}.env')

if config.private_key_b58[:11] == 'gcp_secret:':
	from google.cloud import secretmanager
	client = secretmanager.SecretManagerServiceClient()
	gcp_secret_name = config.private_key_b58[11:]
	response = client.access_secret_version(name=gcp_secret_name)
	config.private_key_b58 = response.payload.data.decode("UTF-8")
	print('** Loaded private key from GCP secret **')


app = FastAPI(
	title=config.app_title, version=version,
	docs_url=None, redoc_url=None
)

db_backup_config = BackupConfig(
	backup_path=config.backup_path,
	tmp_path=config.backup_tmp_path,
	backup_interval=config.backup_interval,
	backup_on_batch_close=True,
	name_template='thingbox_db_backup_{timestamp}.db'
) if config.backup_path else None

db = DB(
	filepath=config.database_file,
	private_key_bytes=b58decode(config.private_key_b58), 
	id_len_bytes=config.id_length_bytes,
	backup_config=db_backup_config)

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['Authorization'])
auth_scheme = OAuth2PasswordBearer(tokenUrl='auth')

auth_sessions = TTLCache(maxsize=config.max_concurrent_auth_attempts, ttl=config.auth_timeout)
user_sessions = TTLCache(maxsize=config.max_concurrent_sessions, ttl=config.session_ttl)
admin_tokens = TTLCache(maxsize=config.max_admin_tokens, ttl=config.admin_ttl)
template_cache = LRUCache(maxsize=config.template_cache_size)


@dataclass
class UserSession:
	api: tweepy.API
	user: tweepy.User
	admin_token: Optional[str] = None
	admin_id: Optional[int] = None


class AuthResponse(BaseModel):
	token: str
	redirect_url: str


class Item(BaseModel):
	target_type: str
	target_id: str
	category: str
	data_encrypted_b64: str
	template: str
	batch: str = None


def make_token():
	return b58encode(urandom(config.token_length_bytes)).decode('utf-8')


def get_template_cached(template):
	if template in template_cache: return template_cache[template]
	if content := db.get_template(template):
		template_cache[template] = content
		return content


def user_is_authenticated(token: str=Depends(auth_scheme)):
	if token in user_sessions:
		return user_sessions[token]
	else:
		raise HTTPException(status_code=401)


def authenticated_user_is_admin(session: UserSession=Depends(user_is_authenticated)):
	if (admin_id := db.is_admin(user_type='twitter', user_id=session.user.id_str)):
		session.admin_id = admin_id
		return session
	else:
		raise HTTPException(status_code=403)


def api_token_is_admin_token(token: str=Depends(auth_scheme)):
	if (session := admin_tokens.get(token, None)) is not None:
		if (admin_id := db.is_admin(user_type='twitter', user_id=session.user.id_str)):
			session.admin_id = admin_id
			return session
		else:
			del admin_tokens[token]
			raise HTTPException(status_code=403)
	else:
		raise HTTPException(status_code=401)


@app.get('/auth')
def auth_begin(switch: Optional[bool] = False):
	token = make_token()
	auth = tweepy.OAuthHandler(callback=f'{config.api_base_url}/auth-complete?token={token}', **config.twitter_api_credentials)
	auth_sessions[token] = auth
	url = auth.get_authorization_url(signin_with_twitter=True) + ('&force_login=true' if switch else '')
	return AuthResponse(token=token, redirect_url=url)


@app.get('/auth-complete')
def auth_complete(token: str, oauth_verifier: Optional[str] = None, denied: Optional[str] = None):
	if token in user_sessions: del user_sessions[token]
	if token in auth_sessions:
		auth = auth_sessions.pop(token)
		if oauth_verifier and not denied:
			auth.get_access_token(oauth_verifier)
			api = tweepy.API(auth)
			user = api.verify_credentials()
			user_sessions[token] = UserSession(api=api, user=user)
	return RedirectResponse(config.app_base_url + ('/#denied' if denied else ''))


@app.get('/user')
def get_items(session: UserSession=Depends(user_is_authenticated)):
	return JSONResponse(dict(
		screen_name=session.user.screen_name, 
		id=session.user.id_str,
		admin=db.is_admin(user_type='twitter', user_id=session.user.id_str)))


@app.get('/items')
def get_items(session: UserSession=Depends(user_is_authenticated)):
	result = db.get_items('twitter', session.user.id_str)
	items = []
	for r in filter(lambda r: r is not None, result):
		try:
			items.append(chevron.render(template=get_template_cached(r['template_id']), data={ **json.loads(r['data']), **TEMPLATE_GLOBALS}))
		except Exception as e:
			print(f'Template error rendering item {r["id"]} in template: {r["template_id"]}')
			print(e)
			items.append(f'<p class="no-title">Template error rendering item with ID: {r["id"]}</p>')
	return items


@app.post('/items')
def post_item(item: Item, batch: Optional[str] = None, close_batch: Optional[bool] = True, session: UserSession=Depends(api_token_is_admin_token)):
	if batch is None: batch = db.create_or_check_batch(admin=session.admin_id, batch=batch)
	if not batch: raise HTTPException(status_code=400, detail='error creating batch, is user an admin?')
	if not db.get_template(item.template): db.add_template(item.template, f'New template: {item.template}')
	res = db.add_item(**{ **item.dict(), **dict(batch=batch) })
	if close_batch: db.close_batch(batch)
	return { **dict(batch=batch, success=res), **(dict(error=f'error creating item, ensure template exists: {item.template}') if not res else {}) }


@app.get('/public-key')
def get_public_key():
	return dict(public_key_b58=b58encode(db.get_public_key().encode()).decode())


@app.get('/clear-template-cache')
def clear_template_cache(session: UserSession=Depends(authenticated_user_is_admin)):
	num_cleared = len(template_cache)
	template_cache.clear()
	return dict(cleared=num_cleared)


@app.get('/admin-token')
def get_admin_token(session: UserSession=Depends(authenticated_user_is_admin)):
	if session.admin_token in admin_tokens: del admin_tokens[session.admin_token]
	token = make_token()
	session.admin_token = token
	admin_tokens[token] = session
	return dict(admin_token=token)


@app.get('/templates')
def get_templates(session: UserSession=Depends(authenticated_user_is_admin)):
	return db.get_templates()

@app.get('/templates/{template_id}')
def get_template(template_id, session: UserSession=Depends(authenticated_user_is_admin)):
	if (res := db.get_template(template=template_id)) == None:
		raise HTTPException(status_code=404, detail=f'No template with id {template_id}')
	else:
		return res

@app.post('/templates/{template_id}')
def create_template(template_id, content: str = Body(default=None), session: UserSession=Depends(authenticated_user_is_admin)):
	if content is None: raise HTTPException(status_code=400, detail='Template content required in request body')
	success = db.add_template(template_id=template_id, content=content)
	if success: template_cache.clear()
	return dict(success=success)

@app.put('/templates/{template_id}')
def update_template(template_id, type: str = 'item', content: str = Body(default=None), session: UserSession=Depends(authenticated_user_is_admin)):
	if content is None: raise HTTPException(status_code=400, detail='Template content required in request body')
	success = db.update_template(template_id=template_id, content=content, type=type)
	if success: template_cache.clear()
	return dict(success=success)

@app.get('/content')
def get_site_content(id: List[str] = Query([])):
	return db.get_site_content_multi(ids=id)

@app.get('/content/{id}')
def get_site_content(id: str):
	return db.get_site_content_multi(ids=[id])

if config.static_files_path:
	app.mount("/", StaticFiles(directory=config.static_files_path, html=True), name="static")
