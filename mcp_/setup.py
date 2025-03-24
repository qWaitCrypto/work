from setuptools import setup, find_packages

setup(
    name="mcp_server",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "mcp_server = server:main"
        ]
    }
)
