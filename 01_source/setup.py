from setuptools import setup, find_packages

setup(
    name="snaglist-pro",
    version="2.0.0",
    description="WhatsApp chat ZIP → formatted snaglist Excel with database persistence and batch processing",
    packages=find_packages(),
    install_requires=[
        "openpyxl>=3.1.0",
        "Pillow>=10.0.0",
        "imagehash>=4.3.0",
        "PyPDF2>=3.0.0",
        "ezdxf>=1.0.0",
        "pyyaml>=6.0",
        "sqlalchemy>=2.0.0",
        "python-dotenv>=1.0.0",
        "rapidfuzz>=3.0.0",
        "sentence-transformers>=3.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": ["pytest>=8.0.0", "pytest-cov>=5.0.0"],
    },
    python_requires=">=3.10",
)
