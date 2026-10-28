import time
from pathlib import Path
import pytest
from password_auth import hash_password, verify_password, accounts, identity, fingerprint, LoginLimiter


@pytest.fixture(scope='module')
def account():
    return {'password_hash':hash_password('sample-test-password-123'), 'role':'editor'}


def test_hash_verification_salts_and_settings(account):
    assert verify_password('sample-test-password-123',account['password_hash'])
    assert not verify_password('wrong',account['password_hash'])
    assert not verify_password('sample-test-password-123','plaintext')
    assert account['password_hash']!=hash_password('sample-test-password-123')
    with pytest.raises(ValueError):hash_password('short')
    with pytest.raises(ValueError):accounts({'local_auth':{'users':{'admin':{'password_hash':'plaintext','role':'editor'}}}})


def test_sessions_expire_and_credentials_changes_revoke(account):
    users={'admin':account}
    ticket={'username':'admin','fingerprint':fingerprint(account),'expires':100}
    assert identity(ticket,users,99)==('admin','editor')
    assert identity(ticket,users,100) is None
    assert identity(ticket,{},99) is None
    assert identity(ticket,{'admin':{**account,'role':'viewer'}},99) is None
    assert identity(ticket,{'admin':{**account,'password_hash':hash_password('another-test-password')}},99) is None


def test_limiter_shared_window_and_global_cap():
    limiter=LoginLimiter()
    assert all(limiter.reserve('admin',0) for _ in range(5))
    assert not limiter.reserve('admin',1)
    assert limiter.reserve('admin',901)
    limiter.success('admin')
    assert limiter.reserve('admin',902)
    limiter=LoginLimiter()
    assert all(limiter.reserve(str(i),0) for i in range(100))
    assert not limiter.reserve('new',0)


def auth_app(account):
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_string('''
import streamlit as st
from login_ui import require_local, guard_fragment
user, role = require_local(dict(st.secrets))
st.write('AUTHENTICATED ' + user)
if role == 'editor': st.button('WRITE')
@st.fragment(run_every=15)
def private():
    guard_fragment()
    st.write('PROTECTED')
private()
''')
    app.secrets['storage']={'mode':'postgres'}
    app.secrets['login']={'method':'password'}
    app.secrets['local_auth']={'users':{'admin':account}}
    return app


def test_login_logout_and_viewer_ui(account):
    app=auth_app({**account,'role':'viewer'}).run()
    assert not app.exception
    assert not any('PROTECTED' in x.value for x in app.markdown)
    app.text_input[0].set_value('admin');app.text_input[1].set_value('wrong')
    app.button[0].click().run()
    assert app.error
    app.text_input[0].set_value('admin');app.text_input[1].set_value('sample-test-password-123')
    app.button[0].click().run()
    assert not app.exception
    assert any('PROTECTED' in x.value for x in app.markdown)
    assert not any(b.label=='WRITE' for b in app.button)
    app.sidebar.button[0].click().run()
    assert not any('PROTECTED' in x.value for x in app.markdown)
    assert len(app.text_input)==2


def test_expired_session_hides_content(account):
    app=auth_app(account)
    app.session_state['_login_ticket']={'username':'admin','fingerprint':fingerprint(account),'expires':time.time()-1}
    app.run()
    assert not app.exception
    assert not any('PROTECTED' in x.value for x in app.markdown)


def test_real_app_does_not_connect_db_before_login(account):
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
    app.secrets['storage']={'mode':'postgres'}
    app.secrets['database']={'url':'postgresql://unused:unused@invalid.invalid/db'}
    app.secrets['login']={'method':'password'}
    app.secrets['local_auth']={'users':{'admin':account}}
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.text_input)==2
    assert not app.metric
