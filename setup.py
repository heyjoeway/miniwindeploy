import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="miniwindeploy-heyjoeway",
    version="1.0.2",
    author="Joseph Judge",
    author_email="joe@jojudge.com",
    description="Stupid simple task runner, intended for deploying/debloating/customizing Windows ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/heyjoeway/miniwindeploy",
    project_urls={
        "Bug Tracker": "https://github.com/heyjoeway/miniwindeploy/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Windows",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    include_package_data= True,
    install_requires=[
        'pywin32'
    ]
)
