from os import urandom, environ
from dataclasses import dataclass
from typing import Optional

import tweepy
from cachetools import TTLCache
from base58 import b58encode, b58decode
from pydantic import BaseModel, BaseSettings
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from thingbox import __version__ as version
from thingbox.db import DB


class Config(BaseSettings):
	app_title: str
	app_base_url: str
	api_base_url: str
	twitter_api_key: str
	twitter_api_secret: str
	database_file: str
	private_key_b58: str
	auth_timeout: int = 303
	session_ttl: int = 3600
	admin_ttl: int = 900
	max_concurrent_auth_attempts: int = 8192
	max_concurrent_sessions: int = 65536
	max_admin_tokens: int = 32
	token_length_bytes: int = 32
	static_files_path: Optional[str] = None

	@property
	def twitter_api_credentials(self):
		return dict(consumer_key=self.twitter_api_key, consumer_secret=self.twitter_api_secret)


environment = environ.get('THINGBOX_ENV', 'dev')
config = Config(_env_file=f'{environment}.env')

app = FastAPI(
	title=config.app_title, version=version,
	docs_url=None, redoc_url=None
)

db = DB(filepath=config.database_file, private_key_bytes=b58decode(config.private_key_b58))

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['Authorization'])
auth_scheme = OAuth2PasswordBearer(tokenUrl='auth')
auth_sessions = TTLCache(maxsize=config.max_concurrent_auth_attempts, ttl=config.auth_timeout)
user_sessions = TTLCache(maxsize=config.max_concurrent_sessions, ttl=config.session_ttl)
admin_tokens = TTLCache(maxsize=config.max_admin_tokens, ttl=config.admin_ttl)


@dataclass
class UserSession:
	api: tweepy.API
	user: tweepy.User
	admin_token: Optional[str] = None


class AuthResponse(BaseModel):
	token: str
	redirect_url: str


class Item(BaseModel):
	target_type: str
	target_id: str
	item_encrypted_b64: str


def make_token():
	return b58encode(urandom(config.token_length_bytes)).decode('utf-8')


def user_is_authenticated(token: str=Depends(auth_scheme)):
	if token in user_sessions:
		return user_sessions[token]
	else:
		raise HTTPException(status_code=401)


def authenticated_user_is_admin(session: UserSession=Depends(user_is_authenticated)):
	if db.is_admin(user_type='twitter', user_id=session.user.id_str):
		return session
	else:
		raise HTTPException(status_code=403)


def api_token_is_admin_token(token: str=Depends(auth_scheme)):
	if (session := admin_tokens.get(token, None)) is not None:
		if db.is_admin(user_type='twitter', user_id=session.user.id_str):
			return session
		else:
			del admin_tokens[token]
			raise HTTPException(status_code=403)
	else:
		raise HTTPException(status_code=401)


@app.get('/auth')
def auth_begin():
	token = make_token()
	auth = tweepy.OAuthHandler(callback=f'{config.api_base_url}/auth-complete?token={token}', **config.twitter_api_credentials)
	auth_sessions[token] = auth
	url = auth.get_authorization_url(signin_with_twitter=True)
	return AuthResponse(token=token, redirect_url=url)


@app.get('/auth-complete')
def auth_complete(token: str, oauth_verifier: str):
	if token in user_sessions: del user_sessions[token]
	if token in auth_sessions:
		auth = auth_sessions.pop(token)
		auth.get_access_token(oauth_verifier)
		api = tweepy.API(auth)
		user = api.verify_credentials()
		user_sessions[token] = UserSession(api=api, user=user)
	return RedirectResponse(config.app_base_url)


@app.get('/user')
def get_items(session: UserSession=Depends(user_is_authenticated)):
	return JSONResponse(dict(
		screen_name=session.user.screen_name, 
		id=session.user.id_str,
		admin=db.is_admin(user_type='twitter', user_id=session.user.id_str)))


@app.get('/items')
def get_items(session: UserSession=Depends(user_is_authenticated)):
	return db.get_items('twitter', session.user.id_str)


@app.get('/public-key')
def get_public_key():
	return dict(public_key_b58=b58encode(db.get_public_key()).decode())


@app.get('/admin-token')
def get_admin_token(session: UserSession=Depends(authenticated_user_is_admin)):
	if session.admin_token in admin_tokens: del admin_tokens[session.admin_token]
	token = make_token()
	session.admin_token = token
	admin_tokens[token] = session
	return dict(admin_token=token)


@app.post('/items')
def post_item(item: Item, session: UserSession=Depends(api_token_is_admin_token)):
	db.add_item(**item.dict())


if config.static_files_path:
	app.mount("/", StaticFiles(directory=config.static_files_path, html=True), name="static")
