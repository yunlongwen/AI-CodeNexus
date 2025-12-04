import hashlib
import os

from fastapi import APIRouter, Query

WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "your_token")

router = APIRouter()


@router.get("/callback")
async def wechat_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
) -> str:
    """
    Minimal WeChat MP access verification endpoint.

    WeChat will send: signature, timestamp, nonce, echostr.
    You must:
    1. Take your TOKEN (pre-shared with WeChat), timestamp, nonce.
    2. Sort them lexicographically and join.
    3. SHA1 hash the result.
    4. If equals signature, return echostr.
    """
    data = "".join(sorted([WECHAT_TOKEN, timestamp, nonce]))
    hashcode = hashlib.sha1(data.encode("utf-8")).hexdigest()
    if hashcode == signature:
        return echostr
    return ""


