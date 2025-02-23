from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os
import markdown
import re

app = FastAPI()

# Markdown 文件存储目录
MARKDOWN_DIR = "./markdown_files"

# 配置 Jinja2 模板
templates = Jinja2Templates(directory="templates")

def highlight_text(content, keywords):
    """ 在 HTML 里高亮搜索词（红色） """
    for word in keywords:
        content = re.sub(rf"({re.escape(word)})", r'<span style="color:red; font-weight:bold;">\1</span>', content, flags=re.IGNORECASE)
    return content

def get_search_snippet(content, keywords, snippet_length=100):
    """ 提取关键词周围的内容片段 """
    for word in keywords:
        match = re.search(rf"(.{{0,{snippet_length}}}{re.escape(word)}.{{0,{snippet_length}}})", content, re.IGNORECASE)
        if match:
            snippet = match.group(1)
            return highlight_text(snippet, keywords)  # 高亮关键词
    return "（无匹配内容）"

def read_markdown(file_name, keywords=None):
    """ 读取 Markdown 文件并转换为 HTML，支持高亮 """
    file_path = os.path.join(MARKDOWN_DIR, file_name)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    if keywords:
        content = highlight_text(content, keywords)
    return markdown.markdown(content)

def search_markdown_files(query):
    """ 模糊搜索 Markdown 文件 """
    keywords = query.lower().split()  # 拆分搜索词
    results = []

    for file_name in os.listdir(MARKDOWN_DIR):
        if file_name.endswith(".md"):
            file_path = os.path.join(MARKDOWN_DIR, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().lower()

                # 计算匹配得分（匹配关键词数量）
                match_count = sum(content.count(word) for word in keywords if word in content)
                
                # 只要匹配到其中一个关键词就算有效
                if match_count > 0:
                    snippet = get_search_snippet(content, keywords)
                    results.append((file_name, match_count, snippet))

    results.sort(key=lambda x: x[1], reverse=True)  # 按匹配得分排序
    return [{"file_name": file, "snippet": snippet} for file, _, snippet in results]

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """ 返回首页 """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search")
def search(q: str = Query(..., min_length=1)):
    """ 执行模糊搜索 """
    return search_markdown_files(q)

@app.get("/view/{file_name}", response_class=HTMLResponse)
def view_markdown(request: Request, file_name: str, query: str = None):
    """ 渲染 Markdown 文件，并高亮关键词 """
    keywords = query.lower().split() if query else []
    content = read_markdown(file_name, keywords)
    if content is None:
        return HTMLResponse("<h2>文件未找到</h2>", status_code=404)
    return templates.TemplateResponse("view.html", {"request": request, "file_name": file_name, "content": content})
