from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect
import logging

from pydantic import BaseModel


log = logging.getLogger(__name__)

class PayloadTypeEnum(str, Enum):
    discon = "disconnect"
    con = "connect"
    msg = "message"

class DisconPayload(BaseModel):
    id: str

class ConPayload(BaseModel):
    id: str

class MsgPayload(BaseModel):
    msg: str
    sender_id: str

class Payload(BaseModel):
    type: PayloadTypeEnum
    data: str

class WebSockCon:
    is_doc: bool
    id: str
    con: WebSocket

    def __init__(self, id: str, con: WebSocket, is_doc: bool):
        self.id = id
        self.con = con
        self.is_doc = is_doc

    def filter_opp_of_me(self, w: "WebSockCon") -> bool:
        if w.is_doc and not self.is_doc:
            return True
        return False

    def filter_not_me(self, w: "WebSockCon") -> bool:
        if w.id == self.id:
            return False
        return True
            
        

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSockCon] = dict()

    @staticmethod
    def map_wcon_payload(w: WebSockCon) -> Payload | None:
        if w.con.client is None:
            return None
        data = ConPayload(id=w.id).model_dump_json()
        p = Payload(type=PayloadTypeEnum.con, data=data)
        return p

    async def connect(self, wsoc: WebSocket, id: str, is_doc):
            await wsoc.accept()
            con = WebSockCon(id=id, con=wsoc, is_doc=is_doc)
            self.active_connections[id] = con
            data = ConPayload(id=con.id).model_dump_json()
            payload = Payload(type=PayloadTypeEnum.con, data=data)
            log.info("New conenction. Broadcasting to interested parties")
            await self.broadcast(to_clients=con.is_doc, payload=payload)
            f = filter(con.filter_opp_of_me, list(self.active_connections.values()))
            f = filter(con.filter_not_me, list(self.active_connections.values()))
            f = map(self.map_wcon_payload, f)

            for e in f:
                if e is None:
                    continue
                await wsoc.send_text(e.model_dump_json())




    async def disconnect(self, id: str):
        con = self.active_connections.pop(id)
        data = DisconPayload(id=con.id).model_dump_json()
        payload = Payload(type=PayloadTypeEnum.discon, data=data)
        await self.broadcast(to_clients=con.is_doc, payload=payload)

    async def relay_message(self, message: str, senderid: str, recvid: str):
        r = self.active_connections.get(recvid)
        if r is None:
            log.warning(f"Connection not found, no relaying, recv: {recvid}")
            return
        try:
            sender = self.active_connections.get(senderid)
            if sender:
                data = MsgPayload(msg=message, sender_id=sender.id)
                payload = Payload(type=PayloadTypeEnum.msg, data=data.model_dump_json())
                await r.con.send_text(payload.model_dump_json())
                log.info(f"Sent message to {recvid}, {payload.model_dump_json()}")
        except WebSocketDisconnect as e:
            log.warn(f"Socket closed couldn't send message: {e}")
            pass
            

    async def broadcast(self, to_clients: bool, payload: Payload):
        connections = list(self.active_connections.values())
        log.info(f"Connections: {self.active_connections}")
        c = list(filter(lambda con: con.is_doc is not to_clients, connections))
        log.info(f"Making broadcast to {len(c)} clients, to_clients = {to_clients}")
        for cons in c:
            try:
                await cons.con.send_text(payload.model_dump_json())
            except WebSocketDisconnect as e:
                log.warn(f"Socket closed couldn't send message: {e}")
                pass
            
            

            
