import uuid
import hashlib
import logging
import httpx
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from urllib.parse import urlparse, unquote, parse_qs
import cache_settings as settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="tmp"), name="static")

# Initialize the cache based on settings
cache = settings.cache_type()
cache.init(**settings.kwargs)


@app.get("/")
def index():
    return PlainTextResponse("Util Server running")


@app.get("/md5/{text}")
@app.get("/md5")
def generate_md5(text: str | None, q: str | None = Query(None, alias="text")):
    if q and q != "":
        text = q
    md5_hash = hashlib.md5(text.encode()).hexdigest()
    return PlainTextResponse(str(md5_hash))



@app.get("/uuid")
def generate_uuid(request: Request,key: str | None = Query(None),ttl:  int | None = Query(settings.ttl)):
    res = str(uuid.uuid4())
    if key and key.strip()!='':
        url = f"http://localhost:8000/uuid?text={key}"
        cached_content = cache.get(key=url)
        if cached_content:
            res = cached_content
        else:
            content=str(uuid.uuid4())
            cache.set(key=url, value=res, ttl=ttl)
    return PlainTextResponse(res)


@app.get("/proxy")
def proxy(request: Request,
          url: str = Query(...),
          bearer: str | None = Query(None),
          accept: str | None = Query(None, alias="accept"),
          follow_redirects: bool = Query(True),
          ttl:  int | None = Query(settings.ttl)
          ):
    # full_requested_url = str(request.url)
    # full_requested_url_parsed = urlparse(full_requested_url)
    # query_params = parse_qs(full_requested_url_parsed.query)
    # logger.info(f"Query params: {query_params.get('accept', None)[0]}")



    decoded_url = unquote(url)
    parsed_url = urlparse(decoded_url)
    # accept_header = query_params.get('accept', None)[0]
    accept_header = unquote(accept) if accept else "*/*"

    if not parsed_url.scheme or not parsed_url.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL")

    cached_content = cache.get(key=decoded_url)
    if cached_content:
        logger.info(f"Cache hit for {decoded_url}")
        logger.info(f"Accept header: {accept_header}")
        logger.debug(f"Cache Content: {cached_content}")
        return Response(content=cached_content, media_type=accept_header)

    try:
        logger.info(f"Cache miss for {decoded_url}")
        logger.info(f"Accept header: {accept_header}")
        headers = {"Accept": accept_header} if accept_header else accept_header
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        logger.info(f"Request Headers: {headers}")
        response = httpx.get(decoded_url, headers=headers, follow_redirects=follow_redirects)
        if 199 < response.status_code < 300:
            content = response.content
            logger.debug(f"Origin Content: {content}")
            cache.set(key=decoded_url, value=content.decode('utf-8'), ttl=ttl)
        else:
            content = f"Error: Received status code {response.status_code} from {decoded_url}"
            logger.error(content)
        return Response(content=content, media_type=accept_header)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/all")
def show_all(content_type: str = "json"):
    cache_contents = cache.show_all(content_type)
    total_items = len(cache_contents)
    return JSONResponse(content={"total_items": total_items, "cache_contents": cache_contents})


@app.get("/clear")
def clear_cache():
    cache.clear()
    return {"message": "Cache cleared"}
