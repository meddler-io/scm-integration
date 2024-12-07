
import json
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



# Make env differntiator
NATS_SUBJECT = ("" if IS_PROD else "dev:" ) + NATS_SUBJECT


print("NATS", NATS_CONNECTION_STRING, NATS_SUBJECT)

if None in [NATS_CONNECTION_STRING, NATS_SUBJECT]:
    raise Exception("NATS message queue credentials missing")


async def handleMsg(msg):


    msg = json_util.loads(msg )
    
    print("msg", msg)
    source = msg["source"]
    access_token = msg["access_token"]
    
    host = None
    if "host" in msg:
        host = msg["host"]
    

    
    webhook_completed , webhook_failed, webhook_processing  = None , None , None
    
    webhooks = msg["webhooks"]
    
    
    try:
        webhook_processing = webhooks["processing"]
        await lib.put_data( webhook_processing )
    except:
        traceback.print_exc()
        raise Exception("No processing webhook")
    
        
    async def update_callback(data):
        return await  lib.put_data( webhook_processing , data=data )
        
        
        
    try:
        print("gettijg data")
        data = await lib.get_scm_data( source , access_token , update_callback , host  )

    except:
        traceback.print_exc()
        
        raise Exception("Failed to push data while processing")

        
    try:
        
        if data:
            try:
                webhook_completed = webhooks["completed"]
                # Completed
                await lib.put_data( webhook_completed , data={} )
                
            except:
                traceback.print_exc()
                pass
        else:
            raise Exception("failed")
    except Exception as err:
        traceback.print_exc()
        
        try:
            webhook_failed = webhooks["failed"]
            await lib.put_data( webhook_failed , data=str(err))
            
        except:
            traceback.print_exc()
            pass





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
                    await handleMsg(msg.data.decode() )
                  
                except:
                    pass
        except Exception as er:
            print("Handled gracefully", er, NATS_SUBJECT)

    # Create deliver group that will be have load balanced messages.


def test():
    sample_msg = {
        "source": "bitbucket",
        "access_token": "",
        "callback_url": "",
    }
      
    # asyncio.run(main())
    loop = asyncio.get_event_loop()
    
    sample_msg = json.dumps(sample_msg)
    loop.run_until_complete(handleMsg( sample_msg ))

# Test Functio
def init():
    # asyncio.run(main())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

if __name__ == '__main__':
    test()