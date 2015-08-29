__author__ = 'xb'

import atexit
import sqlite3

from onedrive_d import get_content
from onedrive_d.api import drives
from onedrive_d.common import logger_factory


class DriveStorage:
    logger = logger_factory.get_logger('DriveStorage')

    def __init__(self, db_path, account_store):
        """
        :param str db_path: Path to Drive database.
        :param onedrive_d.store.account_db.AccountStorage account_store:
        """
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._cursor = self._conn.cursor()
        self._cursor.execute(get_content('onedrive_drives.sql'))
        self._conn.commit()
        self._all_drives = {}
        self._drive_roots = {}
        self.account_store = account_store
        atexit.register(self.close)

    @staticmethod
    def get_key(drive_id, account_id, account_type):
        return drive_id, account_id, account_type

    def assemble_drive_record(self, row, container):
        drive_id, account_id, account_type, drive_dump = row
        try:
            drive_root = self.get_drive_root(account_id, account_type)
        except KeyError:
            self.logger.warning('The %s account %s for drive %s was not registered.', account_type,
                                account_id, drive_id)
            return
        try:
            drive = drives.DriveObject.load(drive_root, account_id, account_type, drive_dump)
            container[self.get_key(drive.drive_id, account_id, account_type)] = drive
        except ValueError as e:
            self.logger.warning('Cannot load drive %s from database: %s', drive_id, e)

    def get_drive_root(self, account_id, account_type):
        key = (account_id, account_type)
        if key not in self._drive_roots:
            self._drive_roots[key] = drives.DriveRoot(self.account_store.get_account(account_id, account_type))
        return self._drive_roots[key]

    def get_all_drives(self):
        self._conn.commit()
        q = self._cursor.execute('SELECT drive_id, account_id, account_type, drive_dump FROM drives')
        for row in q.fetchall():
            self.assemble_drive_record(row, self._all_drives)
        return self._all_drives

    def add_record(self, drive):
        account = drive.root.account
        params = (drive.drive_id, account.profile.user_id, account.TYPE, drive.config.local_root, drive.dump())
        self._cursor.execute('INSERT OR REPLACE INTO drives (drive_id, account_id, account_type, local_root, '
                             'drive_dump) VALUES (?,?,?,?,?)', params)
        self._conn.commit()

    def delete_record(self, drive):
        self._cursor.execute('DELETE FROM drives WHERE drive_id=? AND account_id=? AND account_type=?',
                             (drive.drive_id, drive.root.account.id, drive.root.account.TYPE))
        self._conn.commit()

    def close(self):
        self._conn.commit()
        self._cursor.close()
        self._conn.close()
