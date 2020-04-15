import aiohttp
import asyncio
import bencode
from random import randint, seed
import socket
import struct
from typing import NamedTuple, List
from urllib.parse import urlencode

from torrent import Torrent


class Peer(NamedTuple):
    """
    Represents a peer info
    """
    ip: str
    port: int
    peer_id: str


class TrackerResponse(NamedTuple):
    """
    Represents the response from the tracker
    """
    interval: int
    min_interval: int
    tracker_id: str
    complete: int
    incomplete: int
    peers: List[Peer]


class Tracker:
    """
    A tracker keeps track of available peers for a given torrent.
    """

    def __init__(self, torrent: Torrent):
        # Initialize the pseudorandom number generator
        seed()

        self._torrent = torrent
        self._peer_id = self._generate_peer_id()
        self._tracker_response = None
        # TODO: Documentation advise against creating a ClientSession outside of a coroutine
        # https://stackoverflow.com/questions/54242748/closing-aiohttp-clientsession-when-used-in-class
        # Manage the ClientSession in the main file instead?
        self._http_client = aiohttp.ClientSession()

    async def send_announce_request(self, uploaded, downloaded, event):
        """
        Send a GET request to the tracker to update with our info, and get back a list of available
        peers to connect to.

        :param uploaded: Total number of bytes uploaded
        :param downloaded: Total number of bytes downloaded
        :param event: Must be one of the following strings: started, stopped, completed
        """

        params = {
            'info_hash': self._torrent.get_info_hash(),
            'peer_id': self._peer_id,
            # TODO: Cycle through different ports if one cannot be established, BitTorrent uses 6881-6889
            'port': 6881,
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': self._torrent.get_length() - downloaded,
            'compact': 1,  # Client accepts compact response
            # TODO: Test that event is one of the following strings: started, stopped, completed
            'event': event
        }

        url = self._torrent.get_announce() + '?' + urlencode(params)

        async with self._http_client.get(url) as resp:
            if not resp.status == 200:
                raise ConnectionError('Unable to connect to tracker: status code {}'.format(resp.status))
            self._handle_response(await resp.read())

    async def close(self):
        await self._http_client.close()

    def _handle_response(self, response: bytes):
        response_dict = bencode.decode(response)

        if response_dict.get('failure reason'):
            raise AnnounceFailureError(response_dict['failure reason'])

        # Decompose peers from the tracker response
        raw_peers = response_dict['peers']
        if isinstance(raw_peers, list):
            peers = self._decode_peers_dict_model(raw_peers)
        else:
            peers = self._decode_peers_binary_model(raw_peers)

        # Debug print statements
        print(response_dict.get('interval'))
        print(response_dict.get('min interval'))
        print(response_dict.get('tracker id'))
        print(response_dict.get('complete'))
        print(response_dict.get('incomplete'))
        print(peers)

        self._tracker_response = TrackerResponse(response_dict.get('interval'),
                                                 response_dict.get('min interval'),
                                                 response_dict.get('tracker id'),
                                                 response_dict.get('complete'),
                                                 response_dict.get('incomplete'),
                                                 peers)

    @staticmethod
    def _decode_peers_dict_model(raw_peers: list):
        """
        In the dictionary model, the peers are in a list of dictionaries
        with the following keys: peer id, ip, port
        """
        # TODO: IP address can be IPv6 (hexed) or IPv4 (dotted quad) or DNS name (string)
        # Conversion on 'ip' needed?
        return [Peer(p['ip'], p['port'], p.get('peer id')) for p in raw_peers]


    @staticmethod
    def _decode_peers_binary_model(raw_peers: bytes):
        """
        In the binary model, the peers value is a string consisting of multiples of 6 bytes.
        First 4 bytes are the IP address and last 2 bytes are the port number.
        """
        peers = []
        for i in range(0, len(raw_peers), 6):
            p = struct.unpack_from('!BBBBH', raw_peers, offset=i)
            peers.append(Peer('%d.%d.%d.%d' % p[:4], int(p[4]), None))
        return peers

    @staticmethod
    def _generate_peer_id():
        """
        Generate a unique, 20 bytes long, ID for the client.
        This implementation follows the Azureus-style convention.
        """
        return '-DT0001-' + ''.join([str(randint(0,9)) for i in range(12)])


class AnnounceFailureError(Exception):
    """Raised when an error message is present in the tracker response"""
    pass
