import time
import streamlit as st
from password_auth import accounts, identity, fingerprint, verify_password, LoginLimiter, SESSION_SECONDS, hash_password


@st.cache_resource
def limiter():
    return LoginLimiter()


@st.cache_resource
def dummy_hash():
    return hash_password('not-a-user-password-placeholder')


def require_local(settings):
    try:
        users = accounts(settings)
    except ValueError as exc:
        st.error(str(exc)); st.stop()
    current = identity(st.session_state.get('_login_ticket'), users)
    if current:
        if st.sidebar.button('로그아웃'):
            st.session_state.clear();st.rerun()
        return current
    if '_login_ticket' in st.session_state:
        st.session_state.clear()
        st.info('로그인이 만료되었거나 계정 설정이 변경되었습니다. 다시 로그인해주세요.')
    st.subheader('아이디·비밀번호 로그인')
    with st.form('local_login', clear_on_submit=True):
        username = st.text_input('아이디', max_chars=64).strip().lower()
        password = st.text_input('비밀번호', type='password', max_chars=256)
        submitted = st.form_submit_button('로그인')
    if submitted:
        account = users.get(username)
        key = username if account else '<unknown>'
        if not limiter().reserve(key):
            st.error('로그인 시도가 많습니다. 15분 후 다시 시도해주세요.')
        elif verify_password(password, account['password_hash'] if account else dummy_hash()) and account:
            limiter().success(key)
            st.session_state['_login_ticket'] = {'username': username, 'fingerprint': fingerprint(account), 'expires': time.time()+SESSION_SECONDS}
            st.rerun()
        else:
            st.error('아이디 또는 비밀번호가 올바르지 않습니다.')
    st.caption('로그인은 최대 8시간 유지됩니다. 브라우저 새로고침이나 세션 종료 시 다시 로그인해야 할 수 있습니다.')
    st.stop()


def guard_fragment():
    """Fragments rerun without the main app: recheck login before reading data."""
    try:
        settings = dict(st.secrets)
    except FileNotFoundError:
        return
    if settings.get('storage', {}).get('mode') != 'postgres' or settings.get('login', {}).get('method', 'oidc') != 'password':
        return
    try:
        allowed = accounts(settings)
        valid = identity(st.session_state.get('_login_ticket'), allowed)
    except ValueError:
        valid = None
    if valid is None:
        st.session_state.clear()
        st.rerun(scope='app')
