import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import LoginChallenge, LoginSession, User, get_db
from services.auth_service import (
    CHALLENGE_COOKIE, CHALLENGE_SECONDS, GUEST_COOKIE, SESSION_COOKIE, SESSION_SECONDS,
    optional_user, set_cookie, token_hash, trusted_write, user_info, verify_google_credential,
)
from settings import google_client_id

router = APIRouter(prefix='/api/auth', tags=['auth'])


class GoogleLogin(BaseModel):
    credential: str = Field(min_length=1, max_length=16000)


@router.get('/me')
def me(user=Depends(optional_user)):
    return {'user': user_info(user), 'google_configured': bool(google_client_id())}


@router.post('/challenge', dependencies=[Depends(trusted_write)])
def challenge(request: Request, response: Response, db: Session = Depends(get_db)):
    if not google_client_id():
        raise HTTPException(503, '구글 로그인이 아직 준비되지 않았습니다.')
    now = int(time.time())
    db.execute(delete(LoginChallenge).where(LoginChallenge.expires_at <= now))
    previous = request.cookies.get(CHALLENGE_COOKIE)
    if previous:
        db.execute(delete(LoginChallenge).where(LoginChallenge.token_hash == token_hash(previous)))
    token, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(LoginChallenge(token_hash=token_hash(token), nonce_hash=token_hash(nonce), expires_at=now + CHALLENGE_SECONDS))
    db.commit()
    set_cookie(response, CHALLENGE_COOKIE, token, CHALLENGE_SECONDS)
    return {'client_id': google_client_id(), 'nonce': nonce}


@router.post('/google', dependencies=[Depends(trusted_write)])
def google_login(body: GoogleLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    cookie = request.cookies.get(CHALLENGE_COOKIE)
    challenge = db.get(LoginChallenge, token_hash(cookie)) if cookie else None
    now = int(time.time())
    if challenge is None or challenge.expires_at <= now:
        raise HTTPException(401, '로그인 준비 시간이 만료됐습니다. 다시 시도해 주세요.')
    claims = verify_google_credential(body.credential)
    if not secrets.compare_digest(challenge.nonce_hash, token_hash(claims['nonce'])):
        raise HTTPException(401, '로그인 요청을 확인할 수 없습니다. 다시 시도해 주세요.')
    # Atomic consumption stops concurrent replay of the same verified token.
    consumed = db.execute(delete(LoginChallenge).where(
        LoginChallenge.token_hash == challenge.token_hash, LoginChallenge.expires_at > int(time.time())
    ))
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(401, '이미 사용된 로그인 요청입니다.')
    user = db.scalar(select(User).where(User.google_sub == claims['sub']))
    if user is None:
        user = User(google_sub=claims['sub'])
        db.add(user)
    user.email = claims['email'][:320]
    user.name = str(claims.get('name') or '사용자')[:200]
    db.flush()
    old_token = request.cookies.get(SESSION_COOKIE)
    if old_token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(old_token)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=now + SESSION_SECONDS))
    db.commit()
    set_cookie(response, SESSION_COOKIE, token, SESSION_SECONDS)
    response.delete_cookie(CHALLENGE_COOKIE, path='/')
    return {'user': user_info(user)}


@router.post('/logout', dependencies=[Depends(trusted_write)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
    challenge = request.cookies.get(CHALLENGE_COOKIE)
    if challenge:
        db.execute(delete(LoginChallenge).where(LoginChallenge.token_hash == token_hash(challenge)))
    db.commit()
    for cookie in (SESSION_COOKIE, CHALLENGE_COOKIE, GUEST_COOKIE):
        response.delete_cookie(cookie, path='/')
    return {'ok': True}
