from unittest.mock import MagicMock

from app.ingestion.crawlers.vnexpress_crawler import VnExpressCrawler


def test_vnexpress_parse_article_extracts_standard_fields() -> None:
    html = """
    <html>
      <head>
        <meta property="og:title" content="AI thay doi nganh du lieu" />
        <meta property="og:description" content="Tom tat bai viet" />
        <meta property="og:url" content="https://vnexpress.net/ai-thay-doi-nganh-du-lieu-123456.html" />
        <meta property="og:image" content="https://img.vnexpress.net/photo.jpg" />
        <meta property="article:published_time" content="2026-04-10T07:00:00+07:00" />
      </head>
      <body>
        <ul class="breadcrumb"><li>Kinh doanh</li><li>Cong nghe</li></ul>
        <h1 class="title-detail">AI thay doi nganh du lieu</h1>
        <p class="description">Tom tat bai viet</p>
        <article class="fck_detail">
          <p class="Normal">Doan 1 noi dung.</p>
          <p class="Normal">Doan 2 noi dung.</p>
        </article>
        <div class="box_author"><span class="name">Nguyen Van A</span></div>
      </body>
    </html>
    """
    crawler = VnExpressCrawler(session=MagicMock())

    article = crawler.parse_article(
        html,
        "https://vnexpress.net/ai-thay-doi-nganh-du-lieu-123456.html",
    )

    assert article.source_name == "vnexpress"
    assert article.title == "AI thay doi nganh du lieu"
    assert article.summary == "Tom tat bai viet"
    assert "Doan 1 noi dung." in article.content_text
    assert article.author_names == ["Nguyen Van A"]
    assert "Cong nghe" in article.category_names
    assert article.main_image_url == "https://img.vnexpress.net/photo.jpg"
