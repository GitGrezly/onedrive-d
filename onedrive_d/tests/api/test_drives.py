import io
import unittest
from ciso8601 import parse_datetime

import requests
import requests_mock

from onedrive_d.api import drives
from onedrive_d.api import facets
from onedrive_d.api import items
from onedrive_d.api import options
from onedrive_d.api import resources
from onedrive_d.tests import get_data
from onedrive_d.tests.api import drive_factory


class TestDriveRoot(unittest.TestCase):
    def setUp(self):
        self.root = drive_factory.get_sample_drive_root()
        self.account = self.root.account

    def test_get_all_drives(self):
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                response_drives = [get_data('drive.json'), get_data('drive.json')]
                i = 0
                for x in response_drives:
                    x['id'] = str(i)
                    i += 1
                context.status_code = requests.codes.ok
                return {'value': response_drives}
            mock.get(self.account.client.API_URI + '/drives', json=callback)
            all_drives = self.root.get_all_drives()
            all_ids = [str(i) for i in range(0, 2)]
            for i, x in all_drives.items():
                self.assertIn(i, all_ids)
                self.assertIsInstance(x, drives.DriveObject)
                all_ids.remove(i)
            self.assertEqual(0, len(all_ids))


class TestDriveObject(unittest.TestCase):

    def setUp(self):
        self.drive = drive_factory.get_sample_drive_object()

    def test_get_root(self):
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                data = get_data('drive_root.json')
                context.status_code = requests.codes.ok
                return data
            mock.get(self.drive.drive_uri + '/root?expand=children', json=callback)
            root_item = self.drive.get_root_dir(list_children=True)
            self.assertIsInstance(root_item, items.OneDriveItem)

    def test_create_dir(self):
        """
        https://github.com/OneDrive/onedrive-api-docs/blob/master/items/create.md
        """
        folder_name = 'Documents'
        conflict_behavior = options.NameConflictBehavior.REPLACE
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                data = request.json()
                self.assertEqual(folder_name, data['name'])
                self.assertDictEqual({}, data['folder'])
                self.assertEqual(conflict_behavior, data['@name.conflictBehavior'])
                context.status_code = requests.codes.created
                return {
                    'id': '000aaa!100',
                    'name': folder_name,
                    'folder': {
                        'childCount': 0
                    }
                }
            mock.post(self.drive.get_item_uri(None, None), json=callback, status_code=requests.codes.created)
            item = self.drive.create_dir(name=folder_name, conflict_behavior=conflict_behavior)
            self.assertIsInstance(item, items.OneDriveItem)

    def test_delete_item(self):
        with requests_mock.Mocker() as mock:
            mock.delete(self.drive.get_item_uri(None, None), status_code=requests.codes.no_content)
            self.drive.delete_item()

    def test_update_root(self):
        self.assertRaises(ValueError, self.drive.update_item, None, None)

    def test_update_item(self):
        new_params = {
            'item_id': '123',
            'new_name': 'whatever.doc',
            'new_description': 'This is a dummy description.',
            'new_parent_reference': resources.ItemReference(drive_id='aaa', id='012'),
            'new_file_system_info': facets.FileSystemInfoFacet(
                created_time=parse_datetime('1971-01-01T02:03:04Z'),
                modified_time=parse_datetime('2008-01-02T03:04:05.06Z'))
        }
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                json = request.json()
                self.assertEqual(json['name'], new_params['new_name'])
                self.assertEqual(json['description'], new_params['new_description'])
                self.assertDictEqual(json['parentReference'], new_params['new_parent_reference']._data)
                self.assertDictEqual(json['fileSystemInfo'], new_params['new_file_system_info']._data)
                return get_data('image_item.json')

            mock.patch(self.drive.get_item_uri(new_params['item_id'], None), json=callback)
            self.drive.update_item(**new_params)

    def mock_download_file(self, range_bytes=None):
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                if range_bytes is not None:
                    self.assertEqual(request.headers['range'], 'bytes=%d-%d' % range_bytes)
                    context.status_code = requests.codes.partial
                else:
                    context.status_code = requests.codes.ok
                return b'hel'

            mock.get(self.drive.get_item_uri(item_id='123', item_path=None) + '/content', content=callback)
            self.drive.download_file(item_id='123', range_bytes=range_bytes)

    def test_download_partial_file(self):
        self.mock_download_file(range_bytes=(0, 4))

    def test_download_full_file(self):
        self.mock_download_file()

    def test_upload_small_file(self):
        self.drive.MAX_PUT_SIZE = 10
        input = io.BytesIO(b'12345')
        with requests_mock.Mocker() as mock:
            def callback(request, context):
                name = request.path_url.split('/')[-2][:-1]
                data = {
                    'id': 'abc',
                    'name': name,
                    'size': 5,
                    'file': {},
                }
                context.status_code = requests.codes.created
                return data

            mock.put(self.drive.get_item_uri('123', None) + ':/test:/content?@', json=callback)
            item = self.drive.upload_file('test', data=input, size=5, parent_id='123')
            self.assertEqual('test', item.name)
            self.assertEqual(5, item.size)

    def test_upload_large_file(self):
        self.drive.MAX_PUT_SIZE = 2
        session_url = 'https://foo/bar/accept_data'
        input = io.BytesIO(b'12345')
        output = io.BytesIO()
        expected_ranges = ['0-1/5', '2-3/5', '4-4/5']
        with requests_mock.Mocker() as mock:
            def create_session(request, context):
                context.status_code = requests.codes.ok
                return {
                    'uploadUrl': session_url,
                    'expirationDateTime': '2020-01-01T00:00:00.0Z',
                    'nextExpectedRanges': ['0-']
                }

            def accept_data(request, context):
                self.assertEqual(expected_ranges.pop(0), request.headers['Content-Range'])
                self.assertLessEqual(len(request.body), self.drive.MAX_PUT_SIZE)
                output.write(request.body)
                context.status_code = requests.codes.accepted
                return {
                    'uploadUrl': session_url,
                    'expirationDateTime': '2020-01-01T00:00:00.0Z',
                }

            mock.post(self.drive.get_item_uri(item_id='123', item_path=None) + ':/test:/upload.createSession',
                      json=create_session)
            mock.put(session_url, json=accept_data)
            self.drive.upload_file('test', data=input, size=5, parent_id='123')
            self.assertEqual(input.getvalue(), output.getvalue())


if __name__ == '__main__':
    unittest.main()
