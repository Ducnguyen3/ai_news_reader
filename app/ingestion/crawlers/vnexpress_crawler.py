from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.ingestion.crawlers.base_crawler import BaseCrawler, FetchResult
from app.ingestion.parsers.common import (
    ParsedArticle,
    clean_text,
    clean_text_list,
    find_news_article_json_ld,
    get_meta_content,
    join_url,
    parse_datetime,
)


class VnExpressCrawler(BaseCrawler):
    source_name = "vnexpress"
    domain = "vnexpress.net"
    homepage_url = "https://vnexpress.net"
    category_paths = [
        "thoi-su",
        "the-gioi",
        "kinh-doanh",
        "khoa-hoc-cong-nghe",
        "giai-tri",
        "the-thao",
    ]

    def fetch_homepage(self) -> FetchResult:
        return self._request(self.homepage_url)

    def build_category_page_urls(self, category_path: str, page_number: int) -> list[str]:
        if page_number == 1:
            return [f"{self.homepage_url}/{category_path}"]
        return [
            f"{self.homepage_url}/{category_path}-p{page_number}",
            f"{self.homepage_url}/{category_path}?page={page_number}",
        ]

    def extract_article_links(self, homepage_html: str) -> list[str]:
        soup = BeautifulSoup(homepage_html, "lxml")
        links = [join_url(self.homepage_url, tag.get("href")) for tag in soup.select("a[href]")]
        return self.normalize_links(
            link
            for link in links
            if link
            and re.search(r"https://vnexpress\.net/.+-\d+\.html$", link)
            and "/video/" not in link
        )

    def parse_article(self, html: str, url: str) -> ParsedArticle:
        soup = BeautifulSoup(html, "lxml")
        json_ld = find_news_article_json_ld(soup) or {}
        title_node = soup.select_one("h1.title-detail") or soup.select_one("h1")
        summary_node = soup.select_one(".description") or soup.select_one("h2.description")
        title = clean_text(
            get_meta_content(soup, "property", "og:title")
            or json_ld.get("headline")
            or (title_node.get_text(" ", strip=True) if title_node else "")
        )
        summary = clean_text(
            get_meta_content(soup, "property", "og:description")
            or (summary_node.get_text(" ", strip=True) if summary_node else "")
        )
        content_nodes = soup.select("article.fck_detail p.Normal, article.fck_detail p")
        content_text = clean_text(" ".join(node.get_text(" ", strip=True) for node in content_nodes))
        authors = clean_text_list(
            [tag.get_text(" ", strip=True) for tag in soup.select(".author_mail, .box_author .name, .author")]
        )
        categories = clean_text_list(
            [tag.get_text(" ", strip=True) for tag in soup.select(".breadcrumb li, .box-breadcrumb a.item-cat")]
        )
        publish_time = parse_datetime(
            get_meta_content(soup, "property", "article:published_time")
            or json_ld.get("datePublished")
            or (soup.select_one(".date") and soup.select_one(".date").get_text(" ", strip=True))
        )
        updated_time = parse_datetime(
            get_meta_content(soup, "property", "article:modified_time")
            or json_ld.get("dateModified")
        )
        image_url = get_meta_content(soup, "property", "og:image")
        canonical_url = (
            get_meta_content(soup, "property", "og:url")
            or (soup.find("link", rel="canonical") or {}).get("href")
            or url
        )

        return ParsedArticle(
            source_name=self.source_name,
            article_url=url,
            canonical_url=canonical_url,
            title=title,
            summary=summary or None,
            content_text=content_text,
            publish_time=publish_time,
            author_names=authors,
            category_names=categories,
            main_image_url=image_url,
            tags=[],
            updated_time=updated_time,
        )


__all__ = ["VnExpressCrawler"]
