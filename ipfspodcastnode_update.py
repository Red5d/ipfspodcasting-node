import os, sys, logging, time, random, json, argparse
import requests

class IPFSNode:
    def __init__(self, rpc_url):
        self.rpc_url = rpc_url

    def _request(self, endpoint, files=None):
        if files:
            res = requests.post(self.rpc_url + '/api/v0/' + endpoint, files=files)
        else:
            res = requests.post(self.rpc_url + '/api/v0/' + endpoint)
            
        return res

    def add(self, name, file):
        # Add file to IPFS (wrapped in a directory) and return hash value(s)
        res = self._request('add?pin=true&wrap-with-directory=true', files={name: file})
        return [json.loads(x) for x in res.text.split('\n') if x != '']
    
    def size(self, hash):
        # Get size of content item in IPFS
        res = self._request('ls?arg='+hash)
        return sum([x['Size'] for x in res.json()['Objects'][0]['Links']])
    
    def ls(self, hash):
        # List hash data for a content item in IPFS
        return self._request('ls?arg='+hash).json()

    def cat(self, path):
        # Get content of file in IPFS
        try:
            res = self._request('cat?arg='+path)
            return res.content
        except:
            return None
    
    def pin_add(self, hash):
        # Pin hash to IPFS node
        res = self._request('pin/add?arg=' + hash)
        return res.json()['Pins'][0]
    
    def pin_rm(self, hash):
        # Unpin hash from IPFS node
        res = self._request('pin/rm?arg=' + hash)
        try:
            return res.json()['Pins'][0]
        except:
            return hash
    
    def pin_ls(self):
        # List pinned hashes on IPFS node
        res = self._request('pin/ls')
        return res.json()
    
    def id(self):
        # Get ID of IPFS node
        return self._request('id').json()['ID']
    
    def version(self):
        # Get version of IPFS node
        return self._request('version').json()['Version']
    
    def peers(self):
        # Get list of peers connected to IPFS node
        return self._request('swarm/peers').json()
    
    def repo_stat(self):
        # Get repo stats for IPFS node
        return self._request('repo/stat').json()
    
class IPFSPodcasting:
    def __init__(self, email, node):
        self.email = email
        self.node = node

    def getPayload(self):
        # Build and return the base payload data for the IPFSPodcasting.net API
        return {
            'email': self.email,
            'version': '0.6p',
            'ipfs_id': self.node.id(),
            'ipfs_ver': self.node.version(),
            'online': True if len(self.node.peers()['Peers']) > 0 else False,
            'peers': str(len(self.node.peers()['Peers']))
        }

    def getWork(self):
        # Get work from IPFSPodcasting.net
        res = requests.post("https://IPFSPodcasting.net/Request", timeout=120, data=self.getPayload())
        return res.json()
    
    def sendResponse(self, payload):
        # Send report of actions taken back to IPFSPodcasting.net
        res = requests.post("https://IPFSPodcasting.net/Response", timeout=120, data=payload)
        return res.text


def download_url(url):
    # Download file from url, retrying once if necessary
    try:
        file = requests.get(url, timeout=120)
        if len(file.content) != int(file.headers['Content-Length']):
            logging.error(f"File size mismatch (DL: {len(file.content)} vs Expected: {file.headers['Content-Length']}) for {url}")
            raise ValueError('File size mismatch')
    except:
        try:
            # Retry
            file = requests.get(url, timeout=120)
            if len(file.content) != int(file.headers['Content-Length']):
                logging.error(f"File size mismatch (DL: {len(file.content)} vs Expected: {file.headers['Content-Length']}) for {url}")
                return None
        except:
            logging.error('Error downloading ' + url)
            return None
        
    return file.content


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rpc_url', type=str, required=True, help='Url for RPC API for your IPFS node. Example: http://localhost:5001')
    parser.add_argument('--email', type=str, required=True, help='Your email address')
    parser.add_argument('--log_file', type=str, default='ipfspodcastnode.log', help='Log file to write to. Default: ipfspodcastnode.log')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging and disable random starting delay')

    args = parser.parse_args()

    #Basic logging to file
    logging.basicConfig(format="%(asctime)s : %(message)s", datefmt="%Y-%m-%d %H:%M:%S", filename=args.log_file, level=logging.INFO)

    # Randomize exact starting time
    # (Used by original IPFSPodcasting.net script to help with spreading out API requests from clients, so I'm considering it a recommendation/request for how to use their API)
    if not args.debug:
        wait=random.randint(1,150)
        logging.info('Sleeping ' + str(wait) + ' seconds...')
        time.sleep(wait)

    # Create IPFS node and IPFSPodcasting server objects
    node = IPFSNode(args.rpc_url)
    server = IPFSPodcasting(args.email, node)

    # Get work from IPFSPodcasting.net
    work = server.getWork()

    if args.debug:
            logging.info(f"work: {work}")

    if work['message'] == 'Request Error':
        logging.info('Error requesting work from IPFSPodcasting.net')

    elif work['message'][0:7] != 'No Work':
        payload = server.getPayload()
        # If work available, and we have a download url and filename, download the file and add/pin to IPFS
        if work['download'] != '' and work['filename'] != '':
            logging.info(f"Adding {work['show']} - {work['episode']}: {work['download']}")

            # Download file
            if 'ipfs.io/ipfs' in work['download']:
                # If download url is an IPFS gateway url, use IPFS to download the file
                ipfs_path = '/'.join(work['download'].split('/')[4:])
                file = node.cat(ipfs_path)
            else:
                file = download_url(work['download'])

            if file:
                # Add file to IPFS
                hashes = node.add(work['filename'], file)
                if len(hashes) > 0:
                    logging.info('Added to IPFS: ' + hashes[0]['Hash'])
                    # Get hash values and size of file for reporting back to IPFSPodcasting.net API
                    payload['downloaded'] = hashes[0]['Hash'] + '/' + hashes[1]['Hash']
                    payload['length'] = node.size(hashes[1]['Hash'])
                else:
                    # If no hash values returned, report error
                    payload['error'] = 99
            else:
                logging.info('Error downloading ' + work['download'])

        if work['pin'] != '':
            if work['delete'] != work['pin']:   
                logging.info('Pinning hash (' + str(work['pin']) + ')')
                # Pin hash to IPFS
                pinned = node.pin_add(work['pin'])

                # Get hash values and size of file for reporting back to IPFSPodcasting.net API
                logging.info('Checking linked hashes for ' + str(work['pin']))
                hashes = node.ls(work['pin'])
                payload['length'] = node.size(pinned)
                payload['pinned'] = hashes['Objects'][0]['Links'][0]['Hash'] + '/' + work['pin']

        if work['delete'] != '':
            logging.info('Deleting hash ' + str(work['delete']))
            # Unpin hash from IPFS
            deleted = node.pin_rm(work['delete'])
            payload['deleted'] = work['delete']

        # Collect disk space stats for reporting back to IPFSPodcasting.net API
        payload['used'] = node.repo_stat()['RepoSize']
        df = os.statvfs('/')
        payload['avail'] = df.f_bavail * df.f_frsize

        # Respond back with actions taken
        if args.debug:
            logging.info('Sending Results:' + str(payload))

        # Send report of actions taken back to IPFSPodcasting.net
        res = server.sendResponse(payload)

        if args.debug:
            logging.info('Response:' + res)

    else:
        logging.info('No work to do.')
