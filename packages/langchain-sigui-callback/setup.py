from setuptools import setup, find_packages

setup(
    name="langchain-sigui-callback",
    version="3.0.0",
    description="Sigui DePIN AI Security Oracle Callback Handler for LangChain & LangGraph agents",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Sigui Protocol",
    author_email="contact@sigui.xyz",
    url="https://github.com/ibonon/Sigui",
    packages=find_packages(),
    install_requires=[
        "langchain-core>=0.1.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
