import asyncio

from tracker import Tracker
from torrent import Torrent


async def main():
    torrent = Torrent('ubuntu-19.10-desktop-amd64.iso.torrent')
    tracker = Tracker(torrent)
    await tracker.send_announce_request(0, 0, 'started')
    await tracker.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
