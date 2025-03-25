from setuptools import setup, find_packages

setup(
    name="mcp_server",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "httpx",
        "playwright",
        "openai",
        "beautifulsoup4",
        "chardet",
        "mcp",
    ],
    entry_points={
        "console_scripts": [
            "mcp_server = mcp_.Server:run_server_sync"
        ]
    }
)
