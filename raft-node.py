import aiohttp
import asyncio
import logging
import os
import random
import sys

from aiohttp import web

FOLLOWER = "follower"
CANDIDATE = "candidate"
LEADER = "leader"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RaftNode:
    def __init__(self, node_id, nodes):
        self.node_id = node_id
        self.nodes = nodes
        self.state = FOLLOWER
        self.current_term = 0
        self.voted_for_node = None
        self.leader_id = None
        self.election_timeout_task = None
        self.election_timeout_duration = random.uniform(5, 10)
        self.node_mapping = {i: node for i, node in enumerate(self.nodes)} 

    async def reset_election_timeout(self):
        if self.election_timeout_task:
            self.election_timeout_task.cancel()
        self.election_timeout_task = asyncio.create_task(self.election_timer())

    async def election_timer(self):
        await asyncio.sleep(self.election_timeout_duration)
        if self.state == FOLLOWER:
            await self.elect()

    async def elect(self):
        try:
            self.state = CANDIDATE
            self.current_term += 1
            self.voted_for_node = self.node_id
            votes = 1

            async def request_vote(node):
                logger.debug(f"Attempting to request vote from {node}")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(f'http://{node}/vote', json={
                            "term": self.current_term,
                            "candidate_id": self.node_id
                        }) as response:
                            logger.debug(f"Vote request to {node} responded with {response.status}")
                            if response.status == 200:
                                data = await response.json()
                                if data['candidate_id'] == self.node_id:
                                    logger.debug(f"Vote granted by {node}")
                                    nonlocal votes
                                    votes += 1
                except Exception as e:
                    logger.debug(f"Error reaching node {node}: {e}")

            requested_votes = [request_vote(node) for id, node in self.node_mapping.items() if id != self.node_id]
            await asyncio.gather(*requested_votes)

            if votes >= len(self.nodes) // 2:
                self.state = LEADER
                self.leader_id = self.node_id
                logger.debug(f"Node {self.node_mapping[self.node_id]}: Became leader for term {self.current_term}")

                await self.send_heartbeats()
            else:
                self.state = FOLLOWER
                logger.debug(f"{self.node_mapping[self.node_id]}: Election lost, reverting to follower")
        except Exception as e:
            logger.debug(f"Error during election: {e}")

    async def send_heartbeats(self):
        while self.state == LEADER:
            append_entries = [self.send_append_entries(node) for id, node in self.node_mapping.items() if id != self.node_id]
            await asyncio.gather(*append_entries)
            await asyncio.sleep(1)
    
    async def send_append_entries(self, node):
        logger.debug(f"Sending empty append entry to Node: {node}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'http://{node}/append_entries', json={
                    "term": self.current_term,
                    "leader_id": self.node_id,
                    "entries": []
                }) as response:
                    logger.debug(f"Send Append Entries request to {node} responded with {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        if data["term"] > self.current_term:
                            self.state = FOLLOWER
                            self.current_term = data["term"]
        except Exception as e:
            logger.debug(f"Error while sending empty append entries (heartbeats): {e}")


    async def handle_append_entries(self, request):
        data = await request.json()
        term = data['term']
        leader_id = data["leader_id"]

        logger.debug(f"In method handle_append_entries, data: {data}")
        
        if self.current_term > term:
            return web.json_response({"term": self.current_term, "success": False})

        self.current_term = term
        self.state = FOLLOWER
        self.leader_id = leader_id

        await self.reset_election_timeout()

        return web.json_response({"term": self.current_term, "success": True})

    async def handle_vote_request(self, request):
        data = await request.json()
        term = data['term']
        candidate_id = data['candidate_id']
        vote_granted = False

        if term > self.current_term:
            self.state = FOLLOWER
            self.voted_for_node = None
            self.current_term = term

        if (self.voted_for_node == None or self.voted_for_node == candidate_id) and term >= self.current_term:
            self.voted_for_node = candidate_id
            vote_granted = True

        return web.json_response({
            "term": self.current_term,
            "candidate_id": candidate_id,
            "vote_granted": vote_granted,
            "state": self.state
        })

    async def run(self):
        await self.reset_election_timeout()
        await self.run_server()
        await election_task

    async def run_server(self):
        try:
            app = web.Application()
            app.router.add_post('/vote', self.handle_vote_request)
            app.router.add_post('/append_entries', self.handle_append_entries)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', 8000 + self.node_id)
            await site.start()
            logger.debug(f"Node {self.node_id} running at http://0.0.0.0:{8000 + self.node_id}")
            await asyncio.Event().wait()             
        except Exception as e:
            logger.debug(f"Error creating server: {e}")

if __name__ == "__main__":
    node_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    nodes = os.environ.get('NODES').split(',')
    node = RaftNode(node_id, nodes)
    asyncio.run(node.run())
