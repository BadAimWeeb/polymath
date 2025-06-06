import logging
import re

from aiohttp import web
from datetime import datetime
from colorama import Fore,init
init()

def setup(app, config, packs_manager):
    routes = Routes(config, packs_manager)
    app.add_routes(
        [
            web.post("/upload", routes.upload),
            web.get("/pack.zip", routes.download),
            web.get("/debug", routes.debug),
        ]
    )


class Routes:
    def __init__(self, config, packs_manager):
        self.config = config
        self.packs = packs_manager

    def start(self):
        web.run_app(self.app)

    def timestamp(self):
        # "%m/%d/%Y, %H:%M:%S"
        # 06/12/2018, 09:55:22
        now = datetime.now()
        return "["+now.strftime("%m/%d/%Y")+"]["+now.strftime("%H:%M:%S")+"]"
    
    async def upload(self, request):
        # set the IP depending on the enviroment.        
        Real_IP = request.headers[ self.config['nginx']['ip_header'] ] if self.config["nginx"]["enabled"] else request.remote
        logging.info("Received Upload request from: "+Real_IP)
        
        User_Agent = request.headers['User-Agent'] 
        print(User_Agent)
        if not any( [re.compile(x,flags=re.IGNORECASE).fullmatch(User_Agent) for x in self.config['security']['known_agents']['upload']] ):
            if self.config['security']['block_unknown_agents'] and self.config['security']['reject_upload']:
                logging.error("Rejecting Upload: "+User_Agent+" from "+Real_IP)
                return web.json_response({"error": "Unknown Application"}) 
            else:
                logging.warn("Unknown Application access: "+User_Agent+" from "+Real_IP)
        
        """
        Allow to upload a resourcepack with a spigot id

           Test: curl -F "pack=@./file.zip" -F "id=EXAMPLE" -X POST http://localhost:8080/upload

           Parameters:
               self (Routes): An instance of Routes
               request (aiohttp.web_request.Request): The web request

           Returns:
               pack (web.json_response): Pack url and its SHA1 hash
        """
        data = await request.post()
        key_id = data["id"]

        key_filter_config = self.config['security']['key_filter']
        key_filter_whitelist = key_filter_config['mode'] == 'whitelist'
        key_filter = key_filter_config['keys']

        if key_filter_whitelist:
            if key_id not in key_filter:
                logging.error("Rejecting Upload: "+key_id+" from "+Real_IP)
                return web.json_response({"error": "This license is not valid."})
        else:
            if key_id in key_filter:
                logging.error("Rejecting Upload: "+key_id+" from "+Real_IP)
                return web.json_response({"error": "This license is not valid."})

        pack = data["pack"].file.read()
        id_hash = self.packs.register(pack, key_id, Real_IP) # use the above header if behind e.x.: nginx

        return web.json_response(
            {
                "url": self.config["server"]["url"] + "/pack.zip?id=" + id_hash,
                "sha1": id_hash,
            }
        )

    # To download a resourcepack from its id
    async def download(self, request):
        logging.debug("Received User Download request.")
        
        Real_IP = request.headers[ self.config['nginx']['ip_header'] ] if self.config["nginx"]["enabled"] else request.remote
        User_Agent = request.headers['User-Agent'] 
        if not any( [re.compile(x,flags=re.IGNORECASE).fullmatch(User_Agent) for x in self.config['security']['known_agents']['download']] ):
            if self.config['security']['block_unknown_agents'] and self.config['security']['reject_download']:
                logging.error("Rejecting Upload: "+User_Agent+" from "+Real_IP)
                return web.json_response({"error": "Unknown Application"}) 
            else:
                logging.warn("Unknown Application access: "+User_Agent+" from "+Real_IP)
                
        """
        Allow to download a resourcepack with a spigot id

            Test: curl http://localhost:8080/download?id=EXAMPLE

            Parameters:
                self (Routes): An instance of Routes
                request (aiohttp.web_request.Request): The web request

            Returns:
                pack (web.FileResponse): the resource pack
        """
        params = request.rel_url.query
        try:
            pack = self.packs.fetch(params["id"])
            if not pack:
                return web.Response(body=b"Pack not found")
            else:
                return web.FileResponse(pack, headers={"content-type": "application/zip"})
        except TimeoutError:
            logging.warn("Download Request timed out!")
            
    async def debug(self, request):
        logging.warning(str(type(request)))
        """
        Allow to test the connection

            Test: curl http://localhost:8080/debug
        
            Parameters:
                self (Routes): An instance of Routes
                request (aiohttp.web_request.Request): The web request
        """
        return web.Response(body="It seems to be working...")
