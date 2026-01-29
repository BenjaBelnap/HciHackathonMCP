# How to use

**For Mac (CPU-only):**
``` bash
docker compose --profile cpu up -d 
```

**For Windows/Linux with NVIDIA GPU:**
``` bash
docker compose --profile gpu up -d 
```

This will give you a front end hosted on port 3000. http://localhost:3000/

If you don't have a model available, the docker container that's supposed to pull it is probably still pulling it. Alternatively, you can pull down a model manually with this:

``` bash
docker exec -it ollama ollama pull granite4:350m
```