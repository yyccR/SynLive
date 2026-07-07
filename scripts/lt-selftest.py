"""LiveTalking 本地自测：在容器内当"假浏览器"连 localhost:8028/offer，验证数字人是否真出画面。

用法（在 GPU 机上）：
  docker cp scripts/lt-selftest.py livetalking:/root/metahuman-stream/lt-selftest.py
  docker exec -it livetalking bash -c 'source /root/miniconda3/etc/profile.d/conda.sh; conda activate base; cd /root/metahuman-stream && python lt-selftest.py'

输出 RESULT：
  LIVEOK  -> LiveTalking 渲染正常，浏览器黑屏是浏览器↔GPU 的 UDP/网络问题
  NOFRAMES-> LiveTalking 没出画面，查 musetalk/avatar/日志
"""
import asyncio
import aiohttp
from aiortc import RTCPeerConnection

LT_OFFER = "http://localhost:8028/offer"
WAIT_SEC = 20


async def main():
    pc = RTCPeerConnection()
    pc.addTransceiver("video", direction="recvonly")
    pc.addTransceiver("audio", direction="recvonly")

    state = {"video": 0, "audio": 0, "connected": False}

    @pc.on("track")
    def on_track(track):
        print(f"[track] {track.kind} 收到")

        async def consume():
            while True:
                try:
                    await track.recv()
                    state[track.kind] += 1
                    if track.kind == "video" and state["video"] in (1, 5, 10):
                        print(f"  video 已收 {state['video']} 帧")
                except Exception as e:
                    print(f"  [consume] {track.kind} 结束: {e}")
                    return

        asyncio.ensure_future(consume())

    @pc.on("connectionstatechange")
    def on_state():
        print(f"[pc] connectionState = {pc.connectionState}")
        if pc.connectionState == "connected":
            state["connected"] = True

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    print(f"POST {LT_OFFER} ...")
    async with aiohttp.ClientSession() as s:
        async with s.post(
            LT_OFFER,
            json={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            print(f"  /offer -> HTTP {r.status}")
            if r.status != 200:
                text = await r.text()
                print(f"  body: {text[:300]}")
                print("RESULT: OFFER_FAIL")
                await pc.close()
                return
            ans = await r.json()

    await pc.setRemoteDescription(ans)
    print("answer 已设置，等待画面帧...")

    for _ in range(WAIT_SEC):
        await asyncio.sleep(1)
        if state["video"] >= 5:
            break

    print(f"\n===== 结果：video {state['video']} 帧, audio {state['audio']} 帧, connected={state['connected']} =====")
    if state["video"] > 0:
        print("RESULT: LIVEOK  -> LiveTalking 渲染正常；浏览器黑屏 = 浏览器↔GPU 的 UDP/网络不通")
    else:
        print("RESULT: NOFRAMES -> LiveTalking 没出画面；查 docker logs livetalking（musetalk/avatar）")
    await pc.close()


if __name__ == "__main__":
    asyncio.run(main())
