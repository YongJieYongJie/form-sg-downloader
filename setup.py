import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='formsgdownloader',
    version='1.0.0',
    author='Khoo Yong Jie',
    author_email='khooyongjie@gmx.com',
    description='A simple GUI for downloading data from FormSG forms created '
                'using the "storage" mode',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/YongJieYongJie/form-sg-downloader',
    packages=setuptools.find_packages(),
    package_data={
        '': ['favicon.ico'],
    },
    install_requires=[
        'selenium',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)
