from setuptools import setup, find_packages

setup(
    name='mfdirsync',
    version='0.6.0',
    author='Your Name', # Replace with your actual name
    author_email='your.email@example.com', # Replace with your actual email
    description='A command-line tool to synchronize files between directories.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/mfdirsync', # Replace with your GitHub repository URL
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: Utilities',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'mfdirsync=mfdirsync.__main__:main',
        ],
    },
)
