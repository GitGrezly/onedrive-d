import json
import re
import unittest

import requests
import requests_mock

from onedrive_d.api import accounts
from onedrive_d.api import errors
from onedrive_d.tests import get_data
from onedrive_d.tests.api.account_factory import personal_account_data as data
from onedrive_d.tests.api.account_factory import get_sample_personal_account as get_sample_account
from onedrive_d.tests.api.client_factory import get_sample_personal_client as get_sample_client


class TestPersonalAccount(unittest.TestCase):
    # Sample data acquired from
    # https://github.com/OneDrive/onedrive-api-docs/blob/master/auth/msa_oauth.md

    DEFAULT_CALL_ARGS = {
        'code': '123'
    }

    new_data = get_data('personal_access_token_alt.json')

    def assert_account(self, account):
        """
        :param onedrive_d.api.accounts.PersonalAccount account:
        """
        self.assertIsInstance(account, accounts.PersonalAccount)
        self.assertEqual(data['access_token'], account.access_token)
        self.assertEqual(data['refresh_token'], account.refresh_token)
        self.assertEqual(data['token_type'], account.token_type)
        self.assertEqual(2, len(account.scope))
        self.assertIn('wl.basic', account.scope)
        self.assertIn('onedrive.readwrite', account.scope)
        self.assertGreater(account.expires_at, data['expires_in'])

    def assert_new_tokens(self, account):
        self.assertEqual(self.new_data['access_token'], account.access_token)
        self.assertEqual(self.new_data['refresh_token'], account.refresh_token)
        self.assertEqual(self.new_data['token_type'], account.token_type)
        self.assertEqual(3, len(account.scope))
        self.assertIn('a', account.scope)
        self.assertIn('b', account.scope)
        self.assertIn('c', account.scope)

    def test_get_account_fail_no_code(self):
        client = get_sample_client()
        self.assertRaises(ValueError, accounts.get_personal_account, client, uri='http://foo/bar?error=123')

    def test_get_account_fail_bad_code(self):
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                self.assertIn('code=123', request.text)
                context.status_code = requests.codes.bad
                return {
                    'error': 'dummy error',
                    'error_description': 'dummy description'
                }
            mock.post(re.compile('//login\.live\.com\.*'), json=callback)
            client = get_sample_client()
            self.assertRaises(ValueError, accounts.get_personal_account, client, uri='http://foo/bar?code=123')

    def test_get_account_success_by_code(self, args=DEFAULT_CALL_ARGS):
        """
        Test get_personal_account() by passing it a code.
        :param dict[str, str] args: Arguments to pass to get_personal_account().
        """
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                self.assertIn('code=123', request.text)
                return data
            mock.post(re.compile('//login\.live\.com\.*'), json=callback, status_code=requests.codes.ok)
            client = get_sample_client()
            account = accounts.get_personal_account(client, **args)
            self.assert_account(account)

    def test_get_account_success_by_uri(self):
        """
        Test get_personal_account() by passing it a URL which contains a code in query string.
        """
        args = {
            'uri': 'http://foo/bar?code=123'
        }
        self.test_get_account_success_by_code(args)

    def test_parse_expire_time(self):
        expires_at = 1234
        client = get_sample_client()
        account = accounts.PersonalAccount(client, data, expires_at)
        self.assertEqual(expires_at, account.expires_at)

    def test_load_session(self):
        account = get_sample_account()
        account.load_session(self.new_data)
        self.assert_new_tokens(account)

    def test_renew_session(self):
        account = get_sample_account()
        old_expire_at = account.expires_at
        with requests_mock.Mocker() as mock:
            mock.post(account.client.OAUTH_TOKEN_URI, json=self.new_data, status_code=requests.codes.ok)
            account.renew_tokens()
            self.assert_new_tokens(account)
            self.assertGreater(account.expires_at, old_expire_at)

    def test_renew_session_failure(self):
        account = get_sample_account()
        with requests_mock.Mocker() as mock:
            mock.post(account.client.OAUTH_TOKEN_URI, json=get_data('error_type1.json'), status_code=requests.codes.bad)
            self.assertRaises(errors.OneDriveError, account.renew_tokens)

    def test_dump(self):
        account = get_sample_account()
        dump = account.dump()
        self.assertIsInstance(dump, str)
        data = json.loads(dump)
        data['client'] = account.client
        account_restore = accounts.PersonalAccount(**data)
        self.assertEqual(account.access_token, account_restore.access_token)
        self.assertEqual(account.refresh_token, account_restore.refresh_token)
        self.assertEqual(account.expires_at, account_restore.expires_at)


if __name__ == '__main__':
    unittest.main()
