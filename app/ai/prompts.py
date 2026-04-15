from __future__ import annotations

SUMMARY_PROMPT_VERSION = "vi-summary-v1"
CLASSIFICATION_PROMPT_VERSION = "vi-classification-v1"
RAG_ANSWER_PROMPT_VERSION = "vi-rag-answer-v1"


SUMMARY_PROMPT_TEMPLATE = """Ban la tro ly tom tat tin tuc tieng Viet.

Yeu cau:
- Tom tat trong 2-4 cau.
- Giu lai thong tin chinh: su kien, doi tuong, so lieu, tac dong neu co.
- Van phong trung tinh, gon, ro.
- Khong bo sung thong tin khong co trong bai.

Tieu de: {title}
Tom tat goc: {summary}
Noi dung:
{content}
"""


CLASSIFICATION_PROMPT_TEMPLATE = """Ban la bo phan phan loai du lieu bao chi tieng Viet.

Hay tra ve JSON hop le voi cac truong:
- "primary_topic": chu de chinh ngan gon, thuc dung
- "tags": mang cac tag ngan gon, huu ich cho tim kiem/goi y
- "confidence": so thuc tu 0 den 1

Yeu cau:
- Uu tien nhom chu de tin tuc pho bien nhu: kinh-doanh, cong-nghe, tai-chinh, bat-dong-san, khoi-nghiep, chinh-sach, thi-truong, doanh-nghiep.
- Tag ngan, ro nghia, phu hop du lieu bao chi tieng Viet.
- Khong them giai thich ngoai JSON.

Tieu de: {title}
Tom tat: {summary}
Noi dung:
{content}
"""


RAG_ANSWER_PROMPT_TEMPLATE = """Ban la tro ly hoi dap su dung ngu canh truy xuat tu kho bai viet tin tuc.

Nguyen tac:
- Chi tra loi dua tren context duoc cung cap.
- Neu context khong du, phai noi ro khong du du lieu.
- Khong bịa, khong suy doan qua muc.
- Tra loi bang tieng Viet, ro rang, trung tinh.

Cau hoi: {query_text}

Context:
{context}
"""


def build_summary_prompt(*, title: str, summary: str | None, content: str) -> str:
    return SUMMARY_PROMPT_TEMPLATE.format(title=title, summary=summary or "", content=content)


def build_classification_prompt(*, title: str, summary: str | None, content: str) -> str:
    return CLASSIFICATION_PROMPT_TEMPLATE.format(title=title, summary=summary or "", content=content)


def build_rag_answer_prompt(*, query_text: str, context: str) -> str:
    return RAG_ANSWER_PROMPT_TEMPLATE.format(query_text=query_text, context=context)


RAG_ANSWER_PROMPT_TEMPLATE = """Ban la tro ly hoi dap su dung ngu canh truy xuat tu kho bai viet tin tuc.

Nguyen tac:
- Chi tra loi dua tren context duoc cung cap.
- Neu context khong du, phai noi ro khong du du lieu.
- Khong dua ra noi dung khong co trong context, khong suy doan qua muc.
- Tra loi bang tieng Viet, ro rang, trung tinh.

Cau hoi: {query_text}

Context:
{context}
"""
