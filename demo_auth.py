"""Start the server in-process and compare what an HR token and a staff token can do."""

import asyncio
import threading

import uvicorn
from fastmcp import Client
from fastmcp.exceptions import ToolError

import server

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/mcp"


def start_server() -> uvicorn.Server:
    config = uvicorn.Config(server.mcp.http_app(), port=PORT, log_level="error")
    http_server = uvicorn.Server(config)
    threading.Thread(target=http_server.run, daemon=True).start()
    return http_server


async def main() -> None:
    tokens = {
        "hr": server.create_dev_token([server.HR_COMP_SCOPE]),
        "staff": server.create_dev_token([]),
    }
    http_server = start_server()
    async with asyncio.timeout(10):
        while not http_server.started:
            await asyncio.sleep(0.05)

    for label, token in tokens.items():
        async with Client(URL, auth=token) as client:
            tools = [tool.name for tool in await client.list_tools()]
            print(f"{label:<6} tools: {tools}")
            try:
                result = await client.call_tool("payroll_salary_report", {"department": "Roastery"})
                print(f"{label:<6} salary report: {result.data}")
            except ToolError as error:
                print(f"{label:<6} salary report denied: {error}")

    try:
        async with Client(URL) as client:
            await client.list_tools()
    except Exception as error:  # any failure here means the request was rejected
        print(f"no token rejected: {type(error).__name__}")

    http_server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
