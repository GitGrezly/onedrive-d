__author__ = 'xb'

import unittest

from onedrive_d.common import drive_config
from onedrive_d.tests import get_data


class TestDriveConfig(unittest.TestCase):
    data = get_data('drive_config.json')
    conf = drive_config.DriveConfig(data)

    def test_parse(self):
        for k, v in self.data.items():
            self.assertEqual(v, getattr(self.conf, k))

    def test_append_default_values(self):
        del self.data['max_get_size_bytes']
        conf = drive_config.DriveConfig(self.data)
        self.assertEqual(drive_config.DriveConfig.DEFAULT_VALUES['max_get_size_bytes'], conf.max_get_size_bytes)

    def test_serialize(self):
        dump = self.conf.dump()
        new_conf = drive_config.DriveConfig(dump)
        for k, v in self.data.items():
            self.assertEqual(v, getattr(new_conf, k))

    def test_set_default_config(self):
        """
        Test both setting default config and differential dumping / loading.
        """
        drive_config.DriveConfig.set_default_config(self.conf)
        data = dict(self.data)
        data['ignore_files'] = set(data['ignore_files'])
        data['ignore_files'].add('/q')
        data['proxies'] = {'sock5': '1.2.3.4:5'}
        conf2 = drive_config.DriveConfig(data)
        dump2 = conf2.dump()
        self.assertDictEqual({'ignore_files': ['/q'], 'proxies': {'sock5': '1.2.3.4:5'}}, dump2)
        conf3 = drive_config.DriveConfig.load(dump2)
        for k in self.data:
            self.assertEqual(getattr(conf2, k), getattr(conf3, k))


if __name__ == '__main__':
    unittest.main()
