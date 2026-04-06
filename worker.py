import asyncio
import json
import redis.asyncio as redis

async def start_worker():
    client = redis.from_url("redis://localhost:6379")
    
    queues = ["queue:enterprise", "queue:pro", "queue:free"]
    
    print(f"Worker started. Listening on {queues}...")
    
    while True:
        result = await client.brpop(queues, timeout=0)
        
        if result:
            queue_name, data = result
            job = json.loads(data)
            
            print(f"[{queue_name.decode()}] Processing job for {job['tenant_id']}...")
            
            await asyncio.sleep(1) 
            
            print(f"Done processing.")

if __name__ == "__main__":
    asyncio.run(start_worker())