import aiohttp
import asyncio
from random import randint, seed
import socket
from urllib.parse import urlencode

from torrent import Torrent


class Tracker:
    """
    A tracker keeps track of available peers for a given torrent.
    """

    def __init__(self, torrent: Torrent):
        # Initialize the pseudorandom number generator
        seed()

        self._torrent = torrent
        self._peer_id = self._generate_peer_id()
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
        print(url)
        # TODO: ClientSession.get() takes params as an argument. Error with parsing it though?
        # async with self._http_client.get(self._torrent.get_announce(), params=params) as resp:
        async with self._http_client.get(url) as resp:
            if not resp.status == 200:
                raise ConnectionError('Unable to connect to tracker: status code {}'.format(resp.status))
            print(resp)

    async def close(self):
        await self._http_client.close()

    @staticmethod
    def _generate_peer_id():
        """
        Generate a unique, 20 bytes long, ID for the client.
        This implementation follows the Azureus-style convention.
        """
        return '-DT0001-' + ''.join([str(randint(0,9)) for i in range(12)])
