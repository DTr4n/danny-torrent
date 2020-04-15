import bencode
from hashlib import sha1
from typing import NamedTuple

class TorrentFile(NamedTuple):
    """
    Represents the files within the torrent (i.e. the files to write to disk)
    """
    length: int
    path_segments: list


class Torrent:
    """
    A torrent to be downloaded/uploaded.
    """

    def __init__(self, torrent_file):
        with open(torrent_file, 'rb') as f:
            bencode_content = f.read()
            # TODO: Throw error if file can't be decoded?
            self._content = bencode.decode(bencode_content)
            self._info_hash = sha1(bencode.encode(self._content['info'])).digest()
            self._files = list()  # List of TorrentFile
            self._length = 0
            self._parse_files_and_get_length()

    def _parse_files_and_get_length(self):
        """
        Helper function for identifying the files in the torrent
        (if there are multiple files) and the total length
        """
        # TODO: get md5sum? It is an optional field

        info_dict = self._content['info']

        if self.is_multi_file():
            print('multi_file')
            for file in info_dict['files']:
                self._files.append(TorrentFile(file['length'], file['path']))
                self._length += file['length']
        else:
            print('single_file')
            self._length = info_dict['length']

    # TODO: Look into using @property for getter/setter functions
    def is_multi_file(self) -> bool:
        """
        Determine if the torrent contains multiple files
        """
        return self._content['info'].get('files') is not None

    # TODO: Should an index be a parameter? Because last piece will have a diff length
    def get_piece_length(self) -> int:
        """
        The length (bytes) for each piece
        """
        return self._content['info']['piece length']

    def get_pieces(self) -> list:
        """
        The info pieces. List of 20-byte SHA1 hash values
        """
        pieces = self._content['info']['pieces']
        return [pieces[i:i+20] for i in range(0, len(pieces), 20)]

    def get_name(self) -> str:
        """
        In single file mode - the filename
        In multiple file mode - the name of the directory to store all the files
        """
        return self._content['info']['name']

    def get_length(self) -> int:
        """
        The total size (bytes) for all the files in the torrent.
        """
        return self._length

    def get_info_hash(self) -> bytes:
        """
        Hash of the bencoded info dictionary from the .torrent file using SHA1 hash algorithm
        """
        return self._info_hash

    def get_announce(self) -> str:
        """
        The announce URL of the tracker
        """
        return self._content['announce']
