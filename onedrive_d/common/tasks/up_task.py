import os

from onedrive_d import timestamp_to_datetime
from onedrive_d.api import errors
from onedrive_d.api import facets
from onedrive_d.api.options import NameConflictBehavior
from onedrive_d.common.tasks import TaskBase
from onedrive_d.store.items_db import ItemRecordStatuses


class UpTaskBase(TaskBase):
    def __init__(self, parent_task, rel_parent_path, item_name, conflict_behavior):
        super().__init__(parent_task)
        self.rel_parent_path = rel_parent_path
        self.item_name = item_name
        self._conflict_behavior = conflict_behavior

    def handle(self):
        raise NotImplementedError()


class UploadFileTask(UpTaskBase):
    def __init__(self, parent_task, rel_parent_path, item_name, conflict_behavior=NameConflictBehavior.REPLACE):
        super().__init__(parent_task, rel_parent_path, item_name, conflict_behavior)

    def handle(self):
        try:
            size = os.path.getsize(self.local_path)
            with open(self.local_path, 'rb') as f:
                item = self.drive.upload_file(
                        filename=self.item_name, data=f, size=size, parent_path=self.remote_parent_path,
                        conflict_behavior=self._conflict_behavior)
                modified_time = timestamp_to_datetime(os.path.getmtime(self.local_path))
                fs_info = facets.FileSystemInfoFacet(modified_time=modified_time)
                item = self.drive.update_item(item_id=item.id, new_file_system_info=fs_info)
                self.items_store.update_item(item, ItemRecordStatuses.OK)
                self.logger.info('Uploaded file "%s".', self.local_path)
        except Exception as e:
            self.logger.error('Error occurred when uploading "%s": %s.', self.local_path, e)


class UpdateMetadataTask(UpTaskBase):
    def __init__(self, parent_task, rel_parent_path, item_name, new_mtime):
        super().__init__(parent_task, rel_parent_path, item_name, None)
        if isinstance(new_mtime, int):
            new_mtime = timestamp_to_datetime(new_mtime)
        self._new_mtime = new_mtime

    def handle(self):
        try:
            fs_info = facets.FileSystemInfoFacet(modified_time=self._new_mtime)
            new_item = self.drive.update_item(item_path=self.remote_path, new_file_system_info=fs_info)
            self.items_store.update_item(new_item, ItemRecordStatuses.OK)
        except errors.OneDriveError as e:
            self.logger.error('Error occurred updating server mtime for entry "%s": %s', self.local_path, e)