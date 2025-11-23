from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lmstudio-bridge-enhanced",
    version="3.1.1",
    author="Ahmed Maged",
    author_email="ahmedibrahim085@users.noreply.github.com",
    description="Enhanced MCP server bridging Claude with local LLMs via LM Studio - featuring autonomous agents, multi-model orchestration, and type coercion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ahmedibrahim085/lmstudio-bridge-enhanced",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests",
        "mcp[cli]",
        "openai>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "lmstudio-mcp=main:main",
        ],
    },
)