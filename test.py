import os
import re
import json
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from openai import OpenAI


# -----------------------------
# 文本读取部分
# -----------------------------
def read_text_file(path: Path) -> str:
    """
    读取 txt/md 等纯文本文件
    - utf-8 优先，失败再用 gbk（Windows 常见）
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk", errors="ignore")




def read_pdf_file(path: Path) -> str:
    """
    读取 PDF（仅提取文字）
    注意：如果 PDF 是扫描件图片，提取会很少甚至为空，这是正常现象（需要 OCR 才行）
    """
    reader = PdfReader(str(path))
    texts = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        # 给每页加个分隔符，方便模型理解结构（可选）
        if page_text.strip():
            texts.append(f"\n\n[Page {i+1}]\n{page_text}")
    return "\n".join(texts)


def load_document(path: Path) -> str:
    """
    根据文件后缀加载内容
    """
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return read_text_file(path)
    if suffix == ".pdf":
        return read_pdf_file(path)
    raise ValueError(f"暂不支持的文件类型：{suffix}（仅支持 .txt/.md/.pdf）")


# -----------------------------
# 文本清洗 & 截断
# -----------------------------
def normalize_text(text: str) -> str:
    """
    轻量清洗：
    - 统一换行
    - 压缩过多空行
    - 去掉两端空白
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)  # 连续>=3个换行 -> 2个
    return text.strip()




def truncate_text(text: str, max_chars: int) -> str:
    """
    简单按字符截断，避免输入过长导致费用/延迟暴涨
    """
    if len(text) <= max_chars:
        return text
    # 末尾加提示，告诉模型这不是全文
    return text[:max_chars] + "\n\n[TRUNCATED: 内容过长，已截断，仅基于以上内容总结]"


# -----------------------------
# LLM 调用 & JSON 保障
# -----------------------------
def build_system_prompt() -> str:
    """
    强约束：只输出 JSON，不要 Markdown，不要解释。
    """
    return """
你是一个专业的文档分析助手。请根据用户提供的文档内容，返回严格的 JSON，不要输出任何多余文字。

必须输出以下 JSON 格式（字段必须齐全）：
{
  "doc_type": "文档类型（如：合同/论文/会议纪要/需求文档/说明书/其它）",
  "summary": "一句话总结（不超过40字）",
  "key_points": ["要点1", "要点2", "要点3"],
  "risks_or_questions": ["风险或疑问1", "风险或疑问2"],
  "todo_list": ["行动项1", "行动项2"]
}

规则：
- 只能输出 JSON（第一字符必须是 { ，最后一个字符必须是 }）
- 不要使用 Markdown，不要用代码块
- 列表字段至少给出 2 条（不足可写“无”但仍要保留数组结构）
""".strip()


def extract_json_object(s: str) -> str | None:
    """
    尝试从模型输出中“捞出”一个 JSON 对象：
    - 有些模型偶尔会多说一句话，这里用最外层 {...} 提取
    """
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        return s

    # 粗暴但实用：找第一个 { 到最后一个 }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start:end + 1].strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate
    return None


def call_llm_structured_summary(client: OpenAI, model: str, doc_text: str, retries: int = 1) -> dict:
    """
    调用模型并确保返回可解析 JSON
    - retries: JSON 解析失败时的重试次数（建议 1~2）
    """
    system_prompt = build_system_prompt()

    for attempt in range(retries + 1):
        temperature = 0.2 if attempt == 0 else 0.0  # 重试时更“死板”
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": doc_text}
            ],
            temperature=temperature
        )

        raw = resp.choices[0].message.content or ""
        raw = raw.strip()

        json_str = extract_json_object(raw)
        if not json_str:
            if attempt < retries:
                time.sleep(0.3)
                continue
            raise ValueError("模型输出未包含可识别的 JSON 对象。")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            if attempt < retries:
                time.sleep(0.3)
                continue
            raise

        # 基础校验：确保关键字段存在
        required_keys = {"doc_type", "summary", "key_points", "risks_or_questions", "todo_list"}
        missing = required_keys - set(data.keys())
        if missing:
            if attempt < retries:
                time.sleep(0.3)
                continue
            raise ValueError(f"JSON 缺少字段：{missing}")

        return data

    raise RuntimeError("不可达：重试循环结束仍未返回有效 JSON")


# -----------------------------
# 主流程
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="文档总结器（txt/pdf -> 结构化 JSON）")
    parser.add_argument("file", type=str, help="输入文件路径（支持 .txt/.md/.pdf）")
    parser.add_argument("--max_chars", type=int, default=12000, help="最多输入给模型的字符数，默认 12000")
    parser.add_argument("--out_dir", type=str, default="outputs", help="输出目录，默认 outputs")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="模型名，默认 deepseek-chat")
    parser.add_argument("--retries", type=int, default=1, help="JSON 解析失败时重试次数，默认 1")
    args = parser.parse_args()

    in_path = Path(args.file).expanduser().resolve()
    if not in_path.exists():
        raise FileNotFoundError(f"文件不存在：{in_path}")

    # 1) 读取 key & 创建客户端
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 2) 读取文档
    raw_text = load_document(in_path)
    raw_text = normalize_text(raw_text)

    if not raw_text.strip():
        raise ValueError("文档提取到的文本为空。若是扫描版 PDF，需要 OCR（后续可加）。")

    # 3) 截断
    doc_text = truncate_text(raw_text, args.max_chars)

    # 4) 调用模型获得结构化 JSON
    data = call_llm_structured_summary(
        client=client,
        model=args.model,
        doc_text=doc_text,
        retries=args.retries
    )

    # 5) 写输出
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{in_path.stem}.summary.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n✅ 总结完成")
    print("输入文件：", in_path)
    print("输出文件：", out_path)

    # 6) 控制台展示关键结果
    print("\n📌 summary:", data.get("summary"))
    print("🔑 key_points:")
    for i, p in enumerate(data.get("key_points", []), 1):
        print(f"  {i}. {p}")


if __name__ == "__main__":
    main()
 
