
from scm import lib
import os
from time import sleep
import traceback
from bson import json_util
import asyncio
import nats
import os
from time import sleep

IS_PROD = os.getenv("PROD", False)

NATS_SUBJECT = os.getenv("NATS_SUBJECT", None)
NATS_CONNECTION_STRING = os.getenv("NATS_CONNECTION_STRING", None)


if None in [NATS_CONNECTION_STRING, NATS_SUBJECT]:
    raise Exception("NATS message queue credentials missing")


# Make env differntiator
NATS_SUBJECT = ("" if IS_PROD else "dev:" ) + NATS_SUBJECT

async def main():
    nc = await nats.connect(NATS_CONNECTION_STRING)

    # Create JetStream context.
    js = nc.jetstream()
    # await js.delete_stream(name=NATS_SUBJECT )
    
    await js.add_stream(name=NATS_SUBJECT, subjects=[NATS_SUBJECT],  )
    # Create single push based subscriber that is durable across restarts.
    sub = await js.pull_subscribe(NATS_SUBJECT, durable=NATS_SUBJECT)
    print(f"Waiting: {NATS_CONNECTION_STRING}  {NATS_SUBJECT}  "  )
    while True:
        try:
            msgs = await sub.fetch(1, timeout=10)

            for msg in msgs:
                try:
                    await msg.ack()
                    print(" msg", msg)
                    msg = json_util.loads(msg.data.decode())
                    
                    print("msg", msg)
                    source = msg["source"]
                    access_token = msg["access_token"]
                    
                    
                    
                    webhook_completed , webhook_failed, webhook_processing  = None , None , None
                    
                    webhooks = msg["webhooks"]
                    
                    
                    try:
                        webhook_processing = webhooks["processing"]
                        await lib.put_data( webhook_processing )
                    except:
                        pass
                    
                        
                    try:
                        data = await lib.get_scm_data( source , access_token  )
                        
                        if data:
                            try:
                                webhook_completed = webhooks["completed"]
                                await lib.put_data( webhook_completed , data=data )
                                
                            except:
                                pass
                        else:
                            raise Exception("failed")
                    except Exception as err:
                        try:
                            webhook_failed = webhooks["failed"]
                            await lib.put_data( webhook_failed , data=str(err))
                            
                        except:
                            pass
                    print("Done")
                    # sleep(5)
                except:
                    pass
        except Exception as er:
            print("Handled gracefully", er, NATS_SUBJECT)

    # Create deliver group that will be have load balanced messages.


sample_msg = {
    "source": "bitbucket",
    "access_token": "",
    "callback_url": "",
}

def init():
    # asyncio.run(main())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

if __name__ == '__main__':
    init()