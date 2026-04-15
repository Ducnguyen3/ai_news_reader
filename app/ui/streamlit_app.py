from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.services import NewsUIService


st.set_page_config(page_title="AI News Reader", layout="wide")


def main() -> None:
    """Streamlit entrypoint for browsing enriched articles and RAG Q&A."""

    service = NewsUIService()

    st.title("AI News Reader")
    st.caption("Demo giao dien Streamlit cho crawler tin tuc va AI enrichment.")

    with st.sidebar:
        st.header("Bo loc")
        mode = st.radio("Che do", ["Danh sach bai viet", "Hoi dap RAG"])
        sources = service.list_sources()
        selected_source = st.selectbox("Nguon tin", options=["Tat ca", *sources], index=0)
        keyword = st.text_input("Tu khoa tieu de", placeholder="Vi du: AI, ngan hang, startup")
        limit = st.slider("So bai toi da", min_value=5, max_value=100, value=20, step=5)

    if mode == "Danh sach bai viet":
        render_article_list(
            service=service,
            source_name=None if selected_source == "Tat ca" else selected_source,
            keyword=keyword or None,
            limit=limit,
        )
        return

    render_rag_qa(service=service)


def render_article_list(service: NewsUIService, source_name: str | None, keyword: str | None, limit: int) -> None:
    articles = service.list_articles(source=source_name, keyword=keyword, limit=limit)
    if not articles:
        st.info("Khong tim thay bai viet phu hop bo loc hien tai.")
        return

    st.subheader("Danh sach bai viet")
    article_options = {
        f"{item.title} | {item.source_name} | {format_datetime(item.publish_time)}": item.article_id
        for item in articles
    }

    selected_label = st.selectbox("Chon bai viet", options=list(article_options.keys()))
    selected_article_id = article_options[selected_label]

    st.dataframe(
        [
            {
                "ID": item.article_id,
                "Title": item.title,
                "Source": item.source_name,
                "Publish Time": format_datetime(item.publish_time),
                "Category": item.primary_category or "",
            }
            for item in articles
        ],
        use_container_width=True,
        hide_index=True,
    )

    render_article_detail(service=service, article_id=selected_article_id)


def render_article_detail(service: NewsUIService, article_id: int) -> None:
    detail = service.get_article_detail(article_id)
    if detail is None:
        st.warning("Khong tim thay chi tiet bai viet.")
        return

    st.subheader("Chi tiet bai viet")
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"### {detail.title}")
        st.write(f"**Nguon:** {detail.source_name}")
        st.write(f"**Thoi gian:** {format_datetime(detail.publish_time)}")
        st.write(f"**URL:** {detail.article_url}")
    with col2:
        st.write(f"**Chu de chinh:** {detail.primary_topic or 'Chua enrich'}")
        st.write(f"**Categories:** {', '.join(detail.categories) if detail.categories else 'N/A'}")
        st.write(f"**Tags:** {', '.join(detail.tags) if detail.tags else 'Chua enrich'}")

    with st.expander("Noi dung goc", expanded=True):
        st.text_area("Content", value=detail.content_text[:5000], height=300, disabled=True, label_visibility="collapsed")

    st.markdown("### AI Summary")
    if detail.summary_text:
        st.success(detail.summary_text)
    else:
        st.info(summary_status_label(detail.summary_status))

    st.markdown("### Bai viet lien quan")
    related_items = service.get_related_articles(article_id=article_id, top_k=5)
    if not related_items:
        st.info("Chua co du lieu embedding hoac chua tim thay bai lien quan.")
    else:
        for item in related_items:
            st.markdown(
                f"- **{item.title}** | {item.source_name} | score={item.similarity_score:.3f} | {item.article_url}"
            )


def render_rag_qa(service: NewsUIService) -> None:
    st.subheader("Hoi dap RAG tren kho tin tuc")
    query_text = st.text_area(
        "Nhap cau hoi",
        placeholder="Vi du: Thi truong AI trong tuan nay co nhung tin noi bat nao?",
        height=120,
    )
    top_k = st.slider("So context truy xuat", min_value=1, max_value=10, value=5)

    if not st.button("Hoi", type="primary"):
        return
    if not query_text.strip():
        st.warning("Can nhap cau hoi truoc khi truy van.")
        return

    answer = service.ask_question(query_text=query_text.strip(), top_k=top_k)
    if not answer.contexts:
        st.info("Khong tim thay context phu hop trong kho du lieu hien tai.")
    st.markdown("### Tra loi")
    st.write(answer.answer_text)

    st.markdown("### Context da dung")
    for index, context in enumerate(answer.contexts, start=1):
        with st.expander(
            f"Context {index} | article_id={context.article_id} | score={context.score:.3f} | {context.source_name}"
        ):
            st.write(f"**Title:** {context.article_title}")
            st.write(context.chunk_text)


def format_datetime(value) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%Y-%m-%d %H:%M")


def summary_status_label(status: str) -> str:
    if status == "failed":
        return "AI enrichment da chay nhung summary bi loi."
    if status == "pending":
        return "Summary dang cho enrich."
    return "Chua enrich."


if __name__ == "__main__":
    main()
