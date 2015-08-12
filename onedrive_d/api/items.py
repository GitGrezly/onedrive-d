from ciso8601 import parse_datetime

from . import resources
from . import facets


class OneDriveItemTypes:
    FILE = 'file'
    FOLDER = 'folder'
    IMAGE = 'image'
    PHOTO = 'photo'
    AUDIO = 'audio'
    VIDEO = 'video'
    ALL = [FOLDER, IMAGE, PHOTO, AUDIO, VIDEO, FILE]  # Order matters.


class ItemCollection:
    def __init__(self, drive, data):
        self._drive = drive
        self._data = data
        self._page_count = 0

    @property
    def has_next(self):
        """
        :return True | False: Whether or not there are more sets to fetch.
        """
        return '@odata.nextLink' in self._data

    def get_next(self):
        """
        :return [onedrive_d.api.items.OneDriveItem]: Assuming there is at least one more set, return a list of
        OneDriveItems.
        """
        if self._page_count > 0:
            request = self._drive.root.account.session.get(self._data['@odata.nextLink'])
            self._data = request.json()
        self._page_count += 1
        return [OneDriveItem(self._drive, d) for d in self._data['value']]


class OneDriveItem:
    def __init__(self, drive, data):
        """
        :param onedrive_d.api.drives.DriveObject drive: The parent drive object.
        :param dict[str, str | int | dict] data: JSON response for an Item resource.
        """
        self.drive = drive
        self._data = data
        if 'fileSystemInfo' in data:
            self._fs_info = facets.FileSystemInfoFacet(data['fileSystemInfo'])
        else:
            self._fs_info = None

    @property
    def id(self):
        """
        :rtype: str
        """
        return self._data['id']

    @property
    def is_folder(self):
        """
        :return True | False: True if the item is a folder; False if the item is a file (image, audio, ..., inclusive).
        """
        return OneDriveItemTypes.FOLDER in self._data

    @property
    def type(self):
        """
        :rtype: str
        """
        for x in OneDriveItemTypes.ALL:
            if x in self._data:
                return x

    @property
    def name(self):
        """
        :rtype: str
        """
        return self._data['name']

    @property
    def description(self):
        """
        :rtype: str
        """
        return self._data['description']

    @property
    def e_tag(self):
        """
        :rtype: str
        """
        return self._data['eTag']

    @property
    def c_tag(self):
        """
        :rtype: str
        """
        return self._data['cTag']

    @property
    def created_by(self):
        """
        :rtype: resources.IdentitySet
        """
        return resources.IdentitySet(self._data['createdBy'])

    @property
    def last_modified_by(self):
        """
        :rtype: resources.IdentitySet
        """
        return resources.IdentitySet(self._data['lastModifiedBy'])

    @property
    def size(self):
        """
        :rtype: int
        """
        return self._data['size']

    @property
    def parent_reference(self):
        """
        :rtype: onedrive_d.api.resources.ItemReference
        """
        if not hasattr(self, '_parent_reference'):
            self._parent_reference = resources.ItemReference(self._data['parentReference'])
        return self._parent_reference

    @property
    def web_url(self):
        """
        :rtype: str
        """
        return self._data['webUrl']

    @property
    def folder_props(self):
        """
        :rtype: onedrive_d.api.facets.FolderFacet
        """
        if not hasattr(self, '_folder_props'):
            self._folder_props = facets.FolderFacet(self._data['folder'])
        return self._folder_props

    @property
    def children(self):
        if not hasattr(self, '_children'):
            self._children = {d['id']: OneDriveItem(self.drive, d) for d in self._data['children']}
        return self._children

    @property
    def file_props(self):
        """
        :rtype: onedrive_d.api.facets.FileFacet
        """
        if not hasattr(self, '_file_props'):
            self._file_props = facets.FileFacet(self._data['file'])
        return self._file_props

    @property
    def image_props(self):
        """
        :rtype: onedrive_d.api.facets.ImageFacet
        """
        if not hasattr(self, '_image_props'):
            self._image_props = facets.ImageFacet(self._data['image'])
        return self._image_props

    @property
    def photo_props(self):
        """
        :rtype: onedrive_d.api.facets.PhotoFacet
        """
        if not hasattr(self, '_photo_props'):
            self._photo_props = facets.PhotoFacet(self._data['photo'])
        return self._photo_props

    @property
    def audio_props(self):
        """
        :rtype: onedrive_d.api.facets.AudioFacet
        """
        # TODO: finish AudioFacet
        raise NotImplementedError("Not implemented yet.")

    @property
    def video_props(self):
        """
        :rtype: onedrive_d.api.facets.VideoFacet
        """
        # TODO: finish VideoFacet
        raise NotImplementedError("Not implemented yet.")

    @property
    def location_props(self):
        """
        :rtype: onedrive_d.api.facets.LocationFacet
        """
        if not hasattr(self, '_location_props'):
            self._location_pros = facets.LocationFacet(self._data['location'])
        return self._location_pros

    @property
    def deletion_props(self):
        """
        :rtype: onedrive_d.api.facets.DeletedFacet
        """
        # TODO: finish DeletedFacet
        raise NotImplementedError("Not implemented yet.")

    @property
    def fs_info(self):
        """
        :return facets.FileSystemInfoFacet:
        """
        return self._fs_info

    @property
    def created_time(self):
        """
        :rtype: int
        """
        if self._fs_info is not None:
            return self._fs_info.created_time
        return parse_datetime(self._data['createdDateTime'])

    @property
    def modified_time(self):
        """
        :rtype: int
        """
        if self._fs_info is not None:
            return self._fs_info.modified_time
        return parse_datetime(self._data['lastModifiedDateTime'])
