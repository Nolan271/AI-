"""文档解析模块：支持 Word (.docx)、PDF、TXT 格式的文本提取"""

from pathlib import Path
from typing import Optional


def extract_text_from_docx(path: Path) -> str:
    """提取 .docx 文件中的文本"""
    try:
        from docx import Document

        doc = Document(str(path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        raise ImportError("python-docx is required for .docx parsing")
    except Exception as e:
        raise RuntimeError(f"Failed to parse docx: {e}")


def extract_text_from_pdf(path: Path) -> str:
    """提取 PDF 文件中的文本"""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(path))
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            if text:
                pages.append(text)
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required for .pdf parsing")
    except Exception as e:
        raise RuntimeError(f"Failed to parse pdf: {e}")


def extract_text_from_txt(path: Path) -> str:
    """提取 .txt 文件中的文本，自动检测编码"""
    encodings = ["utf-8", "gbk", "gb2312", "gb18030", "big5", "latin-1"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # fallback
    return path.read_text(encoding="latin-1")


SUPPORTED_EXTENSIONS = {
    ".docx": extract_text_from_docx,
    ".pdf": extract_text_from_pdf,
    ".txt": extract_text_from_txt,
}


def extract_text(path: Path) -> str:
    """自动识别文件类型并提取文本"""
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {list(SUPPORTED_EXTENSIONS.keys())}"
        )
    return SUPPORTED_EXTENSIONS[ext](path)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """将长文本切分为块，用于 RAG 检索"""
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        if end >= text_len:
            chunks.append(text[start:].strip())
            break

        # 寻找段落边界（\n\n）或句子边界（。！？）
        boundary = -1
        for sep in ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? "]:
            pos = text.rfind(sep, start, end)
            if pos > boundary:
                boundary = pos + len(sep)

        if boundary > start:
            chunks.append(text[start:boundary].strip())
            start = boundary
        else:
            chunks.append(text[start:end].strip())
            start = end

        # overlap
        start = max(start - overlap, start)

    return [c for c in chunks if c]
