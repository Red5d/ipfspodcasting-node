# IPFSPodcasting Node
Update script and docker-compose to run a node for IPFSPodcasting.net

Adapted from https://github.com/Cameron-IPFSPodcasting/podcastnode-Python

Changes from original:
* Doesn't need to be run on the same host as the IPFS service as long as it can reach the RPC API.
* All communication is over the RPC API. No subprocess commands needed.
* Organized interactions with the IPFS node and the IPFSPodcasting.net site into class objects.
* Files are downloaded into memory and sent directly to the IPFS node for adding/pinning. 

Use the included docker-compose.yml to start up an IPFS node container.

Ensure that port 4001 on the container is accessible from the Internet, and that the admin RPC port 5001 is **_only accessible internally_**.

After running the script and/or setting a cron job, check the Manage page for your node at [https://ipfspodcasting.net/Manage](https://ipfspodcasting.net/Manage/Node)

Note: Occasionally, the "Current Status" on the node management page shows "Fail" instead of "Success". This appears to happen when a download fails and is usually resolved next time the script runs. Pretty sure this happens with the original/official script too, so just watch to be sure it goes back to "Success" eventually.

Usage: 

    python ipfspodcastnode_update.py [-h] --rpc_url RPC_URL --email EMAIL [--log_file LOG_FILE] [--debug]

    options:
      -h, --help           show this help message and exit
      --rpc_url RPC_URL    Url for RPC API for your IPFS node. Example: http://localhost:5001
      --email EMAIL        Your email address
      --log_file LOG FILE  Log file to write to. Default: ipfspodcastnode.log
      --debug              Enable debug logging and disable random starting delay


Example usage:

    python ipfspodcastnode_update.py --rpc_url 'http://192.168.1.100:5001' --email you@example.com

Set up a cron job to run this script automatically. The recommendation from IPFSPodcasting.net is a time period of every 10 minutes:

    */10 * * * * /usr/bin/flock -n /tmp/ipfspodcastnode.lockfile python ipfspodcastnode_update.py --rpc_url 'http://192.168.1.100:5001' --email you@example.com

