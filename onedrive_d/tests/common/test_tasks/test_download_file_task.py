__author__ = 'xb'

import unittest

try:
    from unittest import mock
except:
    import mock

from requests import codes
from requests_mock import Mocker

from onedrive_d import datetime_to_timestamp
from onedrive_d.api import items
from onedrive_d.common import tasks
from onedrive_d.tests import get_data
from onedrive_d.tests.common import test_tasks


class TestDownloadFileTask(test_tasks.BaseTestCase, unittest.TestCase):
    def setUp(self):
        super().setup_objects()
        item_data = get_data('image_item.json')
        item_data['name'] = 'test'
        item_data['size'] = 1
        self.item = items.OneDriveItem(self.drive, item_data)
        self.task = tasks.DownloadFileTask(self.task_base, item=self.item)
        self.file_path = self.drive.config.local_root + '/test'
        self.tmp_file_path = self.drive.config.local_root + '/' + self.task.get_temp_filename()

    @Mocker()
    def test_handle(self, mock_request):
        mock_request.get(self.drive.drive_uri + self.drive.drive_path + '/items/' + self.item.id + '/content',
                         content=b'1', status_code=codes.ok)
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            self.task.handle()
        m.assert_called_once_with(self.tmp_file_path, 'wb')
        handle = m()
        handle.write.assert_called_once_with(b'1')
        self.assertEqual(1, len(self.utime_records))
        self.assertIn(self.file_path, self.utime_records)
        ts = datetime_to_timestamp(self.item.modified_time)
        self.assertEqual((ts, ts), self.utime_records[self.file_path])


if __name__ == '__main__':
    unittest.main()
